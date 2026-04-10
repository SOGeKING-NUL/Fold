from contextlib import contextmanager

import psycopg

from api.config import get_settings


@contextmanager
def get_db_connection():
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        yield conn


def run_migrations() -> None:
    migration_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        external_user_ref TEXT UNIQUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code TEXT NOT NULL,
        name TEXT NOT NULL,
        account_type TEXT NOT NULL,
        currency TEXT NOT NULL DEFAULT 'INR',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, code)
    );

    CREATE TABLE IF NOT EXISTS journal_transactions (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        source TEXT NOT NULL,
        external_ref TEXT,
        description TEXT,
        occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(source, external_ref)
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
        source TEXT NOT NULL,
        external_event_id TEXT NOT NULL,
        payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
        status TEXT NOT NULL DEFAULT 'received',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(source, external_event_id)
    );
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(migration_sql)
        conn.commit()
