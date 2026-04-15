"""
API Routes
==========
FastAPI endpoint handlers for extraction pipelines (text, audio, image)
and the category correction endpoint.

Primary path: AWS Bedrock vision-language model for structured extraction.
Fallback: local regex-based extraction when Bedrock is disabled or fails.
"""

import os
import sys
import tempfile
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from api.schemas import (
    TextRequest,
    CorrectionRequest,
    TransactionData,
    TransactionResponse,
    ErrorResponse,
)
from api.config import get_settings
from nlp.cloud_extractor import CloudExtractor
from stt.transcriber import VoiceTranscriber

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")

# ─── Lazy-loaded engines (initialized once on first request) ──────────
_cloud: CloudExtractor | None = None
_cloud_checked = False
_stt: VoiceTranscriber | None = None


def get_cloud() -> CloudExtractor | None:
    """Singleton loader for the Bedrock cloud extractor (optional)."""
    global _cloud, _cloud_checked
    if not _cloud_checked:
        _cloud_checked = True
        try:
            settings = get_settings()
            if settings.bedrock_enabled:
                _cloud = CloudExtractor(
                    region=settings.bedrock_region,
                    model_id=settings.bedrock_model_id,
                    timeout_seconds=settings.bedrock_timeout_seconds,
                )
                _logger.info("Cloud extractor enabled (model=%s)", settings.bedrock_model_id)
            else:
                _logger.info("BEDROCK_ENABLED not set — cloud extraction disabled")
        except Exception:
            _logger.exception("Failed to init cloud extractor")
    return _cloud


def get_stt() -> VoiceTranscriber:
    """Singleton loader for the Whisper STT engine."""
    global _stt
    if _stt is None:
        _stt = VoiceTranscriber(model_size="small")
    return _stt


# ═══════════════════════════════════════════════════════════════════════
# 1. TEXT PIPELINE
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract/text", response_model=TransactionResponse)
async def extract_from_text(request: TextRequest):
    """Extract structured transaction data from a raw text message."""
    try:
        cloud = get_cloud()
        if cloud is not None:
            result = cloud.extract_from_text(request.text)
            return TransactionResponse(
                source="text",
                data=TransactionData(text_transcript=request.text, **result),
            )

        from nlp.inference import TransactionExtractor
        nlp = TransactionExtractor()
        result = nlp.extract(request.text)
        return TransactionResponse(
            source="text",
            data=TransactionData(text_transcript=request.text, **result),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════
# 2. AUDIO PIPELINE
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract/audio", response_model=TransactionResponse)
async def extract_from_audio(file: UploadFile = File(...)):
    """Extract structured transaction data from a voice note (Whisper STT -> cloud/NLP)."""
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or ".ogg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        stt = get_stt()
        transcript = stt.process_audio(tmp_path)["transcript"]

        cloud = get_cloud()
        if cloud is not None:
            result = cloud.extract_from_text(transcript)
        else:
            from nlp.inference import TransactionExtractor
            nlp = TransactionExtractor()
            result = nlp.extract(transcript)

        return TransactionResponse(
            source="audio",
            data=TransactionData(text_transcript=transcript, **result),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ═══════════════════════════════════════════════════════════════════════
# 3. IMAGE PIPELINE
# ═══════════════════════════════════════════════════════════════════════

@router.post("/extract/image", response_model=TransactionResponse)
async def extract_from_image(file: UploadFile = File(...)):
    """
    Extract structured transaction data from a receipt/screenshot image.
    Sends the image directly to the cloud VLM for end-to-end extraction.
    """
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename or ".jpg")[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        cloud = get_cloud()
        if cloud is not None:
            result = cloud.extract_from_image(content, image_ext=suffix)
            return TransactionResponse(
                source="image",
                data=TransactionData(
                    text_transcript=result.get("description") or "",
                    **{k: v for k, v in result.items() if k != "description"},
                ),
            )

        # Fallback: legacy OCR + NLP path (only if Bedrock disabled)
        from ocr.extractor import ReceiptOCR
        from nlp.inference import TransactionExtractor
        ocr = ReceiptOCR()
        ocr_result = ocr.process_receipt(tmp_path, use_preprocessing=True)
        all_text = " ".join(ocr_result.get("all_lines", []))
        nlp = TransactionExtractor()
        nlp_result = nlp.extract(all_text)
        return TransactionResponse(
            source="image",
            data=TransactionData(text_transcript=all_text, **nlp_result),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ═══════════════════════════════════════════════════════════════════════
# 4. CATEGORY CORRECTION (Memory System)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/correct")
async def correct_category(request: CorrectionRequest):
    """Save a user's category correction to the override map."""
    try:
        from nlp.inference import TransactionExtractor
        nlp = TransactionExtractor()
        nlp.save_correction(request.keyword, request.correct_category)
        return {
            "status": "success",
            "message": f"Saved: '{request.keyword}' → '{request.correct_category}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
