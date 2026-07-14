"""
Web Extraction Controller
==========================
Clerk-authenticated endpoints for the web prompt box.

Architecture:
- TEXT:  Synchronous — NLP extraction, result returned immediately (<1s)
- AUDIO: Synchronous — Whisper STT → NLP → Ledger, result returned (~3-5s)
- IMAGE: Synchronous — UPI detection → OCR → Ollama → NLP → Ledger, result returned (~5-7s)

All endpoints process the request synchronously and return the complete result.
No background workers, no job queues, no polling needed.
"""

import os
import sys
import tempfile
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from pydantic import BaseModel

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from api.middleware.clerk_auth import clerk_auth
from api.repositories.user_repository import get_or_create_user_from_clerk
from api.services import ledger_service
from nlp.inference import TransactionExtractor
from api.config import get_settings

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/web/extract", tags=["web-extraction"])



# Lazy-loaded NLP engine (only needed for synchronous text extraction)
_nlp: TransactionExtractor | None = None


def get_nlp() -> TransactionExtractor:
    global _nlp
    if _nlp is None:
        _nlp = TransactionExtractor()
    return _nlp


# ─── Request / Response Models ─────────────────────────────────────────

class TextExtractionRequest(BaseModel):
    text: str


class ExtractionResponse(BaseModel):
    """Returned for synchronous extraction (text, audio, image)."""
    status: str = "success"
    source: str
    extracted_data: dict
    ledger_result: dict
    message: str


# ─── Auth Dependency ───────────────────────────────────────────────────

async def get_current_user_info(request: Request) -> dict:
    """
    Dependency that returns both the user_ref and clerk_user_id.
    """
    user_info = await clerk_auth.require_auth(request)

    user = get_or_create_user_from_clerk(
        clerk_user_id=user_info["clerk_user_id"],
        email=user_info.get("email"),
        full_name=user_info.get("full_name"),
        avatar_url=user_info.get("avatar_url"),
    )

    return {
        "user_ref": user_info["clerk_user_id"],
        "clerk_user_id": user_info["clerk_user_id"],
    }


# ═══════════════════════════════════════════════════════════════════════
# 1. TEXT — Synchronous (fast, no queue needed)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/text", response_model=ExtractionResponse)
async def extract_and_save_text(
    payload: TextExtractionRequest,
    user_info: dict = Depends(get_current_user_info)
):
    """
    Extract transaction from text and save to ledger.
    This is synchronous because NLP text extraction is fast (<1 second).
    """
    user_ref = user_info["user_ref"]

    try:
        nlp = get_nlp()
        extracted = nlp.extract(payload.text)

        if extracted.get("amount"):
            accounts = ledger_service.list_accounts(user_ref)
            payment_accounts = [acc for acc in accounts if acc.get("account_type") in ("cash", "bank", "credit")]

            if not payment_accounts:
                return ExtractionResponse(
                    source="text",
                    extracted_data=extracted,
                    ledger_result={"status": "pending", "reason": "no_payment_method"},
                    message=f"Found {extracted['category']} expense of ₹{extracted['amount']}. Please add a payment method first to save this transaction."
                )

            ledger_result = ledger_service.post_expense(
                user_ref=user_ref,
                source="web_text",
                description=payload.text[:200],
                amount=extracted["amount"],
                category=extracted.get("category"),
                payment_method=extracted.get("payment_method"),
                payment_provider=extracted.get("payment_provider"),
                bank_hint=extracted.get("bank_account"),
            )
            message = f"Saved {extracted['category']} expense of ₹{extracted['amount']}"
        else:
            ledger_result = {"status": "skipped", "reason": "no_amount"}
            message = "Extracted data but no amount found"

        return ExtractionResponse(
            source="text",
            extracted_data=extracted,
            ledger_result=ledger_result,
            message=message
        )

    except Exception as e:
        _logger.exception("Text extraction failed")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# 2. AUDIO — Synchronous (processes immediately, user waits)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/audio", response_model=ExtractionResponse)
async def extract_and_save_audio(
    file: UploadFile = File(...),
    user_info: dict = Depends(get_current_user_info)
):
    """
    Extract transaction from audio and save to ledger.
    This is synchronous - the user waits for the result (~3-5 seconds).
    """
    user_ref = user_info["user_ref"]
    
    _logger.info("="*80)
    _logger.info("🎤 [API] Audio upload received (SYNCHRONOUS)")
    _logger.info("  - User: %s", user_ref)
    _logger.info("  - Filename: %s", file.filename)
    _logger.info("="*80)

    try:
        # Save uploaded audio to a temp file
        suffix = os.path.splitext(file.filename or ".ogg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="fold_audio_") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        _logger.info("🎧 [API] Processing audio...")
        
        try:
            # Import processing modules
            from stt.transcriber import transcribe_audio
            
            # Step 1: Transcribe audio → text
            _logger.info("  [1/3] Transcribing audio...")
            settings = get_settings()
            transcript = transcribe_audio(tmp_path, api_key=settings.sarvam_api_key)
            _logger.info("    ✓ Transcript: %s", transcript[:100])

            # Step 2: Extract structured data from transcript
            _logger.info("  [2/3] Extracting transaction data...")
            nlp = get_nlp()
            extracted = nlp.extract(transcript)
            extracted["transcript"] = transcript
            extracted["raw_text"] = transcript
            _logger.info("    ✓ Amount: %s, Category: %s", extracted.get("amount"), extracted.get("category"))

            # Step 3: Save to ledger if we have an amount
            _logger.info("  [3/3] Saving to ledger...")
            if extracted.get("amount"):
                accounts = ledger_service.list_accounts(user_ref)
                payment_accounts = [a for a in accounts if a.get("account_type") in ("cash", "bank", "credit")]

                if not payment_accounts:
                    _logger.info("    ⚠ No payment accounts found")
                    return ExtractionResponse(
                        source="audio",
                        extracted_data=extracted,
                        ledger_result={"status": "pending", "reason": "no_payment_method"},
                        message=f"Found {extracted['category']} expense of ₹{extracted['amount']}. Please add a payment method first."
                    )

                ledger_result = ledger_service.post_expense(
                    user_ref=user_ref,
                    source="web_audio",
                    description=transcript[:200],
                    amount=extracted["amount"],
                    category=extracted.get("category"),
                    payment_method=extracted.get("payment_method"),
                    payment_provider=extracted.get("payment_provider"),
                    bank_hint=extracted.get("bank_account"),
                )
                message = f"Saved {extracted['category']} expense of ₹{extracted['amount']}"
                _logger.info("    ✓ Journal #%s", ledger_result.get("journal_id"))
            else:
                ledger_result = {"status": "skipped", "reason": "no_amount"}
                message = f"Transcribed: {transcript}"

            _logger.info("✅ [API] Audio processing complete")
            _logger.info("="*80)

            return ExtractionResponse(
                source="audio",
                extracted_data=extracted,
                ledger_result=ledger_result,
                message=message
            )

        finally:
            # Always clean up the temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        _logger.exception("❌ [API] Audio extraction failed")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# 3. IMAGE — Synchronous (processes immediately, user waits)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/image", response_model=ExtractionResponse)
async def extract_and_save_image(
    file: UploadFile = File(...),
    user_info: dict = Depends(get_current_user_info)
):
    """
    Extract transaction from image and save to ledger.
    This is synchronous - the user waits for the result (~5-7 seconds).
    """
    user_ref = user_info["user_ref"]
    
    _logger.info("="*80)
    _logger.info("📥 [API] Image upload received (SYNCHRONOUS)")
    _logger.info("  - User: %s", user_ref)
    _logger.info("  - Filename: %s", file.filename)
    _logger.info("="*80)

    try:
        # Save uploaded image to a temp file
        suffix = os.path.splitext(file.filename or ".jpg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="fold_image_") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        _logger.info("📸 [API] Processing image...")
        
        try:
            # Import processing modules
            from ocr.extractor import ReceiptOCR
            from ocr.upi_detector import UPIAppDetector
            from nlp.inference import TransactionExtractor
            
            settings = get_settings()

            # Step 1: UPI logo detection
            visual_provider = None
            try:
                if settings.roboflow_api_key:
                    _logger.info("  [1/5] UPI detection...")
                    detector = UPIAppDetector(
                        api_key=settings.roboflow_api_key,
                        model_id=settings.roboflow_upi_model_id,
                    )
                    visual_provider = detector.detect(tmp_path)
                    _logger.info("    ✓ Provider: %s", visual_provider or "none")
            except Exception:
                _logger.exception("    ✗ UPI detection failed, continuing")

            # Step 2: OCR — extract raw text from the image
            _logger.info("  [2/5] OCR extraction...")
            ocr = ReceiptOCR()
            ocr_result = ocr.process_receipt(tmp_path, use_preprocessing=False)
            all_text = " ".join(ocr_result.get("all_lines", []))
            print(f"    ✓ Extracted {len(ocr_result.get('all_lines', []))} lines")
            
            print("====== DEBUG: OCR RAW TEXT ======")
            print(all_text)
            print("=================================")

            # Step 3: Groq structuring — let the LLM parse noisy OCR text
            text_source = "upi_ocr" if visual_provider else "receipt_ocr"
            _logger.info("  [3/5] Extracting fields via Groq LLM...")
            llm_result = {}
            settings = get_settings()
            if settings.groq_api_key:
                try:
                    from nlp.llm_structurer import structure_from_ocr
                    llm_result = structure_from_ocr(
                        raw_text=all_text,
                        text_source=text_source,
                        api_key=settings.groq_api_key,
                        hints={"visual_provider": visual_provider},
                    )
                    _logger.info("    ✓ Amount: %s", llm_result.get("amount"))
                    
                    print("====== DEBUG: GROQ OUTPUT ======")
                    print(llm_result)
                    print("================================")
                except Exception:
                    _logger.exception("    ✗ Groq LLM structuring failed, continuing")

            # Step 4: NLP classification — get category from DistilBERT
            _logger.info("  [4/5] NLP classification...")
            preprocessed_text = all_text
            if llm_result:
                llm_lines = []
                if llm_result.get("description"):
                    llm_lines.append(str(llm_result["description"]))
                if llm_result.get("amount") is not None:
                    llm_lines.append(f"amount rs {llm_result['amount']}")
                if llm_result.get("payment_method"):
                    llm_lines.append(f"payment method {llm_result['payment_method']}")
                if llm_result.get("payment_provider"):
                    llm_lines.append(f"provider {llm_result['payment_provider']}")
                if llm_result.get("bank_account"):
                    llm_lines.append(f"bank {llm_result['bank_account']}")
                llm_hint_text = " ; ".join(llm_lines).strip()
                if llm_hint_text:
                    preprocessed_text = f"{llm_hint_text}\n{all_text}".strip()

            nlp = get_nlp()
            nlp_result = nlp.extract(preprocessed_text or "expense")
            _logger.info("    ✓ Category: %s", nlp_result.get("category"))
            
            print("====== DEBUG: NLP OUTPUT ======")
            print(nlp_result)
            print("===============================")

            # Merge results — LLM is primary for OCR fields, NLP for category
            final_amount = llm_result.get("amount") or nlp_result.get("amount")
            final_payment = llm_result.get("payment_method") or nlp_result.get("payment_method")
            final_provider = visual_provider or llm_result.get("payment_provider") or nlp_result.get("payment_provider")
            final_bank = llm_result.get("bank_account") or nlp_result.get("bank_account")

            if final_provider and (not final_payment or final_payment == "unknown"):
                final_payment = "upi"

            extracted = {
                "amount": final_amount,
                "category": nlp_result["category"],
                "payment_method": final_payment,
                "payment_provider": final_provider,
                "bank_account": final_bank,
                "ocr_text": all_text[:500],
                "raw_text": all_text[:500],
            }
            
            print("====== DEBUG: FINAL EXTRACTED MERGED ======")
            print(extracted)
            print("===========================================")

            # Step 5: Save to ledger
            _logger.info("  [5/5] Saving to ledger...")
            if extracted.get("amount"):
                accounts = ledger_service.list_accounts(user_ref)
                payment_accounts = [acc for acc in accounts if acc.get("account_type") in ("cash", "bank", "credit")]

                if not payment_accounts:
                    _logger.info("    ⚠ No payment accounts found")
                    return ExtractionResponse(
                        source="image",
                        extracted_data=extracted,
                        ledger_result={"status": "pending", "reason": "no_payment_method"},
                        message=f"Found {extracted['category']} expense of ₹{extracted['amount']}. Please add a payment method first to save this transaction."
                    )

                ledger_result = ledger_service.post_expense(
                    user_ref=user_ref,
                    source="web_image",
                    description=f"{extracted['category']} from receipt",
                    amount=extracted["amount"],
                    category=extracted.get("category"),
                    payment_method=extracted.get("payment_method"),
                    payment_provider=extracted.get("payment_provider"),
                    bank_hint=extracted.get("bank_account"),
                )
                message = f"Saved {extracted['category']} expense of ₹{extracted['amount']}"
                _logger.info("    ✓ Journal #%s", ledger_result.get("journal_id"))
            else:
                ledger_result = {"status": "skipped", "reason": "no_amount"}
                message = "Extracted data but no amount found"

            _logger.info("✅ [API] Image processing complete")
            _logger.info("="*80)

            return ExtractionResponse(
                source="image",
                extracted_data=extracted,
                ledger_result=ledger_result,
                message=message
            )

        finally:
            # Always clean up the temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        _logger.exception("❌ [API] Image extraction failed")
        raise HTTPException(status_code=500, detail=str(e))


