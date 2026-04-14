"""
UPI Logo Detector
=================
Detects which UPI payment app appears in a screenshot using the Roboflow
hosted inference API (dataset: document-classification/upi).

For production local hosting, swap the detect() internals to use
ultralytics YOLO or the Roboflow Inference Server docker container
with the same model weights exported in YOLO format.
"""

import base64
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# Roboflow class names → canonical provider slugs used in payment_profiles
_CLASS_TO_PROVIDER: dict[str, str] = {
    "logo-pnju": "upi",
    "gpay": "gpay",
    "google_pay": "gpay",
    "google-pay": "gpay",
    "phonepe": "phonepe",
    "phone_pe": "phonepe",
    "phone-pe": "phonepe",
    "paytm": "paytm",
    "bhim": "bhim",
    "cred": "cred",
    "bharatpe": "bharatpe",
    "amazonpay": "amazonpay",
    "amazon_pay": "amazonpay",
}


class UPIAppDetector:
    """
    Calls the Roboflow hosted model to detect UPI app logos in screenshots.
    Returns the canonical provider slug or None.

    Hosted API: POST https://detect.roboflow.com/{workspace}/{project}/{version}
    Use the exact endpoint from Roboflow → Deploy → cURL (ROBOFLOW_UPI_MODEL_ID).

    Request options (see Roboflow object-detection docs):
    - Multipart file field ``file`` (preferred), or
    - Raw base64 body with ``Content-Type: application/x-www-form-urlencoded``
      and query param ``name=filename.jpg``.
    ``confidence`` is on a 0–100 scale (default 40).
    """

    def __init__(
        self,
        api_key: str,
        model_id: str = "document-classification/upi/1",
        confidence: int = 40,
    ) -> None:
        self.api_key = api_key
        self.model_id = model_id.strip().strip("/")
        self.confidence = confidence

    def detect(self, image_path: str) -> str | None:
        """
        Run logo detection on image_path.
        Returns the canonical provider slug (e.g. "phonepe") for the
        highest-confidence detection, or None if nothing found.
        """
        try:
            dbg = self.detect_with_debug(image_path)
            predictions = dbg.get("predictions", [])
            if not predictions:
                return None

            best = max(predictions, key=lambda p: p.get("confidence", 0))
            cls_raw = (
                best.get("class", "")
                .lower()
                .replace("-", "_")
                .replace(" ", "_")
                .strip()
            )
            provider = _CLASS_TO_PROVIDER.get(cls_raw)
            if provider:
                logger.info(
                    "UPI logo detected: class=%s → provider=%s (confidence=%.2f)",
                    cls_raw,
                    provider,
                    best.get("confidence", 0),
                )
            return provider
        except Exception:
            logger.exception("UPI logo detection failed — falling back to text-only")
            return None

    def detect_with_debug(self, image_path: str) -> dict:
        """
        Run Roboflow detection and return raw debug payload.
        Shape:
        {
          ok: bool,
          model_id: str,
          endpoint: str,
          status_code: int | None,
          predictions: list[dict],
          provider: str | None,
          best_class: str | None,
          best_confidence: float | None,
          error: str | None,
        }
        """
        out: dict = {
            "ok": False,
            "model_id": self.model_id,
            "endpoint": f"https://detect.roboflow.com/{self.model_id}",
            "status_code": None,
            "predictions": [],
            "provider": None,
            "best_class": None,
            "best_confidence": None,
            "error": None,
        }
        try:
            img_bytes = Path(image_path).read_bytes()
            suffix = Path(image_path).suffix.lower() or ".jpg"
            filename = f"upload{suffix if suffix in ('.jpg', '.jpeg', '.png', '.webp') else '.jpg'}"
            url = f"https://detect.roboflow.com/{self.model_id}"
            base_params = {"api_key": self.api_key, "confidence": self.confidence}

            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    url,
                    params=base_params,
                    files={"file": (filename, img_bytes, "application/octet-stream")},
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 405:
                    b64 = base64.b64encode(img_bytes).decode("ascii")
                    resp = client.post(
                        url,
                        params={**base_params, "name": filename},
                        content=b64,
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Accept": "application/json",
                        },
                    )
                out["status_code"] = resp.status_code
                resp.raise_for_status()

            body = resp.json()
            preds = body.get("predictions", []) or []
            out["predictions"] = preds
            if preds:
                best = max(preds, key=lambda p: p.get("confidence", 0))
                cls_raw = (
                    str(best.get("class", ""))
                    .lower()
                    .replace("-", "_")
                    .replace(" ", "_")
                    .strip()
                )
                out["best_class"] = cls_raw
                out["best_confidence"] = best.get("confidence", None)
                out["provider"] = _CLASS_TO_PROVIDER.get(cls_raw)
            out["ok"] = True
            return out
        except Exception as exc:
            out["error"] = str(exc)
            logger.exception("UPI logo debug detection failed")
            return out
