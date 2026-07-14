import os
import time
import logging
from contextlib import contextmanager
import psycopg
from api.config import get_settings

_logger = logging.getLogger(__name__)

# Cache the settings object so we don't re-parse .env on every connection
_cached_settings = None

def _get_cached_settings():
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = get_settings()
    return _cached_settings

@contextmanager
def get_db_connection():
    """Open a connection to the database with retry logic for DNS failures."""
    settings = _get_cached_settings()
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            with psycopg.connect(
                settings.database_url,
                connect_timeout=10,   # Don't hang forever on slow Neon cold-starts
            ) as conn:
                yield conn
                return
        except psycopg.OperationalError as exc:
            if "getaddrinfo failed" not in str(exc) or attempt == 2:
                raise
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))
    if last_exc is not None:
        raise last_exc

def ensure_schema() -> None:
    """Create all tables and indexes if they don't exist."""
    _logger.info("Initializing database schema...")
    start = time.time()

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    clerk_user_id TEXT UNIQUE NOT NULL,
                    email TEXT,
                    full_name TEXT,
                    avatar_url TEXT,
                    default_account_id BIGINT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_users_clerk_id ON users(clerk_user_id);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

                CREATE TABLE IF NOT EXISTS accounts (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    account_type TEXT NOT NULL CHECK (account_type IN ('cash', 'bank', 'credit')),
                    balance BIGINT NOT NULL DEFAULT 0,
                    institution_name TEXT,
                    account_number_last4 TEXT,
                    is_default BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, name),
                    CONSTRAINT positive_balance_non_credit CHECK (
                        account_type = 'credit' OR balance >= 0
                    )
                );

                CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id);
                CREATE INDEX IF NOT EXISTS idx_accounts_user_name ON accounts(user_id, name);
                CREATE INDEX IF NOT EXISTS idx_accounts_is_default ON accounts(is_default);

                -- Foreign key for default_account_id on users
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_default_account'
                    ) THEN
                        ALTER TABLE users ADD CONSTRAINT fk_default_account
                        FOREIGN KEY (default_account_id) REFERENCES accounts(id) ON DELETE SET NULL;
                    END IF;
                END $$;

                CREATE TABLE IF NOT EXISTS payment_profiles (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    profile_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    linked_account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, provider, profile_name)
                );

                CREATE INDEX IF NOT EXISTS idx_payment_profiles_user_id ON payment_profiles(user_id);
                CREATE INDEX IF NOT EXISTS idx_payment_profiles_provider ON payment_profiles(user_id, provider);

                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    amount BIGINT NOT NULL,
                    type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer', 'opening_balance')),
                    category TEXT NOT NULL,
                    description TEXT,
                    account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL,
                    to_account_id BIGINT REFERENCES accounts(id) ON DELETE SET NULL,
                    payment_profile_id BIGINT REFERENCES payment_profiles(id) ON DELETE SET NULL,
                    source TEXT NOT NULL,
                    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_occurred_at ON transactions(occurred_at DESC);
                CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
                CREATE INDEX IF NOT EXISTS idx_transactions_user_occurred ON transactions(user_id, occurred_at DESC);
                CREATE INDEX IF NOT EXISTS idx_transactions_account_id ON transactions(account_id);
                CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);

                CREATE TABLE IF NOT EXISTS journal_media (
                    id BIGSERIAL PRIMARY KEY,
                    transaction_id BIGINT NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                    media_kind TEXT NOT NULL CHECK (media_kind IN ('image', 'audio')),
                    mime_type TEXT,
                    file_bytes BYTEA NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
        conn.commit()

    elapsed = time.time() - start
    _logger.info(f"Schema initialized in {elapsed:.2f}s")

def run_migrations() -> None:
    ensure_schema()
