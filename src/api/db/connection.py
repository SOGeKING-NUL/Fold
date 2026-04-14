import os
import time
from contextlib import contextmanager

import psycopg

from api.config import get_settings


@contextmanager
def get_db_connection():
    settings = get_settings()
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with psycopg.connect(settings.database_url) as conn:
                yield conn
                return
        except psycopg.OperationalError as exc:
            # Network/DNS hiccups can briefly fail webhook requests on Windows.
            if "getaddrinfo failed" not in str(exc) or attempt == 2:
                raise
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))

    if last_exc is not None:
        raise last_exc


_RESET_SCHEMA_SQL = """
    DROP TABLE IF EXISTS journal_media CASCADE;
    DROP TABLE IF EXISTS telegram_expense_pending_media CASCADE;
    DROP TABLE IF EXISTS payment_profiles CASCADE;
    DROP TABLE IF EXISTS ingestion_events CASCADE;
    DROP TABLE IF EXISTS telegram_sessions CASCADE;
    DROP TABLE IF EXISTS ledger_entries CASCADE;
    DROP TABLE IF EXISTS journal_transactions CASCADE;
    DROP TABLE IF EXISTS accounts CASCADE;
    DROP TABLE IF EXISTS users CASCADE;

    CREATE TABLE users (
        id BIGSERIAL PRIMARY KEY,
        external_user_ref TEXT NOT NULL UNIQUE,
        preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE accounts (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        account_type TEXT NOT NULL CHECK (account_type IN ('asset', 'liability', 'equity', 'income', 'expense', 'investment')),
        institution_name TEXT,
        account_number_last4 TEXT,
        is_digital BOOLEAN NOT NULL DEFAULT FALSE,
        currency TEXT NOT NULL DEFAULT 'INR',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, code)
    );

    CREATE TABLE payment_profiles (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        profile_type TEXT NOT NULL CHECK (profile_type IN ('upi', 'card', 'wallet', 'bank_app')),
        provider TEXT NOT NULL,
        profile_name TEXT NOT NULL,
        handle_ref TEXT,
        linked_account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, profile_type, provider, profile_name)
    );

    CREATE TABLE journal_transactions (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        external_ref TEXT,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('expense', 'income', 'investment', 'transfer', 'opening_balance')),
        description TEXT,
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE NULLS NOT DISTINCT (user_id, source, external_ref)
    );

    CREATE TABLE journal_media (
        id BIGSERIAL PRIMARY KEY,
        journal_transaction_id BIGINT NOT NULL REFERENCES journal_transactions(id) ON DELETE CASCADE,
        media_kind TEXT NOT NULL CHECK (media_kind IN ('image', 'audio')),
        mime_type TEXT,
        file_bytes BYTEA NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE telegram_expense_pending_media (
        telegram_user_id BIGINT PRIMARY KEY,
        media_kind TEXT NOT NULL CHECK (media_kind IN ('image', 'audio')),
        mime_type TEXT,
        file_bytes BYTEA NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE ledger_entries (
        id BIGSERIAL PRIMARY KEY,
        journal_transaction_id BIGINT NOT NULL REFERENCES journal_transactions(id) ON DELETE CASCADE,
        account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        direction TEXT NOT NULL CHECK (direction IN ('debit', 'credit')),
        amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
        currency TEXT NOT NULL DEFAULT 'INR',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE telegram_sessions (
        id BIGSERIAL PRIMARY KEY,
        telegram_user_id BIGINT NOT NULL UNIQUE,
        state TEXT NOT NULL DEFAULT 'idle',
        payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE ingestion_events (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
        source TEXT NOT NULL,
        external_event_id TEXT NOT NULL,
        payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        status TEXT NOT NULL DEFAULT 'received',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(source, external_event_id)
    );
"""

# Idempotent DDL for normal startup (does not drop existing data).
_ENSURE_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        external_user_ref TEXT NOT NULL UNIQUE,
        preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        account_type TEXT NOT NULL CHECK (account_type IN ('asset', 'liability', 'equity', 'income', 'expense', 'investment')),
        institution_name TEXT,
        account_number_last4 TEXT,
        is_digital BOOLEAN NOT NULL DEFAULT FALSE,
        currency TEXT NOT NULL DEFAULT 'INR',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, code)
    );

    CREATE TABLE IF NOT EXISTS payment_profiles (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        profile_type TEXT NOT NULL CHECK (profile_type IN ('upi', 'card', 'wallet', 'bank_app')),
        provider TEXT NOT NULL,
        profile_name TEXT NOT NULL,
        handle_ref TEXT,
        linked_account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, profile_type, provider, profile_name)
    );

    CREATE TABLE IF NOT EXISTS journal_transactions (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        external_ref TEXT,
        transaction_type TEXT NOT NULL CHECK (transaction_type IN ('expense', 'income', 'investment', 'transfer', 'opening_balance')),
        description TEXT,
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE NULLS NOT DISTINCT (user_id, source, external_ref)
    );

    CREATE TABLE IF NOT EXISTS journal_media (
        id BIGSERIAL PRIMARY KEY,
        journal_transaction_id BIGINT NOT NULL REFERENCES journal_transactions(id) ON DELETE CASCADE,
        media_kind TEXT NOT NULL CHECK (media_kind IN ('image', 'audio')),
        mime_type TEXT,
        file_bytes BYTEA NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS telegram_expense_pending_media (
        telegram_user_id BIGINT PRIMARY KEY,
        media_kind TEXT NOT NULL CHECK (media_kind IN ('image', 'audio')),
        mime_type TEXT,
        file_bytes BYTEA NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS ledger_entries (
        id BIGSERIAL PRIMARY KEY,
        journal_transaction_id BIGINT NOT NULL REFERENCES journal_transactions(id) ON DELETE CASCADE,
        account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        direction TEXT NOT NULL CHECK (direction IN ('debit', 'credit')),
        amount_minor BIGINT NOT NULL CHECK (amount_minor > 0),
        currency TEXT NOT NULL DEFAULT 'INR',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS telegram_sessions (
        id BIGSERIAL PRIMARY KEY,
        telegram_user_id BIGINT NOT NULL UNIQUE,
        state TEXT NOT NULL DEFAULT 'idle',
        payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS ingestion_events (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
        source TEXT NOT NULL,
        external_event_id TEXT NOT NULL,
        payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        status TEXT NOT NULL DEFAULT 'received',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(source, external_event_id)
    );
"""


def reset_database_schema() -> None:
    """
    Drops and recreates all Fold ledger tables. Destroys all data.
    Set env FOLD_RESET_DATABASE=1 (or true) before startup, or call from a one-off admin script.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_RESET_SCHEMA_SQL)
        conn.commit()


def ensure_schema() -> None:
    """Creates tables if missing. Safe on every app startup; does not delete rows."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_ENSURE_SCHEMA_SQL)
            cur.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS preferences_json JSONB NOT NULL DEFAULT '{}'::jsonb"
            )
        conn.commit()


def run_migrations() -> None:
    """
    Startup hook: ensures schema exists without wiping data.

    To force a full reset (dev only), set FOLD_RESET_DATABASE=1 and restart once, then unset it.
    """
    if os.getenv("FOLD_RESET_DATABASE", "").lower() in ("1", "true", "yes"):
        reset_database_schema()
    else:
        ensure_schema()
