"""
FastAPI Application Entry Point
================================
Launches the multi-modal financial extraction API server.

Endpoints:
    POST /api/v1/extract/text   — Extract from plain text
    POST /api/v1/extract/audio  — Extract from voice note (.ogg)
    POST /api/v1/extract/image  — Extract from receipt image (.jpg/.png)
    POST /api/v1/correct        — Save a category correction

Run with:
    uvicorn src.api.main:app --reload --port 8000

Or directly:
    python src/api/main.py
"""

import os
import sys

# ─── Ensure src/ is on the Python path ───────────────────────────────────
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from fastapi import FastAPI
from api.routes import router

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

# ─── Register Routes ────────────────────────────────────────────────────
app.include_router(router)


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
