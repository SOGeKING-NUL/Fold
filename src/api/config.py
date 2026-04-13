import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> None:
    """Load simple KEY=VALUE pairs from .env into process env."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        # Prefer values from .env so local DATABASE_URL / tokens match the project file
        # even when the shell already defines empty or stale variables.
        if key and value:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    database_url: str
    telegram_bot_token: str
    telegram_webhook_secret: str
    roboflow_api_key: str
    roboflow_upi_model_id: str
    max_transaction_inr: float = 10_000_000.0  # ₹1 crore


def get_settings() -> Settings:
    _load_env_file()

    database_url = os.getenv("DATABASE_URL")
    telegram_bot_token = os.getenv("TELE_BOT_HTTP_API")
    telegram_webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    roboflow_api_key = os.getenv("ROBOFLOW_API_KEY", "")
    roboflow_upi_model_id = os.getenv(
        "ROBOFLOW_UPI_MODEL_ID", "document-classification/upi/1"
    )
    max_transaction_inr = float(os.getenv("MAX_TRANSACTION_INR", "1000000"))

    missing = []
    if not database_url:
        missing.append("DATABASE_URL")
    if not telegram_bot_token:
        missing.append("TELE_BOT_HTTP_API")
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(f"Missing required env variables: {missing_text}")

    return Settings(
        database_url=database_url,
        telegram_bot_token=telegram_bot_token,
        telegram_webhook_secret=telegram_webhook_secret,
        roboflow_api_key=roboflow_api_key,
        roboflow_upi_model_id=roboflow_upi_model_id,
        max_transaction_inr=max_transaction_inr,
    )
