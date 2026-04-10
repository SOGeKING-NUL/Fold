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
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    database_url: str
    telegram_bot_token: str
    telegram_webhook_secret: str


def get_settings() -> Settings:
    _load_env_file()

    database_url = os.getenv("DATABASE_URL")
    telegram_bot_token = os.getenv("TELE_BOT_HTTP_API")
    telegram_webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

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
    )
