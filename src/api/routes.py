"""
API Routes
==========
Defines the FastAPI endpoint handlers for the three extraction pipelines
(audio, text, image).

Each route receives raw input, passes it through the appropriate AI engine
(STT / OCR / direct), and then funnels the result through the unified
NLP TransactionExtractor to produce a normalized JSON response.

Pipelines:
    1. TEXT:  Raw text → NLP extraction
    2. AUDIO: Audio file → Whisper STT → transcript → NLP extraction
    3. IMAGE: Image → PaddleOCR → Ollama structuring → NLP classification
"""

import os
import sys
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException

# ─── Fix imports: add `src/` to the Python path ─────────────────────────
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import logging

from api.schemas import (
    TextRequest,
    TransactionData,
    TransactionResponse,
    ErrorResponse,
)
from api.config import get_settings
from nlp.inference import TransactionExtractor
from nlp.llm_structurer import structure_from_ocr
from stt.transcriber import transcribe_audio
from ocr.extractor import ReceiptOCR
from ocr.upi_detector import UPIAppDetector

_logger = logging.getLogger(__name__)

# ─── Router ──────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1")

# ─── Lazy-loaded AI engines (initialized once on first request) ──────────
_nlp: TransactionExtractor | None = None
_ocr: ReceiptOCR | None = None
_upi_detector: UPIAppDetector | None = None
_upi_detector_checked = False


def get_nlp() -> TransactionExtractor:
    """Singleton loader for the NLP extraction engine."""
    global _nlp
    if _nlp is None:
        _nlp = TransactionExtractor()
    return _nlp


def get_ocr() -> ReceiptOCR:
    """Singleton loader for the PaddleOCR engine."""
    global _ocr
    if _ocr is None:
        _ocr = ReceiptOCR()
    return _ocr


def get_upi_detector() -> UPIAppDetector | None:
    """Singleton loader for the Roboflow UPI logo detector (optional)."""
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
                _logger.info("UPI logo detector enabled (model=%s)", settings.roboflow_upi_model_id)
            else:
                _logger.info("ROBOFLOW_API_KEY not set — UPI logo detection disabled")
        except Exception:
            _logger.exception("Failed to init UPI detector — logo detection disabled")
    return _upi_detector


# ═══════════════════════════════════════════════════════════════════════
# 1. TEXT PIPELINE
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract/text", response_model=TransactionResponse)
async def extract_from_text(request: TextRequest):
    """
    Extract structured transaction data from a raw text message.
    This is the simplest pipeline — bypasses STT and OCR entirely.

    Used when a user sends a plain text message like:
        "Swiggy se 450 rupaye ka pizza mangwaya UPI se"
    """
    try:
        nlp = get_nlp()
        result = nlp.extract(request.text)

        return TransactionResponse(
            source="text",
            data=TransactionData(
                text_transcript=request.text,
                **result
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# 2. AUDIO PIPELINE
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract/audio", response_model=TransactionResponse)
async def extract_from_audio(file: UploadFile = File(...)):
    """
    Extract structured transaction data from a voice note.

    Flow: .ogg file → Whisper STT → raw transcript → NLP extraction.

    Accepts any audio format supported by FFmpeg (.ogg, .wav, .mp3, .m4a).
    """
    try:
        # Save uploaded audio to a temporary file
        suffix = os.path.splitext(file.filename or ".ogg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Step 1: Transcribe audio → text
        settings = get_settings()
        transcript = transcribe_audio(tmp_path, api_key=settings.sarvam_api_key)

        # Step 2: Extract structured data from transcript
        nlp = get_nlp()
        result = nlp.extract(transcript)

        # Cleanup temp file
        os.unlink(tmp_path)

        return TransactionResponse(
            source="audio",
            data=TransactionData(
                text_transcript=transcript,
                **result
            )
        )
    except Exception as e:
        # Cleanup on error
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# 3. IMAGE (OCR) PIPELINE
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract/image", response_model=TransactionResponse)
async def extract_from_image(file: UploadFile = File(...)):
    """
    Extract structured transaction data from a receipt or UPI screenshot.

    Flow:
      1) Roboflow logo model detects if this is a UPI screenshot
      2) PaddleOCR extracts raw text from the image
      3) Groq (LLM) structures the noisy OCR text into clean JSON
      4) NLP model classifies the category
    """
    try:
        suffix = os.path.splitext(file.filename or ".jpg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Step 1: Visual UPI logo detection (identifies if screenshot is from GPay, PhonePe, etc.)
        visual_provider: str | None = None
        detector = get_upi_detector()
        if detector is not None:
            visual_provider = detector.detect(tmp_path)

        # Step 2: Run PaddleOCR to extract text from the image
        ocr = get_ocr()
        ocr_result = ocr.process_receipt(tmp_path, use_preprocessing=False)
        all_text = ocr_result.get("raw_text", "")

        # Step 3: Groq structures the noisy OCR text into clean fields
        # OCR text from receipts is messy and unstructured — an LLM is the
        # best tool to make sense of scattered text fragments
        text_source = "upi_ocr" if visual_provider else "receipt_ocr"
        llm_result: dict = {}
        settings = get_settings()
        if settings.groq_api_key:
            try:
                llm_result = structure_from_ocr(
                    raw_text=all_text,
                    text_source=text_source,
                    api_key=settings.groq_api_key,
                    hints={"visual_provider": visual_provider},
                )
                _logger.info(
                    "[ExtractImage] LLM structured: amount=%s method=%s provider=%s bank=%s",
                    llm_result.get("amount"),
                    llm_result.get("payment_method"),
                    llm_result.get("payment_provider"),
                    llm_result.get("bank_account"),
                )
            except Exception:
                _logger.exception("LLM structuring failed; continuing with NLP fallback")

        # Step 4: Build preprocessed text for NLP classification
        # We prepend LLM's structured output so the DistilBERT model
        # gets clean, readable text for category classification
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

        # Step 5: Merge results — LLM is primary for OCR fields, NLP for category
        final_amount = llm_result.get("amount") or nlp_result.get("amount")
        final_payment = llm_result.get("payment_method") or nlp_result.get("payment_method")
        final_provider = (
            visual_provider
            or llm_result.get("payment_provider")
            or nlp_result.get("payment_provider")
        )
        final_bank = llm_result.get("bank_account") or nlp_result.get("bank_account")

        # If we know the UPI provider, the payment method must be "upi"
        if final_provider and (final_payment is None or final_payment == "unknown"):
            final_payment = "upi"

        os.unlink(tmp_path)

        return TransactionResponse(
            source="image",
            data=TransactionData(
                text_transcript=preprocessed_text,
                amount=final_amount,
                category=nlp_result["category"],
                payment_method=final_payment,
                payment_provider=final_provider,
                bank_account=final_bank,
            )
        )
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug/upi-logo")
async def debug_upi_logo(file: UploadFile = File(...)):
    """
    Debug endpoint to test Roboflow UPI-logo model directly.
    Returns raw detection payload + resolved provider.
    """
    try:
        suffix = os.path.splitext(file.filename or ".jpg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        detector = get_upi_detector()
        if detector is None:
            raise HTTPException(status_code=400, detail="UPI detector disabled: ROBOFLOW_API_KEY missing")
        dbg = detector.detect_with_debug(tmp_path)
        os.unlink(tmp_path)
        return {"status": "success", **dbg}
    except HTTPException:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))

