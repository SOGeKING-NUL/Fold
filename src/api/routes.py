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
from nlp.ollama_structurer import OllamaStructurer
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
_ollama_structurer: OllamaStructurer | None = None
_ollama_structurer_checked = False


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


def get_ollama_structurer() -> OllamaStructurer | None:
    """Singleton loader for local Ollama OCR text structurer (optional)."""
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
                _logger.info(
                    "Ollama structurer enabled (base=%s model=%s)",
                    settings.ollama_base_url,
                    settings.ollama_model,
                )
            else:
                _logger.info("OLLAMA_ENABLED=false — Ollama structurer disabled")
        except Exception:
            _logger.exception("Failed to init Ollama structurer — disabled")
    return _ollama_structurer


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

    Flow:
      1) Roboflow logo model first (UPI detection),
      2) OCR mode decision:
         - UPI detected -> raw OCR
         - no UPI detected -> preprocessed OCR
      3) OCR transcript to NLP.
    """
    try:
        suffix = os.path.splitext(file.filename or ".jpg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Step 1: Visual UPI logo detection first (model-driven routing)
        visual_provider: str | None = None
        detector = get_upi_detector()
        if detector is not None:
            visual_provider = detector.detect(tmp_path)

        # Step 2: Run PaddleOCR. Preprocessing intentionally disabled in
        # OCR->LLM->NLP flow for both UPI and normal receipts.
        # use_preprocessing = not bool(visual_provider)
        use_preprocessing = False
        ocr = get_ocr()
        ocr_result = ocr.process_receipt(tmp_path, use_preprocessing=use_preprocessing)

        all_text = " ".join(ocr_result.get("all_lines", []))
        ocr_parsed = ocr_result.get("parsed", {})

        # Step 3: Ollama structures OCR text (if enabled)
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
                _logger.info(
                    "[ExtractImage] ollama structured amount=%s method=%s provider=%s bank=%s cash_flow=%s",
                    llm_result.get("amount"),
                    llm_result.get("payment_method"),
                    llm_result.get("payment_provider"),
                    llm_result.get("bank_account"),
                    llm_result.get("cash_flow"),
                )
            except Exception:
                _logger.exception("Ollama structuring failed; continuing with OCR/NLP fallback")

        # Step 4: NLP on LLM-preprocessed OCR text (NLP remains final extractor/category)
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
            if llm_result.get("cash_flow"):
                llm_lines.append(f"cash flow {llm_result['cash_flow']}")
            llm_hint_text = " ; ".join(llm_lines).strip()
            if llm_hint_text:
                preprocessed_text = f"{llm_hint_text}\n{all_text}".strip()

        nlp = get_nlp()
        nlp_result = nlp.extract(preprocessed_text or "expense")

        # Merge:
        # - UPI screenshots: NLP amount works better (currency-tagged / app-style text)
        # - Invoice/bill images: OCR total-line extraction works better
        is_upi_evidence = bool(
            visual_provider
            or llm_result.get("payment_provider")
            or ocr_parsed.get("payment_provider")
            or nlp_result.get("payment_provider")
            or ocr_parsed.get("payment_method") == "upi"
            or nlp_result.get("payment_method") == "upi"
        )
        # LLM is primary for OCR-derived extraction. NLP is mainly for category.
        final_amount = llm_result.get("amount") or ocr_parsed.get("amount") or nlp_result.get("amount")
        final_payment = llm_result.get("payment_method") or ocr_parsed.get("payment_method") or nlp_result.get("payment_method")
        if final_payment == "unknown":
            final_payment = llm_result.get("payment_method") or nlp_result.get("payment_method")

        final_provider = (
            visual_provider
            or llm_result.get("payment_provider")
            or ocr_parsed.get("payment_provider")
            or nlp_result.get("payment_provider")
        )
        final_bank = llm_result.get("bank_account") or nlp_result.get("bank_account")
        final_cash_flow = llm_result.get("cash_flow") or ocr_parsed.get("cash_flow") or nlp_result.get("cash_flow")

        # debug: where final amount was chosen from
        amount_source = "none"
        if llm_result.get("amount") is not None:
            amount_source = "llm"
        elif ocr_parsed.get("amount") is not None:
            amount_source = "ocr"
        elif nlp_result.get("amount") is not None:
            amount_source = "nlp"

        if final_provider and (final_payment is None or final_payment == "unknown"):
            final_payment = "upi"
        if is_upi_evidence and (final_payment is None or final_payment == "unknown"):
            final_payment = "upi"

        _logger.info(
            "[ExtractImage] merged amount=%s method=%s provider=%s bank=%s cash_flow=%s amount_source=%s llm_called=%s llm_success=%s",
            final_amount,
            final_payment,
            final_provider,
            final_bank,
            final_cash_flow,
            amount_source,
            ollama is not None,
            bool(llm_result),
        )

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
                cash_flow=final_cash_flow,
                receipt_account_last4=ocr_parsed.get("instrument_last4"),
                receipt_institution_hint=ocr_parsed.get("instrument_institution_hint"),
                debug_is_upi_evidence=is_upi_evidence,
                debug_amount_source=amount_source,
                debug_ocr_preprocessing=use_preprocessing,
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
