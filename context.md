# Fold Backend Context (V2)

This is the persistent implementation memory for the current backend state after the Ledger + Telegram V2 upgrade.

## Why V2 Was Built

The earlier backend was expense-only and command-minimal. It could post basic expenses, but it did not support:

- income and investment flows
- account setup with opening balances
- account-to-account transfer flows
- weekly/monthly financial reporting
- inline Telegram dashboard UX
- reliable single-transaction journal posting

V2 was implemented to make the backend a proper accounting core instead of a single-use expense logger.

## Core Product Principles

1. Ledger is source of truth for reports.
2. Double-entry accounting is enforced at write-time.
3. One currency model (`INR`) for now to reduce complexity.
4. Telegram is treated as a first-class client, not a thin command relay.
5. Extraction (OCR/STT/NLP) stays separate from accounting correctness.

## Implemented V2 Areas

### 1) Database Reset + Schema Hardening

File: `src/api/db/connection.py`

What changed:

- Startup schema hook **`ensure_schema()`** creates finance tables with **`CREATE TABLE IF NOT EXISTS`** so data persists across restarts (including `uvicorn --reload`). A **full wipe** is opt-in only: set **`FOLD_RESET_DATABASE=1`** (or `true`/`yes`) for one restart when you intentionally want a clean slate, then unset it.
- Added constrained transaction typing:
  - `expense`, `income`, `investment`, `transfer`, `opening_balance`
- Added constrained account typing:
  - `asset`, `liability`, `equity`, `income`, `expense`, `investment`
- Added `metadata_json` to `journal_transactions` for category/payment annotations.
- Idempotency uniqueness is now user-scoped (`user_id`, `source`, `external_ref`).

Why:

- Reset was explicitly chosen to avoid carrying old assumptions.
- Constrained enums prevent silent invalid accounting classes.
- Metadata allows reporting/breakdowns without denormalizing core tables.

Important operational note:

- Prefer **never** leaving `FOLD_RESET_DATABASE` enabled in production; it drops all ledger data.
- Longer term, replace ad-hoc SQL with **versioned migrations** (e.g. Alembic) for additive schema changes.

### 2) Atomic Journal Posting Core

Files:

- `src/api/repositories/ledger_repository.py`
- `src/api/services/ledger_service.py`

What changed:

- Added `create_balanced_journal(...)` that posts journal header + entries in one DB transaction.
- Added pre-write balancing check (`debits == credits`).
- Account creation/upsert is integrated inside the same flow.

Why:

- Prevent partial writes across journal and entries.
- Ensure every posted transaction is accounting-balanced by construction.

### 3) Expanded Ledger API Surface

Files:

- `src/api/schemas.py`
- `src/api/controllers/ledger_controller.py`
- `src/api/services/ledger_service.py`

Implemented endpoints:

- `POST /api/v1/ledger/expense`
- `POST /api/v1/ledger/income`
- `POST /api/v1/ledger/investment`
- `POST /api/v1/ledger/transfer`
- `POST /api/v1/ledger/opening-balance`
- `POST /api/v1/ledger/accounts`
- `GET /api/v1/ledger/accounts/{user_ref}`
- `GET /api/v1/ledger/balances/{user_ref}`
- `GET /api/v1/ledger/reports/weekly/{user_ref}`
- `GET /api/v1/ledger/reports/monthly/{user_ref}`
- `GET /api/v1/ledger/reports/cashflow/{user_ref}`
- `GET /api/v1/ledger/reports/breakdown/{user_ref}`
- `GET /api/v1/ledger/transactions/{user_ref}`

Why:

- This maps directly to required product workflows: outgoing, incoming, invested, and moved funds.
- Reports and history are API-first so Telegram and any future UI can use the same backend contract.

### 4) Reporting Behavior (Ledger-Only)

File: `src/api/repositories/ledger_repository.py`

Implemented:

- Weekly and monthly summary totals:
  - `income_minor`
  - `expense_minor`
  - `investment_minor`
  - net cashflow
- Breakdowns by:
  - account
  - payment method (from metadata)
  - category (from metadata)
- Transaction history listing with pagination controls (`limit`, `offset`).

Why:

- Financial insights must come from posted ledger entries, not model guesses alone.
- Grouped breakdowns power dashboard style reporting and decision support.

#### Double-entry: why `ledger_entries` has more rows than “actions”

Each **business event** is one row in **`journal_transactions`** (e.g. opening balance = journal #3, one expense = journal #4).

Each such journal posts **at least two** rows in **`ledger_entries`**: one **debit** and one **credit** of the same amount (balanced). So:

- 1 opening balance + 1 expense ⇒ **2 journals** and **4 ledger lines** — this is correct, not duplicate data.
- **Category correction** updates the existing expense line and metadata; it does **not** add another journal.

If you ever see **twice as many `journal_transactions` rows** as you expect (e.g. four journals for two actions), that would indicate a bug or double-post; row count in **`ledger_entries` alone is not 1:1 with user actions.**

### 5) Telegram Dashboard V2

Files:

- `src/api/services/telegram_service.py`
- `src/api/controllers/telegram_controller.py`
- `src/api/repositories/ledger_repository.py` (`telegram_sessions` usage)

What changed:

- `/start` now sends inline dashboard buttons:
  - Add Expense
  - Add Income
  - Add Investment
  - Transfer
  - Weekly Report
  - Monthly Report
  - Balance Snapshot
  - Accounts
- Callback routing implemented for dashboard/report/account actions.
- Session storage now used to persist funding-account preference for expenses.
- Backward-compatible text commands retained:
  - `/expense`
  - `/income`
  - `/investment`
  - `/transfer`
  - `/opening`
  - `/balance`

Why:

- Inline dashboard reduces command memorization friction.
- Session-backed account preference allows practical multi-account spend routing.

#### Category correction (Telegram)

After an expense is recorded (AI path or `/expense`), the bot shows **Change category** plus the main dashboard. Tapping **Change category** swaps the inline keyboard to **category picks** and **« Back**; choosing a category (or Back) uses **`editMessageReplyMarkup`**. A category choice calls **`LedgerService.reassign_expense_category`** / **`LedgerRepository.reassign_expense_journal_category`**, which:

- moves the **expense debit** line to the correct `expense_*` account (so balances stay consistent with the new label), and  
- updates **`metadata_json`** (`category`, `category_user_corrected`).

This is human feedback on top of model predictions, stored in Postgres today.

#### Planned (not implemented): correction → CSV for retraining

We want a **closed loop** for NLP accuracy: every time a user fixes a category, that example is **gold-label data** (raw or OCR/STT text → user-chosen category). The intended pipeline (design only for now):

1. **Hook** on successful `reassign_expense_journal_category` (or a nightly job reading `metadata_json->'category_user_corrected'`).  
2. **Append a row** to a **CSV** (or Parquet) training export, e.g. columns: `occurred_at`, `user_ref`, `journal_id`, `source`, `model_category`, `corrected_category`, `description` / `text_transcript`, optional `amount`, `payment_method`, `modality` (text/audio/image).  
3. **Offline**: merge export with existing EDA / synthetic datasets, **fine-tune** DistilBERT (or successor), redeploy `my_finetuned_distilbert`.  
4. Optionally also call or mirror **`POST /api/v1/correct`** / `category_overrides.json` for **immediate** recall on repeated merchants — complementary to bulk retraining.

This is **not full reinforcement learning** in the RL control-theory sense; it is closer to **active learning** / **human-in-the-loop supervision** or **RLHF-style preference data** (corrections as implicit “which label is right”). Naming it “RL technique” in product language is fine as long as engineering treats it as **supervised fine-tuning from logged corrections**.

**Implementation intentionally deferred** until we settle retention (PII in exports), deduplication, and whether the append is synchronous vs async worker.

#### Reports — current behavior and implementation plan (Telegram)

**Today (implemented):**

- Callbacks **`report:weekly`** and **`report:monthly`** call **`LedgerService.get_enriched_period_report`**, using the same windows as before (**7-day** rolling weekly; **monthly** = **`max(1, day_of_month)`** days rolling, matching **`get_monthly_report`**).
- One Telegram message: **UTC range hint** → **totals** (income / expense / investment / net) → **top categories** → **top accounts** → **by payment method** (non-zero lines only; per-section caps). Message truncated near 4000 chars if needed.

**Next steps (plan):**

1. **Export** — CSV/PDF and `sendDocument`; optional scheduled email.
2. **Charts** — matplotlib/plotly → `sendPhoto`.
3. **Calendar-aligned month** — optional alternate window (1st → today) if product wants statement-style periods instead of rolling `N` days.

API clients can already use **`GET /api/v1/ledger/reports/breakdown/{user_ref}`** (with `period`, `group_by`) and **`GET /api/v1/ledger/transactions/{user_ref}`** for custom UIs; Telegram is the thin presentation layer on top.

## Accounting Templates Implemented

Inside `LedgerService`:

- Expense:
  - debit expense account
  - credit funding account
- Income:
  - debit destination asset
  - credit income account
- Investment:
  - debit investment account
  - credit funding account
- Transfer:
  - debit destination account
  - credit source account
- Opening balance:
  - debit target account
  - credit opening equity account

Why:

- These templates encode domain intent while preserving strict double-entry mechanics.

## Data Flow Overview

```mermaid
flowchart TD
  telegramUser[TelegramUser] --> webhook[/api/v1/webhooks/telegram]
  webhook --> telegramSvc[TelegramService]
  telegramSvc --> sessions[(telegram_sessions)]
  telegramSvc --> ledgerSvc[LedgerService]
  ledgerSvc --> ledgerRepo[LedgerRepository]
  ledgerRepo --> db[(Postgres)]

  apiClient[APIClient] --> ledgerApi[/api/v1/ledger/*]
  ledgerApi --> ledgerSvc
```

## Validation Performed During V2 Implementation

- Health endpoint check (`/health`) succeeded.
- Ledger endpoint smoke tests succeeded:
  - account creation
  - expense posting
  - weekly/monthly report fetch
  - breakdown and transactions fetch
- Telegram webhook smoke test succeeded with valid secret token:
  - `/start` payload accepted and handled.

## What Still Needs Next Iteration

1. Move from `ensure_schema()` bootstrap to **versioned migrations** (Alembic or equivalent) for additive changes.
2. Add explicit account-type mapping for `/transfer` command parsing in Telegram (currently defaults to asset in quick command path).
3. Add richer multi-step Telegram setup wizard for creating custom accounts and opening balances via buttons/forms only.
4. Add stronger idempotency and replay protections for webhook updates (`ingestion_events` integration not fully wired).
5. Add integration tests for all journal template paths and report filters.
6. **Training export pipeline:** append category corrections to CSV (or object store) for batch fine-tuning; see “Planned (not implemented)” under Telegram V2 above.

## Non-Goals (Still Deferred)

- Multi-currency accounting.
- Full media-auto ingestion in Telegram for photo/voice posting into ledger automatically.
- Advanced forecasting or ML-based budgeting.

# Fold Backend Context and Engineering Memory

This document is the persistent implementation memory for the Fold backend. It explains not only what is implemented, but why those choices were made, where behavior currently lives in code, and what is intentionally not implemented yet.

## Project Intent

Fold is building a multi-input expense capture backend optimized for Indian/Hinglish usage. The system ingests text, voice, and receipt images, extracts transaction fields, and posts accounting-safe ledger entries.

Design philosophy:

- Use strong off-the-shelf models for perception (OCR/STT).
- Keep the orchestration and data guarantees in our backend.
- Standardize output shape across modalities so downstream systems stay simple.

## Current Backend Surface (What Exists)

Main app entrypoint: `src/api/main.py`

Routers currently mounted:

- `src/api/routes.py` -> `/api/v1` extraction + correction APIs
- `src/api/controllers/ledger_controller.py` -> `/api/v1/ledger/*`
- `src/api/controllers/telegram_controller.py` -> `/api/v1/webhooks/telegram`

Health endpoint:

- `GET /health` returns service status.

Startup behavior:

- `run_migrations()` runs from `src/api/db/connection.py`: by default **`ensure_schema()`** (create-if-missing, **no data wipe**). Destructive reset only when **`FOLD_RESET_DATABASE=1`**.

## Environment and Config Decisions

Config source: `src/api/config.py`

Required env variables:

- `DATABASE_URL`
- `TELE_BOT_HTTP_API`

Optional but strongly recommended:

- `TELEGRAM_WEBHOOK_SECRET`

Why this approach:

- Keep deployment and local dev simple with `.env` fallback loading.
- Hard-fail when DB/token are absent to avoid silent runtime partial states.
- Make webhook secret optional to reduce local setup friction, but enforce when set.

## Unified Extraction Contract (Core API Design)

Extraction APIs return a common response (`TransactionResponse` in `src/api/schemas.py`) with:

- `status`
- `source`
- `data` containing:
  - `text_transcript`
  - `amount`
  - `category`
  - `payment_method`
  - `bank_account`

Why this was implemented:

- Downstream services (ledger/chat/analytics) should not care whether source was text, audio, or image.
- One schema allows easier testing in `/docs`, cleaner clients, and fewer branching bugs.

## Text Pipeline (`POST /api/v1/extract/text`)

Implementation: `src/api/routes.py`

Flow:

- Input text goes directly to `TransactionExtractor.extract()`.
- Returns normalized structured fields.

Why:

- Text path is the baseline and fastest path.
- It is used for both direct client integration and fallback debug/testing.

## Audio Pipeline (`POST /api/v1/extract/audio`)

Implementation: `src/api/routes.py` + `src/stt/transcriber.py`

Flow:

1. Upload is written to a temp file.
2. Whisper transcribes audio (`VoiceTranscriber` with model `small`).
3. Transcript is passed into NLP extractor.
4. Temp file is deleted in success and error paths.

Why:

- Temp files are required because Whisper/FFmpeg decode from file path reliably.
- Deleting temp files avoids disk growth and accidental PII persistence.
- STT only returns transcript by design; NLP owns extraction logic so business parsing stays centralized.

## Image Pipeline (`POST /api/v1/extract/image`)

Implementation: `src/api/routes.py` + `src/ocr/extractor.py` + NLP module

Flow:

1. Uploaded image saved to temp file.
2. OCR runs (`ReceiptOCR.process_receipt`).
3. OCR gives `all_lines`, `key_lines`, and parsed amount/payment guess.
4. Full OCR text wall is fed to NLP for category and fallback extraction.
5. Merge policy:
   - amount: OCR first, NLP fallback
   - payment_method: OCR first; if OCR=`unknown`, NLP fallback
   - category: NLP
6. Temp image file is deleted.

Why this hybrid merge exists:

- OCR is strongest for visually explicit totals and mode clues on receipts.
- NLP is stronger for semantic category inference from noisy text.
- Hybrid arbitration reduces false positives from any single subsystem.

## How Images Are Saved (Current Behavior)

Current behavior in API routes:

- Images are not permanently stored by backend.
- They are written to an OS temp path for processing only.
- Temp files are removed before response completion.

Implication:

- There is no built-in image archive/history in DB or filesystem.
- If persistent media storage is needed, that is a future feature (object storage + retention policy).

## OCR Architecture Rationale

Implementation: `src/ocr/extractor.py`

Key mechanisms:

- Optional preprocessing pipeline exists (upscale/CLAHE/denoise/sharpen/binarize).
- Spatial sorting reconstructs lines from OCR bounding boxes.
- Heuristic filtering isolates key financial lines.
- Amount extraction prioritizes total-like lines; payment mode normalization maps to `upi`, `card`, `cash`, `unknown`.

Why this is implemented:

- Raw OCR output is unordered word fragments.
- Financial extraction requires structure reconstruction, not just plain text dumping.
- Payment normalization supports consistent downstream enums.

Current nuance:

- Route currently calls `use_preprocessing=False` for image extraction.
- This reflects practical preference for raw image OCR behavior in current flow.

## STT Architecture Rationale

Implementation: `src/stt/transcriber.py`

Key mechanisms:

- Whisper local model (`small`) loaded once.
- Hindi language mode with Hinglish domain prompt anchoring.
- Output is transcript only.

Why:

- Whisper handles code-switching well enough for this use case.
- Domain prompt reduces bad lexical drift/hallucinated phrasing.
- Keeping STT focused on transcription prevents duplicated parsing logic across modules.

## NLP Architecture Rationale

Implementation: `src/nlp/inference.py`

Core extraction strategy:

- Category:
  - first check `category_overrides.json` user memory
  - otherwise run DistilBERT classifier
  - if outlier label, fallback to default category
- Amount:
  - Hindi multiplier words
  - currency-tagged regex
  - largest-number fallback
- Payment method:
  - dictionary match for UPI/Card/Cash terms
- Bank account:
  - dictionary match on known Indian bank names

Why:

- Real user utterances are noisy and multilingual.
- Model-only extraction is brittle without override memory.
- Rule+model hybrid provides practical robustness in small-data environments.

## Category Correction Memory (`POST /api/v1/correct`)

Implemented as a persistent override map in `category_overrides.json`.

Why:

- User corrections are high-value signal.
- Persisting corrections creates compounding accuracy improvements without retraining.

## Ledger System (Double-Entry Backbone)

Implementation:

- Controller: `src/api/controllers/ledger_controller.py`
- Service: `src/api/services/ledger_service.py`
- Repository: `src/api/repositories/ledger_repository.py`
- DB schema: `src/api/db/connection.py`

Current capabilities:

- Post expense (`POST /api/v1/ledger/expense`)
- Fetch balances (`GET /api/v1/ledger/balances/{user_ref}`)

Ledger write logic:

- Converts amount to minor units.
- Ensures user and default accounts exist.
- Writes one journal transaction.
- Writes two ledger entries (debit + credit).

Why:

- Double-entry model keeps accounting integrity and auditability.
- Minor unit storage avoids float precision drift.

Known design caveat:

- Funding account is created with `account_type="asset"` in service logic, even when code may imply liabilities (e.g., `card_liability`). This should be revisited for strict accounting semantics.

## Telegram Webhook Integration

Implementation:

- Controller: `src/api/controllers/telegram_controller.py`
- Service: `src/api/services/telegram_service.py`
- Secret middleware: `src/api/middleware/telegram_security.py`

Security model:

- If `TELEGRAM_WEBHOOK_SECRET` is configured, webhook requires matching `X-Telegram-Bot-Api-Secret-Token`.

Current bot command support:

- `/start`, `/add` -> sends payment method inline keyboard
- `/expense <amount> <description>` -> posts ledger expense
- `/balance` -> returns balances
- callback `pay:*` -> confirmation message

Why this narrow command scope:

- Fastest path to validate webhook + ledger loop.
- Keeps conversational state complexity low in current iteration.

## Media Auto-Detection in Telegram (Current State)

Not implemented yet.

What exists now:

- Telegram handler checks `update["message"]["text"]` and `callback_query`.
- No handling for `photo`, `document`, `voice`, or media download via Telegram file APIs.

So, if a user "just sends an image" to bot today:

- It will not trigger the OCR extraction pipeline automatically.
- The message falls through to help/ignored behavior depending on payload shape.

## Database Tables Currently Auto-Migrated

From `ensure_schema()` / optional reset (`FOLD_RESET_DATABASE`):

- `users`
- `accounts`
- `payment_profiles`
- `journal_transactions`
- `journal_media`
- `telegram_expense_pending_media`
- `ledger_entries`
- `telegram_sessions`
- `ingestion_events`

Why include more than current active paths:

- `telegram_sessions` and `ingestion_events` provide a foundation for idempotency/stateful chat expansion and source event tracking.

## `/docs` Testing Philosophy

The OpenAPI docs are intended as a first-line system verification surface.

Recommended checks:

1. `GET /health`
2. Extraction endpoints (`text`, `audio`, `image`)
3. Ledger write + read endpoints
4. Telegram webhook behavior via real Telegram updates (not synthetic docs call only)

Why:

- This sequence validates model loading, file handling, DB writes, and orchestration in realistic order.

## Known Gaps and Next High-Value Steps

1. Telegram media ingestion:
   - add handlers for `voice` and `photo`
   - fetch media with Telegram `getFile` + file download
   - route to existing `/extract/audio` and `/extract/image` pipeline logic
2. Persistent media strategy:
   - optional object storage path for receipts/audio with retention controls
3. Accounting semantics:
   - preserve true account type on custom funding codes
4. Error envelopes:
   - standardize all errors to `ErrorResponse`
5. Observability:
   - structured logs and per-stage latency timing (OCR, STT, NLP, DB)

## Non-Goals in Current Build

- Full conversational agent state machine
- Human-in-the-loop reconciliation dashboard
- Long-term media archival
- Multi-tenant auth and RBAC

These are intentionally deferred to keep the core extraction + ledger loop stable first.

That is a **100% correct and highly efficient** engineering strategy. By using "off-the-shelf" models for the heavy lifting (OCR and Speech-to-Text) and focusing your "from scratch" effort on the **NLP Intent Layer**, you’re following the 80/20 rule of AI development.

Building a custom OCR or STT engine is a multi-year research project. Building a custom Hinglish Transaction Classifier is a high-value, specialized weekend-to-month project.

### Why this pipeline works for India:
The "Indo-Western" nature of Indian spending means your data pipeline needs to be flexible. Here is how your proposed architecture looks in practice:



---

### 1. The Dataset & Cleaning
The **Indian Banking Transaction Dataset** (like the one with 11k narrations) is a goldmine because it contains the weird abbreviations banks use (e.g., `NPR/MAB/` or `UPI/9234...`).
* **The "Hinglish" Hack:** Since you are adding synthetic data, don't just add pure Hindi. Use **Template-based Generation**.
    * *Template:* `[Merchant] pe [Amount] ka [Category] kharcha kiya`
    * *Result:* "Amazon pe 500 ka shopping kharcha kiya."
* **Cleaning:** Ensure you strip out the "noise" (Transaction IDs, timestamps) before feeding it to your NLP layer so the model focuses on the *semantics* (Category and Merchant).

### 2. The OCR Strategy (Receipts)
Since you are using off-the-shelf models, I recommend **PaddleOCR** or **Surya OCR**.
* **Why?** They have excellent support for Indic scripts (Devanagari) and handle "noisy" images (crumpled receipts) better than Tesseract.
* **The Catch:** OCR will give you a "word soup." You will need a small logic layer to find the **Total Amount**. Usually, looking for the largest number near the bottom of the text works 90% of the time.

### 3. The STT Layer (Whisper)
**Whisper** is actually surprisingly good at Hinglish out of the box because it was trained on vast amounts of multilingual web data.
* **Pro-Tip:** Use the `base` or `small` version of Whisper. It’s fast enough to run on a decent phone/laptop and handles "Chai pe 20 rupaye diye" perfectly.

### 4. The "From Scratch" NLP Layer
Since you have ~11k rows + synthetic data, you shouldn't build a literal "from scratch" neural net (as in, training your own embeddings). That would require millions of rows.
* **The Better Way:** Use a **DistilBERT** or a **Bi-LSTM** and fine-tune it specifically on your cleaned transaction dataset. 
* **Task:** Your NLP layer should perform **Joint Intent & Slot Filling**:
    1.  **Intent:** Is this an Expense, Income, or Transfer?
    2.  **Slots:** Extract `Amount`, `Category`, and `Entity`.

---

### Implementation Checklist
| Component | Recommendation | Why? |
| :--- | :--- | :--- |
| **STT** | OpenAI Whisper (`base.en` or `small`) | SOTA for Hinglish audio. |
| **OCR** | PaddleOCR (Multilingual) | Best open-source Indic script support. |
| **NLP** | Bi-LSTM + CRF or DistilBERT | Lightweight, handles code-switching well. |
| **Database** | Supabase (PostgreSQL) | Since you're already using it, it's perfect for storing these JSON results. |

### The "Silent" Challenge: Spellings
In Hinglish, people spell phonetically. "Kharcha," "Khrcha," and "Kharch" are all the same. When generating your synthetic data, make sure to **deliberately introduce typos**. This will make your NLP layer "robust" rather than "rigid."

Does this align with how you were planning to structure the code, or were you thinking of a more traditional Machine Learning approach (like Random Forest) for the NLP layer?

---

### Update: Dataset Generation & EDA Readiness
The synthetic dataset (`eda_dataset.csv`) has been successfully generated using the aforementioned strategy. 
* **Hinglish Synthesis:** For the ~1k original English rows, we generated ~1.5k Hinglish templates incorporating the phonetic typos discussed above.
* **Intentional Outliers for EDA:** To pressure-test data-cleaning pipelines prior to training, 150 highly corrupted rows (e.g., negative amounts, string-based amounts like "five hundred", misspelled payment methods, and null variables) have been intentionally injected alongside two noisy dummy columns (`location` and `notes`).

---

### Update: Visual Receipt Extraction (OCR Pipeline)
To handle physical receipts and digital payment screenshots, we built a 4-step OCR Extraction Pipeline (`src/ocr/extractor.py`). 
We chose to build a targeted OCR pipeline rather than feeding raw images into a multimodal LLM (like GPT-4V) to reduce latency and API costs, while retaining complete control over the data format before it hits our NLP classifier.

1. **Intensive Preprocessing (OpenCV):** Receipts are notoriously noisy. We implemented a rigorous image cleaning pipeline (Grayscaling -> CLAHE Contrast Enhancement -> Denoising -> Sharpening -> Otsu Binarization). This ensures shadows and bad lighting don't destroy the text.
2. **Text Extraction:** Using an OCR engine to generate bounding boxes (coordinates) and raw text strings.
3. **Custom Spatial Sorting:** OCR engines return "Word Soup". To combat this, we built a custom algorithm to calculate the center Y-coordinate of every text box. It dynamically groups text boxes sitting on the same horizontal plane (adjusting for font height) and sorts them left-to-right. This successfully recreates logical "rows" (e.g., aligning a dish name with its price on the far right).
4. **Heuristic Filter:** We scan these reconstructed rows for keywords (`Total`, `Cash`, `Amount`, `₹`) to extract only the 1-2 lines harboring the final amount. This prevents our NLP model from being overwhelmed by the entire 50-line receipt.

**OCR Engine Note (EasyOCR vs. PaddleOCR):** During local development, we temporarily utilized `EasyOCR` instead of `PaddleOCR` as a fallback because installing PaddlePaddle on local Windows environments often throws severe C++ build and pip dependency lock errors. However, **PaddleOCR is vastly superior for receipt processing**. It uses structured PP-OCRv4 models that are significantly more accurate at reading fine English print, decimal points, and symbols on receipts than EasyOCR. For production (on a Linux server or Docker), the system must strictly use PaddleOCR.

---

### Update: Migration to PaddleOCR & Architecture Refinement
We have since successfully resolved the local Windows build constraints and fully migrated `extractor.py` to **PaddleOCR 2.9 (anchored by PaddlePaddle 2.6.2)**. This specific versioning strategy was chosen to explicitly bypass a catastrophic C++ DLL lock crash (`ConvertPirAttribute2RuntimeAttribute`) triggered by Paddle 3's new experimental execution graph hitting standard Windows environments or interacting poorly with `albumentations` loading PyTorch. 

During the migration, we discovered two critical architectural learnings:
1. **Raw Processing vs. Preprocessing:** The intensive OpenCV pipeline that served as a "crutch" to highlight text for EasyOCR actually *degraded* PaddleOCR's performance. PaddleOCR utilizes profound internal Convolutional Neural Networks (CNNs) trained on real-world raw photographs, and forcibly applying Otsu binarization stripped out the subtle pixel gradients it relies upon to distinguish noise from characters. We moved to **Raw Matrix Processing**, wildly improving the engine's capability to read floating-point decimals accurately without hallucinating random characters.
2. **Final Intent Parsing:** At the end of the spatial sorting and keyword filtering algorithm, we appended a final `extract_payment_details` Regex validation method. Instead of handing the NLP layer raw strings, `extractor.py` now internally scans the filtered keys for the largest valid monetary float mapping to the label "Total", alongside parsing standard mode keywords (`cash`, `upi`, `card`). It returns a meticulously structured JSON object (e.g., `{"amount": 185.0, "payment_method": "cash"}`). This entirely shields our future NLP architecture from having to wrestle with OCR logic constraints.

### Example: How the Heuristic Filter Handles Ambiguous Lines
**Input RAW Key Line:** 
`>> Total : 4.00 1450.00`

In this example (from `receipt5.jpg`), the word `Total` is structurally adjacent to both the quantity (`4.00`) and the final price (`1450.00`). 
Instead of a simple regex that grabs the *first* number it sees (which would fail by extracting `4.00`), our `extract_payment_details` regex strictly extracts *every* valid float on lines containing `Total/Payable`. It generates an array of candidates: `[4.0, 1450.0]`. 

Because it is evaluating a designated "Total" line, it applies `max([4.0, 1450.0])`, perfectly bypassing quantities and discounts to output the true JSON:
{
    "amount": 1450.0,
    "payment_method": "unknown"
}
```

### Payment Method Normalization (ENUMs)
Because UPI screenshots contain diverse merchant tools (BHIM, PhonePe, GPay, Paytm, Cred) and physical receipts mention specific card networks (Visa, Mastercard, Amex), the `extract_payment_details` module normalizes these downstream. It strictly maps any found payment application to one of three final `ENUM` states: 
* `"upi"`
* `"card"`
* `"cash"`
* `"unknown"` (Fallback)

---

### Update: Voice Note Extraction (STT Pipeline)
To handle spoken Hinglish voice notes (the second major input channel alongside receipt images), we built a Speech-to-Text pipeline (`src/stt/transcriber.py`) using **OpenAI Whisper** running locally.

#### Why Whisper?
Whisper was trained on 680,000 hours of multilingual audio data scraped from the web. Unlike Google STT or AWS Transcribe, which require explicit language selection and struggle with code-switching, Whisper natively handles **Hinglish** — the fluid mix of Hindi and English that Indian users default to when speaking about money (e.g., "Swiggy se do sau pachaas rupaye ka order kiya, UPI se pay kiya").

#### Architecture (3 Steps)
The module mirrors the OCR extractor's structure exactly:

1. **Transcription (Whisper `base` model):** The audio file (.ogg, .wav, .mp3, etc.) is decoded via FFmpeg and passed to Whisper's encoder-decoder transformer. We inject a **domain prompt** — a pre-written Hinglish banking sentence — into Whisper's `initial_prompt` parameter. This is a critical engineering trick: it anchors the model's decoder latent space to our financial vocabulary, preventing it from force-translating Hindi words into English or hallucinating irrelevant text. We set `language="hi"` to keep the decoder in Hindi mode (which naturally preserves Hinglish code-switching).

#### Output Format
The `process_audio()` method simply returns a dict with the raw transcript:
```json
{
    "transcript": "Spent 3000 rupees on shopping."
}
```
*Note: We deliberately decided against attempting complex regex amount/payment extraction within the STT module itself. Because the downstream Artificial NLP Layer will be explicitly trained to parse intent and extract entity slots from Hinglish sentences, we only require Whisper to deliver an accurate string, delegating all intelligence to the NLP classifier.*

#### Dependencies & Environment Notes
* **openai-whisper** (installed via `pip install openai-whisper`). This is the *local* model, not the OpenAI API — no API key needed, no network calls during inference.
* **FFmpeg 8.1** (installed via `winget install Gyan.FFmpeg`). Required by Whisper to decode audio containers (OGG/Opus from WhatsApp, M4A from iPhone voice memos, etc.) into raw PCM waveforms. Must be on the system PATH.
* **torch** (pulled automatically by whisper). We are using the CPU-only variant (`fp16=False` in transcribe config) to avoid CUDA dependency on development machines.
* **Model size:** Using `base` (139 MB download, ~1 GB RAM at inference). Can be upgraded to `small` (461 MB) for higher accuracy if hardware allows.

---

### Update: Hybrid Payment Tracking (NLP + UX)
Extracting the `payment_method` exclusively from free-form WhatsApp voice notes introduces a vulnerability. Users often say "Zomato pe 500 ka kharcha kiya" but completely omit *how* they paid (UPI, cash, etc.).

Instead of blindly defaulting to "unknown" and corrupting the financial database, we have agreed on a **Hybrid Architecture (NLP layer + Chatbot UX)**:

1. **Attempt NLP Extraction First:** Deep inside the NLP Inference layer, we will run a specialized Regex/Dictionary matcher against the transcript. It scans for explicit mentions:
   * **UPI:** `"upi", "gpay", "paytm", "phonepe", "bhim", "cred"`
   * **Card:** `"card", "visa", "mastercard", "amex"`
   * **Cash:** `"cash", "naqad", "nakd"`
2. **Interactive WhatsApp Fallback:** If the NLP layer returns `payment_method: null` (meaning the user didn't explicitly vocalize it), the system does **not** fail. Instead, the backend will trigger a specific WhatsApp Interactive Message containing three UI buttons: `[ 💵 Cash ]`, `[ 📱 UPI ]`, `[ 💳 Card ]`.
3. **Database Finalization:** Once the user taps the button, the webhook receives the payload and completes the transaction row in the database.

This strategy guarantees 100% data completion while maintaining a frictionless UX.

---

### Update: Framework Decision (PyTorch vs. TensorFlow)
For the Deep Learning NLP Layer, we are utilizing **PyTorch** via HuggingFace Transformers, deliberately avoiding TensorFlow. The core reasons are:

1. **Ecosystem Dominance:** In modern NLP (especially post-2022 LLMs and Transformer variants), PyTorch has become the undisputed industry standard. Over 90% of state-of-the-art models released on HuggingFace are natively built in PyTorch. Finding TensorFlow implementations of modern Indic-language or Hinglish optimized sequence classifiers is often difficult and prone to bugs.
2. **Environment Synchronization:** Our STT layer (OpenAI Whisper) natively relies on the `torch` backend. By selecting PyTorch for the NLP DistilBERT classifier, we prevent monolithic environment bloat. If we introduced TensorFlow, the production deployed server would be forced to house *both* massive 2GB+ deep learning frameworks simultaneously, catastrophically increasing RAM footprint and cold-start latency.
3. **Pythonic Extensibility:** PyTorch's dynamic computational graph structure (`Eager Execution`) feels like standard Python, making it significantly easier to debug model gradients or tweak the internal loss functions during Colab fine-tuning. TensorFlow's static graph architecture (`tf.function` decorators), while great for heavy scale, introduces unnecessary friction for a rapid prototyping stealth financial application.

---

### Update: Model Export Artifacts & Local Inference
When extracting the `.zip` file from Google Colab after training `DistilBERT`, you will see a collection of files rather than a single `.exe` or `.dll`. HuggingFace models are purposefully modular. Here is the anatomical breakdown of those artifacts:

#### 1. What are these files?
* **`model.safetensors`**: The actual "brain" of your model. It contains the exact mathematical weights (the billions of numbers optimized during training). It uses the `.safetensors` format (instead of the older `pytorch_model.bin`) because it is unpickled, making it secure against malicious code injection and significantly faster to load into RAM.
* **`config.json`**: The architectural blueprint. It tells the Transformers library exactly how to mount the weights (e.g., how many layers, attention heads, and our custom `num_labels` mapping).
* **`vocab.txt` / `tokenizer.json` / `special_tokens_map.json`**: The translation layer. Deep learning models cannot read text; they look at integers. These files dictate exactly how a Hinglish sentence like "Swiggy se kharcha" gets chopped into sub-word tokens and converted into an array of ID numbers before hitting the tensor weights.

#### 2. How to use them locally
You no longer need Google Colab. To deploy this locally inside your backend, you simply place the extracted unzipped folder (e.g., `my_finetuned_distilbert/`) into your `src/nlp/` directory and point the `transformers` library directly at the folder path instead of downloading from the internet:

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Simply point to the local directory containing the extracted files!
LOCAL_MODEL_PATH = "./src/nlp/my_finetuned_distilbert"

# Load the local Tokenizer and Model
tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_PATH)
model = AutoModelForSequenceClassification.from_pretrained(LOCAL_MODEL_PATH)
model.eval() # Set to evaluation mode (turns off training node behavior)

# Inference Example
text = "Bhai Swiggy se pizza mangwaya 450 rupaye ka"
inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=64)

with torch.no_grad():
    outputs = model(**inputs)

category_id = torch.argmax(outputs.logits, dim=1).item()
# Map 'category_id' back to your string labels (e.g., 0 -> "food")
```
This local loading strategy ensures your backend executes inference offline in milliseconds without relying on external internet APIs.

## Ops: One-time Cleanup for Bad OCR Journals

After the V2.1 simplification (pooled `expense_operating` account + transaction cap), existing journals
created with absurdly large OCR-derived amounts still pollute balances. Run these **once** against the
production database to purge them:

```sql
-- 1. Find journals where any single entry exceeds the cap (₹1 crore = 1,000,000,000 minor units)
SELECT jt.id, jt.description, le.amount_minor
FROM journal_transactions jt
JOIN ledger_entries le ON le.journal_transaction_id = jt.id
WHERE le.amount_minor > 1000000000
ORDER BY le.amount_minor DESC;

-- 2. Delete their entries then the journals themselves
DELETE FROM ledger_entries
WHERE journal_transaction_id IN (
    SELECT DISTINCT jt.id
    FROM journal_transactions jt
    JOIN ledger_entries le ON le.journal_transaction_id = jt.id
    WHERE le.amount_minor > 1000000000
);
DELETE FROM journal_transactions
WHERE id IN (
    SELECT jt.id
    FROM journal_transactions jt
    LEFT JOIN ledger_entries le ON le.journal_transaction_id = jt.id
    WHERE le.id IS NULL
);

-- 3. (Optional) Migrate existing per-category expense accounts to the pooled account
UPDATE ledger_entries
SET account_id = (
    SELECT a.id FROM accounts a
    JOIN users u ON u.id = a.user_id
    WHERE a.code = 'expense_operating'
      AND a.user_id = (SELECT user_id FROM accounts WHERE id = ledger_entries.account_id)
    LIMIT 1
)
WHERE account_id IN (
    SELECT id FROM accounts
    WHERE account_type = 'expense' AND code != 'expense_operating'
);
```

After running the cleanup, verify balances via the Telegram Balance Snapshot button.

## Update: V2.2 Ledger + Telegram + Dataset Improvements

This section captures the latest implementation changes now present in the codebase.

### 1) Safer ledger posting rules

- Added `MAX_TRANSACTION_INR` support in `src/api/config.py` (default: `10000000`, i.e. ₹1 crore).
- `LedgerService._to_minor()` now rejects values above this cap.
- Spending preflight is enforced for **asset** funding accounts:
  - `post_expense`, `post_investment`, and `post_transfer` validate projected balance before posting.
  - If a debit would push an asset account below zero, posting is rejected with a user-facing error.
- New repository helper: `get_account_balance_minor(user_ref, account_code)`.

### 2) Pooled accounts + metadata categories

- Expense, income, and investment posting now use pooled ledger account codes by default:
  - `expense_operating`
  - `income_operating`
  - `investment_portfolio`
- Expense recategorization no longer moves ledger lines across `expense_*` accounts.
  - `reassign_expense_journal_category()` now updates `journal_transactions.metadata_json` only.
- Category correction still works via Telegram "Change category" and metadata updates.

### 3) Clearer balances/report UX

- Telegram Balance Snapshot now shows only cash-relevant accounts (asset/liability), not expense/income buckets.
- Added `LedgerService.get_cash_snapshot(user_ref)` for this filtered view.
- Enriched weekly/monthly Telegram report removed the low-value "Top accounts" section and keeps:
  - Totals
  - Top categories
  - By payment method

### 4) UPI + onboarding flow improvements

- Main dashboard now includes `Add bank / Link UPI` to continue setup even after onboarding is complete.
- Onboarding copy now explicitly supports:
  - adding multiple bank accounts over time,
  - linking each UPI app (GPay/PhonePe/etc.) to a selected bank account.
- UPI link wizard path remains:
  1. provider
  2. pick account
  3. profile label
  4. optional handle
- Successful UPI linking sets `payment_provider` in session and confirms bank-account mapping.

### 5) OCR/NLP extraction enhancements

- Added OCR helper modules:
  - `src/ocr/amount_plausibility.py` (reject ID-sized numbers as amounts)
  - `src/ocr/cash_flow.py` (`paid to` -> expense, `received from` -> income)
  - `src/ocr/upi_detector.py` (Roboflow UPI logo detector client)
- `src/ocr/extractor.py` now uses plausibility and cash-flow detection.
- `src/nlp/inference.py` now returns `cash_flow` and accepts `friends` in valid categories.
- API schema/route (`src/api/schemas.py`, `src/api/routes.py`) include `cash_flow` in extraction responses.

### 6) Dataset augmentation upgrades for retraining

- `augment_dataset.py` was upgraded and now:
  - auto-resolves input CSV from root or `src/nlp/train_transactions.csv`,
  - applies category-aware payment method distributions,
  - injects strong lexical cue templates per category,
  - adds synthetic `friends`/P2P rows,
  - includes occasional realistic UPI bank-last4 clutter in text lines.
- Regenerated output: `eda_dataset_v2.csv`.
- Note: model prediction of `friends` requires retraining/exporting a new DistilBERT checkpoint and aligned label mapping.

### 7) Final image routing (Roboflow-first)

- `ROBOFLOW_UPI_MODEL_ID` is now used as the first decision point for image flow.
- Implemented in:
  - `src/api/routes.py` (`POST /api/v1/extract/image`)
  - `src/api/services/telegram_service.py` (`_extract_from_image_file`)
- Runtime order is now:
  1. Run Roboflow logo detector first.
  2. If UPI logo is detected: run OCR in raw mode (`use_preprocessing=False`), then pass OCR transcript to NLP.
  3. If UPI logo is not detected: run OCR with preprocessing (`use_preprocessing=True`), then pass OCR transcript to NLP.
  4. Amount arbitration remains modality-aware:
     - UPI evidence -> NLP amount priority
     - Non-UPI/invoice evidence -> OCR amount priority
- Added debug visibility fields in extraction responses:
  - `debug_is_upi_evidence`
  - `debug_amount_source`
  - `debug_ocr_preprocessing`