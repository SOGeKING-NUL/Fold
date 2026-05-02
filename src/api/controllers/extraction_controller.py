"""
Web Extraction Controller
==========================
Clerk-authenticated endpoints for the web prompt box.
Handles text, audio, and image extraction with automatic ledger posting.
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
from api.repositories.user_repository import UserRepository
from api.services.ledger_service import LedgerService, ExpenseRequest
from nlp.inference import TransactionExtractor
from stt.transcriber import VoiceTranscriber
from ocr.extractor import ReceiptOCR
from ocr.upi_detector import UPIAppDetector
from nlp.ollama_structurer import OllamaStructurer
from api.config import get_settings

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/web/extract", tags=["web-extraction"])

user_repo = UserRepository()
ledger_service = LedgerService()

# Lazy-loaded AI engines
_nlp: TransactionExtractor | None = None
_stt: VoiceTranscriber | None = None
_ocr: ReceiptOCR | None = None
_upi_detector: UPIAppDetector | None = None
_upi_detector_checked = False
_ollama_structurer: OllamaStructurer | None = None
_ollama_structurer_checked = False


def get_nlp() -> TransactionExtractor:
    global _nlp
    if _nlp is None:
        _nlp = TransactionExtractor()
    return _nlp


def get_stt() -> VoiceTranscriber:
    global _stt
    if _stt is None:
        _stt = VoiceTranscriber(model_size="small")
    return _stt


def get_ocr() -> ReceiptOCR:
    global _ocr
    if _ocr is None:
        _ocr = ReceiptOCR()
    return _ocr


def get_upi_detector() -> UPIAppDetector | None:
    global _upi_detector, _upi_detector_checked
    if not _upi_detector_checked:
        _upi_detector_checked = True
        try:
            settings = get_settings()
            if settings.roboflow_api_key:
                _upi_detector = UPIAppDetector(
                    api_key=settings.roboflow_api_key,
                    model_id=settings.roboflow_upi_model_id,
                )
        except Exception:
            _logger.exception("Failed to init UPI detector")
    return _upi_detector


def get_ollama_structurer() -> OllamaStructurer | None:
    global _ollama_structurer, _ollama_structurer_checked
    if not _ollama_structurer_checked:
        _ollama_structurer_checked = True
        try:
            settings = get_settings()
            if settings.ollama_enabled:
                _ollama_structurer = OllamaStructurer(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                )
        except Exception:
            _logger.exception("Failed to init Ollama structurer")
    return _ollama_structurer


class TextExtractionRequest(BaseModel):
    text: str


class ExtractionResponse(BaseModel):
    status: str = "success"
    source: str
    extracted_data: dict
    ledger_result: dict
    message: str


async def get_current_user_ref(request: Request) -> str:
    """Dependency to get current user from Clerk token."""
    user_info = await clerk_auth.require_auth(request)
    
    # Get or create user in database
    user = user_repo.get_or_create_user_from_clerk(
        clerk_user_id=user_info["clerk_user_id"],
        email=user_info.get("email"),
        full_name=user_info.get("full_name"),
        avatar_url=user_info.get("avatar_url"),
    )
    
    return user["external_user_ref"]


@router.post("/text", response_model=ExtractionResponse)
async def extract_and_save_text(
    payload: TextExtractionRequest,
    user_ref: str = Depends(get_current_user_ref)
):
    """
    Extract transaction from text and save to ledger.
    Used when user types in the prompt box.
    """
    try:
        # Extract structured data
        nlp = get_nlp()
        extracted = nlp.extract(payload.text)
        
        # Save to ledger if we have an amount
        if extracted.get("amount"):
            # Check if user has any payment accounts
            user = user_repo.get_user_by_ref(user_ref)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user's accounts to check if they have any payment methods
            accounts = ledger_service.list_accounts(user_ref)
            payment_accounts = [acc for acc in accounts if acc.get("account_type") in ("asset", "liability")]
            
            if not payment_accounts:
                # User hasn't added any payment methods yet
                return ExtractionResponse(
                    source="text",
                    extracted_data=extracted,
                    ledger_result={"status": "pending", "reason": "no_payment_method"},
                    message=f"Found {extracted['category']} expense of ₹{extracted['amount']}. Please add a payment method first to save this transaction."
                )
            
            ledger_result = ledger_service.post_expense(
                ExpenseRequest(
                    user_ref=user_ref,
                    source="web_text",
                    description=payload.text[:200],
                    expense_account_code="expense_operating",
                    funding_account_code=None,
                    funding_account_type=None,
                    amount=extracted["amount"],
                    external_ref=None,
                    category=extracted.get("category"),
                    payment_method=extracted.get("payment_method"),
                    payment_provider=extracted.get("payment_provider"),
                    receipt_account_last4=None,
                    receipt_institution_hint=None,
                )
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


@router.post("/audio", response_model=ExtractionResponse)
async def extract_and_save_audio(
    file: UploadFile = File(...),
    user_ref: str = Depends(get_current_user_ref)
):
    """
    Extract transaction from audio and save to ledger.
    Used when user records voice in the prompt box.
    """
    tmp_path = None
    try:
        # Save uploaded audio
        suffix = os.path.splitext(file.filename or ".ogg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Transcribe audio
        stt = get_stt()
        stt_result = stt.process_audio(tmp_path)
        transcript = stt_result["transcript"]
        
        # Extract structured data
        nlp = get_nlp()
        extracted = nlp.extract(transcript)
        extracted["transcript"] = transcript
        
        # Save to ledger if we have an amount
        if extracted.get("amount"):
            # Check if user has any payment accounts
            user = user_repo.get_user_by_ref(user_ref)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user's accounts to check if they have any payment methods
            accounts = ledger_service.list_accounts(user_ref)
            payment_accounts = [acc for acc in accounts if acc.get("account_type") in ("asset", "liability")]
            
            if not payment_accounts:
                # User hasn't added any payment methods yet
                return ExtractionResponse(
                    source="audio",
                    extracted_data=extracted,
                    ledger_result={"status": "pending", "reason": "no_payment_method"},
                    message=f"Found {extracted['category']} expense of ₹{extracted['amount']}. Please add a payment method first to save this transaction."
                )
            
            ledger_result = ledger_service.post_expense(
                ExpenseRequest(
                    user_ref=user_ref,
                    source="web_audio",
                    description=transcript[:200],
                    expense_account_code="expense_operating",
                    funding_account_code=None,
                    funding_account_type=None,
                    amount=extracted["amount"],
                    external_ref=None,
                    category=extracted.get("category"),
                    payment_method=extracted.get("payment_method"),
                    payment_provider=extracted.get("payment_provider"),
                    receipt_account_last4=None,
                    receipt_institution_hint=None,
                )
            )
            message = f"Saved {extracted['category']} expense of ₹{extracted['amount']}"
        else:
            ledger_result = {"status": "skipped", "reason": "no_amount"}
            message = f"Transcribed: {transcript}"
        
        # Cleanup
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        return ExtractionResponse(
            source="audio",
            extracted_data=extracted,
            ledger_result=ledger_result,
            message=message
        )
    
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        _logger.exception("Audio extraction failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/image", response_model=ExtractionResponse)
async def extract_and_save_image(
    file: UploadFile = File(...),
    user_ref: str = Depends(get_current_user_ref)
):
    """
    Extract transaction from receipt image and save to ledger.
    Used when user uploads image in the prompt box.
    """
    tmp_path = None
    try:
        # Save uploaded image
        suffix = os.path.splitext(file.filename or ".jpg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # UPI detection
        visual_provider: str | None = None
        detector = get_upi_detector()
        if detector is not None:
            visual_provider = detector.detect(tmp_path)
        
        # OCR
        use_preprocessing = False
        ocr = get_ocr()
        ocr_result = ocr.process_receipt(tmp_path, use_preprocessing=use_preprocessing)
        all_text = " ".join(ocr_result.get("all_lines", []))
        ocr_parsed = ocr_result.get("parsed", {})
        
        # Ollama structuring
        text_source = "upi_ocr" if visual_provider else "receipt_ocr"
        ollama = get_ollama_structurer()
        llm_result: dict = {}
        if ollama is not None:
            try:
                llm_result = ollama.structure_from_ocr(
                    raw_text=all_text,
                    text_source=text_source,
                    hints={
                        "visual_provider": visual_provider,
                        "ocr_amount": ocr_parsed.get("amount"),
                        "ocr_payment_method": ocr_parsed.get("payment_method"),
                        "ocr_payment_provider": ocr_parsed.get("payment_provider"),
                        "instrument_last4": ocr_parsed.get("instrument_last4"),
                        "instrument_institution_hint": ocr_parsed.get("instrument_institution_hint"),
                    },
                )
            except Exception:
                _logger.exception("Ollama structuring failed")
        
        # NLP extraction
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
        
        # Merge results
        final_amount = llm_result.get("amount") or ocr_parsed.get("amount") or nlp_result.get("amount")
        final_payment = llm_result.get("payment_method") or ocr_parsed.get("payment_method") or nlp_result.get("payment_method")
        final_provider = visual_provider or llm_result.get("payment_provider") or ocr_parsed.get("payment_provider") or nlp_result.get("payment_provider")
        final_bank = llm_result.get("bank_account") or nlp_result.get("bank_account")
        
        if final_provider and (not final_payment or final_payment == "unknown"):
            final_payment = "upi"
        
        extracted = {
            "amount": final_amount,
            "category": nlp_result["category"],
            "payment_method": final_payment,
            "payment_provider": final_provider,
            "bank_account": final_bank,
            "receipt_account_last4": ocr_parsed.get("instrument_last4"),
            "receipt_institution_hint": ocr_parsed.get("instrument_institution_hint"),
            "ocr_text": all_text[:500],
        }
        
        # Save to ledger if we have an amount
        if extracted.get("amount"):
            # Check if user has any payment accounts
            user = user_repo.get_user_by_ref(user_ref)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get user's accounts to check if they have any payment methods
            accounts = ledger_service.list_accounts(user_ref)
            payment_accounts = [acc for acc in accounts if acc.get("account_type") in ("asset", "liability")]
            
            if not payment_accounts:
                # User hasn't added any payment methods yet
                return ExtractionResponse(
                    source="image",
                    extracted_data=extracted,
                    ledger_result={"status": "pending", "reason": "no_payment_method"},
                    message=f"Found {extracted['category']} expense of ₹{extracted['amount']}. Please add a payment method first to save this transaction."
                )
            
            ledger_result = ledger_service.post_expense(
                ExpenseRequest(
                    user_ref=user_ref,
                    source="web_image",
                    description=f"{extracted['category']} from receipt",
                    expense_account_code="expense_operating",
                    funding_account_code=None,
                    funding_account_type=None,
                    amount=extracted["amount"],
                    external_ref=None,
                    category=extracted.get("category"),
                    payment_method=extracted.get("payment_method"),
                    payment_provider=extracted.get("payment_provider"),
                    receipt_account_last4=extracted.get("receipt_account_last4"),
                    receipt_institution_hint=extracted.get("receipt_institution_hint"),
                )
            )
            message = f"Saved {extracted['category']} expense of ₹{extracted['amount']}"
        else:
            ledger_result = {"status": "skipped", "reason": "no_amount"}
            message = "Extracted data but no amount found"
        
        # Cleanup
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        return ExtractionResponse(
            source="image",
            extracted_data=extracted,
            ledger_result=ledger_result,
            message=message
        )
    
    except Exception as e:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        _logger.exception("Image extraction failed")
        raise HTTPException(status_code=500, detail=str(e))
