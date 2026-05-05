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
            if "getaddrinfo failed" not in str(exc) or attempt == 2:
                raise
            last_exc = exc
            time.sleep(0.5 * (attempt + 1))
    if last_exc is not None:
        raise last_exc

_RESET_SCHEMA_SQL = """
    DROP TABLE IF EXISTS journal_media CASCADE;
    DROP TABLE IF EXISTS payment_profiles CASCADE;
    DROP TABLE IF EXISTS ingestion_events CASCADE;
    DROP TABLE IF EXISTS ledger_entries CASCADE;
    DROP TABLE IF EXISTS journal_transactions CASCADE;
    DROP TABLE IF EXISTS transactions CASCADE;
    DROP TABLE IF EXISTS accounts CASCADE;
    DROP TABLE IF EXISTS users CASCADE;

    CREATE TABLE users (
        id BIGSERIAL PRIMARY KEY,
        clerk_user_id TEXT UNIQUE NOT NULL,
        email TEXT,
        full_name TEXT,
        avatar_url TEXT,
        default_account_id BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX idx_users_clerk_id ON users(clerk_user_id);
    CREATE INDEX idx_users_email ON users(email);

    CREATE TABLE accounts (
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

    ALTER TABLE users ADD CONSTRAINT fk_default_account FOREIGN KEY (default_account_id) REFERENCES accounts(id) ON DELETE SET NULL;

    CREATE TABLE payment_profiles (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        profile_name TEXT NOT NULL,
        provider TEXT NOT NULL,
        linked_account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, provider, profile_name)
    );

    CREATE TABLE transactions (
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

    CREATE TABLE journal_media (
        id BIGSERIAL PRIMARY KEY,
        transaction_id BIGINT NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
        media_kind TEXT NOT NULL CHECK (media_kind IN ('image', 'audio')),
        mime_type TEXT,
        file_bytes BYTEA NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
"""

def ensure_schema() -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create base tables
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
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, name)
                );
            """)
            
            # Add is_default column if it doesn't exist
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'accounts' AND column_name = 'is_default'
                    ) THEN
                        ALTER TABLE accounts ADD COLUMN is_default BOOLEAN NOT NULL DEFAULT FALSE;
                    END IF;
                END $$;
            """)
            
            # Add balance constraint if it doesn't exist
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'positive_balance_non_credit'
                    ) THEN
                        ALTER TABLE accounts ADD CONSTRAINT positive_balance_non_credit CHECK (
                            account_type = 'credit' OR balance >= 0
                        );
                    END IF;
                END $$;
            """)
            
            # Add foreign key constraint if it doesn't exist
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'fk_default_account'
                    ) THEN
                        ALTER TABLE users ADD CONSTRAINT fk_default_account 
                        FOREIGN KEY (default_account_id) REFERENCES accounts(id) ON DELETE SET NULL;
                    END IF;
                END $$;
            """)
            
            # Create other tables
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payment_profiles (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    profile_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    linked_account_id BIGINT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, provider, profile_name)
                );

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

def reset_database_schema() -> None:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_RESET_SCHEMA_SQL)
        conn.commit()

def run_migrations() -> None:
    if os.getenv("FOLD_RESET_DATABASE", "").lower() in ("1", "true", "yes"):
        reset_database_schema()
    else:
        ensure_schema()
