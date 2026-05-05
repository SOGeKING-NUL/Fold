"""
FastAPI Application Entry Point
================================
Launches the multi-modal financial extraction API server.

Endpoints:
    POST /api/v1/extract/text   — Extract from plain text (legacy/direct)
    POST /api/v1/extract/audio  — Extract from voice note (legacy/direct)
    POST /api/v1/extract/image  — Extract from receipt image (legacy/direct)
    POST /api/v1/correct        — Save a category correction

    POST /api/v1/web/extract/text  — Clerk-auth text (synchronous, <1s)
    POST /api/v1/web/extract/audio — Clerk-auth audio (synchronous, ~3-5s)
    POST /api/v1/web/extract/image — Clerk-auth image (synchronous, ~5-7s)

Run with:
    uvicorn src.api.main:app --reload --port 8000
"""

import os
import sys
import logging

# ─── Ensure src/ is on the Python path ───────────────────────────────────
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Load environment variables FIRST
from api.config import _load_env_file
_load_env_file()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from api.controllers.ledger_controller import router as ledger_router
from api.controllers.web_controller import router as web_router
from api.controllers.extraction_controller import router as extraction_router
from api.db.connection import run_migrations

_logger = logging.getLogger(__name__)

# ─── Create Application ─────────────────────────────────────────────────
app = FastAPI(
    title="Fold — Financial Ledger Extraction API",
    description=(
        "Multi-modal API that extracts structured financial data "
        "(amount, category, payment method, bank account) from "
        "voice notes, receipt images, and text messages."
    ),
    version="1.0.0",
)

# ─── CORS for Next.js dashboard ─────────────────────────────────────────
_web_origins = os.getenv("FOLD_WEB_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _web_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routes ────────────────────────────────────────────────────
app.include_router(router)
app.include_router(ledger_router)
app.include_router(web_router)
app.include_router(extraction_router)


@app.on_event("startup")
def startup_event():
    # ensure_schema() only creates missing tables; it does not wipe data.
    # For a one-time full reset set FOLD_RESET_DATABASE=1, restart, then unset.
    run_migrations()
    
    # Log all registered routes for debugging
    _logger.info("✅ Application startup complete")
    _logger.info("Registered routes:")
    for route in app.routes:
        if hasattr(route, 'path'):
            _logger.info(f"  {route.path} - {route.name if hasattr(route, 'name') else 'unnamed'}")


# ─── Health Check ────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "fold-extraction-api"}


# ─── Direct Launch ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
