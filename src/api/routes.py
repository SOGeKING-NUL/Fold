"""
API Routes
==========
Defines the FastAPI endpoint handlers for the three extraction pipelines
(audio, text, image) plus the category correction endpoint.

Each route receives raw input, passes it through the appropriate AI engine
(STT / OCR / direct), and then funnels the result through the unified
NLP TransactionExtractor to produce a normalized JSON response.
"""

import os
import sys
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException

# ─── Fix imports: add `src/` to the Python path ─────────────────────────
# This allows us to import sibling packages (ocr, stt, nlp) cleanly
# regardless of how the server is launched.
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import logging

from api.schemas import (
    TextRequest,
    CorrectionRequest,
    TransactionData,
    TransactionResponse,
    ErrorResponse,
)
from api.config import get_settings
from nlp.inference import TransactionExtractor
from stt.transcriber import VoiceTranscriber
from ocr.extractor import ReceiptOCR
from ocr.upi_detector import UPIAppDetector

_logger = logging.getLogger(__name__)

# ─── Router ──────────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/v1")

# ─── Lazy-loaded AI engines (initialized once on first request) ──────────
_nlp: TransactionExtractor | None = None
_stt: VoiceTranscriber | None = None
_ocr: ReceiptOCR | None = None
_upi_detector: UPIAppDetector | None = None
_upi_detector_checked = False


def get_nlp() -> TransactionExtractor:
    """Singleton loader for the NLP extraction engine."""
    global _nlp
    if _nlp is None:
        _nlp = TransactionExtractor()
    return _nlp


def get_stt() -> VoiceTranscriber:
    """Singleton loader for the Whisper STT engine."""
    global _stt
    if _stt is None:
        _stt = VoiceTranscriber(model_size="small")
    return _stt


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

    Used when a WhatsApp user sends a plain text message like:
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
        stt = get_stt()
        stt_result = stt.process_audio(tmp_path)
        transcript = stt_result["transcript"]

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
    Extract structured transaction data from a receipt image.

    Flow: .jpg/.png → PaddleOCR → raw text lines → NLP category guess
          + OCR amount/payment extraction.

    The OCR engine handles amount and payment_method extraction natively.
    The raw text is additionally fed into DistilBERT for category guessing.
    """
    try:
        suffix = os.path.splitext(file.filename or ".jpg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Step 1: Run PaddleOCR
        ocr = get_ocr()
        ocr_result = ocr.process_receipt(tmp_path, use_preprocessing=False)

        all_text = " ".join(ocr_result.get("all_lines", []))
        ocr_parsed = ocr_result.get("parsed", {})

        # Step 2: NLP on raw OCR text (category + text-based provider)
        nlp = get_nlp()
        nlp_result = nlp.extract(all_text)

        # Step 3: Visual UPI logo detection (highest priority for provider)
        visual_provider: str | None = None
        detector = get_upi_detector()
        if detector is not None:
            visual_provider = detector.detect(tmp_path)

        # Merge: amount (OCR > NLP), payment_method (OCR > NLP),
        # payment_provider (visual > OCR > NLP)
        final_amount = ocr_parsed.get("amount") or nlp_result.get("amount")
        final_payment = ocr_parsed.get("payment_method")
        if final_payment == "unknown":
            final_payment = nlp_result.get("payment_method")

        final_provider = (
            visual_provider
            or ocr_parsed.get("payment_provider")
            or nlp_result.get("payment_provider")
        )
        if final_provider and (final_payment is None or final_payment == "unknown"):
            final_payment = "upi"

        final_cash_flow = ocr_parsed.get("cash_flow") or nlp_result.get("cash_flow")

        os.unlink(tmp_path)

        return TransactionResponse(
            source="image",
            data=TransactionData(
                text_transcript=all_text,
                amount=final_amount,
                category=nlp_result["category"],
                payment_method=final_payment,
                payment_provider=final_provider,
                bank_account=nlp_result.get("bank_account"),
                cash_flow=final_cash_flow,
            )
        )
    except Exception as e:
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# 4. CATEGORY CORRECTION (Memory System)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/correct")
async def correct_category(request: CorrectionRequest):
    """
    Save a user's category correction to the override map.
    Future transactions containing this keyword will automatically
    use the corrected category instead of the model's prediction.

    Example request:
        {"keyword": "xyz society", "correct_category": "rent"}
    """
    try:
        nlp = get_nlp()
        nlp.save_correction(request.keyword, request.correct_category)
        return {
            "status": "success",
            "message": f"Saved: '{request.keyword}' → '{request.correct_category}'"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
