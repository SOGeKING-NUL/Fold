# Stealth Fold - Current Working Architecture

## Overview

This project is an expense and income capture system that accepts **text**, **audio**, and **image** inputs from both API endpoints and Telegram, extracts structured transaction data, and posts ledger entries using double-entry accounting.

The current implementation uses a hybrid stack:

- Rule-based + NLP extraction for text normalization and categorization.
- OCR for image text extraction.
- Roboflow for UPI screenshot detection and provider hints.
- Local Ollama SLM for OCR-to-structured-data parsing.
- Ledger repository/service for account resolution and journal posting.

---

## Runtime Components and Tools

### API and Application

- **FastAPI** (`src/api/routes.py`): extraction endpoints (`/extract/text`, `/extract/audio`, `/extract/image`) and correction routes.
- **Uvicorn**: serves the app APIs.
- **Web dashboard service** (`src/api/controllers/web_controller.py`): session-based reporting APIs for the frontend.

### Input Processing

- **Text extraction layer**: `src/nlp/inference.py`
  - Entity parsing (amount/payment/category hints).
  - Category prediction with model fallback behavior.
- **Audio transcription**: `src/stt/transcriber.py` (Whisper-based).
- **OCR**: `src/ocr/extractor.py` (PaddleOCR + heuristics).
- **UPI visual detection**: `src/ocr/upi_detector.py` via Roboflow.
- **OCR structuring LLM**: `src/nlp/ollama_structurer.py` using local Ollama (`qwen2.5:3b-instruct` by default).

### Ledger and Persistence

- **Repository and posting logic**: `src/api/repositories/*`, `src/api/services/*`.
- **DB connections**: `src/api/db/connection.py` with retry/backoff for transient connectivity errors.
- **Accounting model**: journal-based posting with funding-account resolution.

---

## Environment and Config

Core settings are loaded from `.env` through `src/api/config.py`.

Important variables currently used:

- `DATABASE_URL`
- `ROBOFLOW_API_KEY`
- `ROBOFLOW_UPI_MODEL_ID`
- `OLLAMA_ENABLED`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
- `MAX_TRANSACTION_INR`
- `FOLD_WEB_SIGNING_SECRET`

---

## Current Processing Pipelines

## 1) Text Pipeline

Entry points:

- API: `/extract/text`
- Telegram: text messages and `/expense ...`

Flow:

1. Receive user text.
2. Run `TransactionExtractor` (`src/nlp/inference.py`) to extract:
   - amount
   - category
   - payment method/provider hints
   - account/bank hints when present
3. Pass extracted data to posting layer.
4. Ledger resolver selects funding account (explicit hint > instrument match > defaults).
5. Create journal entry and return confirmation + debug info.

Notes:

- Category can be overridden by user correction flow.
- Parser attempts to preserve explicit payment intent (`cash`, `upi`, bank name, etc.).

## 2) Audio Pipeline

Entry points:

- API: `/extract/audio`
- Telegram: voice notes/audio uploads

Flow:

1. Audio bytes are transcribed to text (Whisper transcriber).
2. Transcript is fed into the same text extraction pipeline as above.
3. Structured output is posted through the same ledger service.

Notes:

- Audio and text share the same downstream extraction + ledger code paths, so fixes in text parsing generally apply to audio as well.

## 3) Image Pipeline (Current Main Focus)

Entry points:

- API: `/extract/image`
- Telegram: image/photo receipts and UPI screenshots

Current flow:

1. **Roboflow first**: detect if image has UPI visual/provider cues.
2. **OCR extraction** (`ReceiptOCR`):
   - Preprocessing is intentionally disabled in current UPI-focused flow.
   - OCR lines are reconstructed spatially and parsed.
3. **Ollama structuring** (`OllamaStructurer`):
   - Raw OCR text + hints are sent to local model.
   - Model returns strict JSON fields such as:
     - amount
     - payment method
     - provider
     - bank account
     - cash flow
     - description
4. **NLP pass for category/context**:
   - LLM-hinted text is prepended to raw OCR blob.
   - NLP extractor runs mainly for category + fallback fields.
5. **Merge priority**:
   - Primary: LLM structured output.
   - Secondary: OCR parsed fields.
   - Fallback: NLP extracted fields.
6. **Ledger posting** uses merged result with instrument hints (`last4`, institution) where available.

Recent hardening for image accuracy:

- Added OCR guard to reject identifier/handle digits as amounts (e.g. `user1234@...` should not become `₹1234`).
- Continued filtering for bank-last4 and date-year numbers.
- Debug flags include amount source and LLM call/success status.

---

## Ledger Maintenance (How Entries Are Kept Correct)

The ledger maintains correctness through structured resolution order:

1. Determine transaction direction (`expense` or `income`).
2. Resolve funding/source account using strongest evidence first:
   - explicit user mention (`cash`, `slice`, `hdfc`, etc.)
   - receipt/UPI instrument signals (bank + last4)
   - payment method/provider cues
   - user defaults as final fallback
3. Validate amount boundaries (`MAX_TRANSACTION_INR`, positivity checks).
4. Post journal entries (debit/credit) and persist transaction metadata.
5. Return traceable response with journal id and debug context.

This layered approach is what prevents generic defaults (for example always charging one bank) when stronger account evidence exists in text/audio/image input.

---

## Observability and Debugging

Current debug outputs (especially via Telegram) include:

- amount source (`llm`, `ocr`, `nlp`)
- UPI evidence boolean
- detected payment provider
- receipt bank last4 (if found)
- LLM called/success flags
- raw transcript preview

These signals help quickly isolate whether issues are from OCR text quality, LLM structuring, merge logic, or ledger account resolution.

---

## Current Status Summary

- Roboflow-first UPI routing is active.
- OCR is active and feeds raw text to LLM.
- Ollama local model is integrated for OCR structuring.
- NLP remains active for category and fallback extraction.
- Ledger posting remains centralized and shared across API + Telegram.
- Recent OCR amount fix reduces false picks from handle/id digits.

For future tuning, the most impactful areas are:

- stricter success-screen amount anchoring (`paid`, `pay completed`, `received`)
- better OCR line segmentation on dark UPI screenshots
- additional account resolution rules for multi-bank users
