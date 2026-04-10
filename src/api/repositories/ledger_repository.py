from psycopg.rows import dict_row
from psycopg.types.json import Json

from api.db.connection import get_db_connection


class LedgerRepository:
    def get_or_create_user(self, external_user_ref: str, conn=None) -> dict:
        owns_conn = conn is None
        if owns_conn:
            with get_db_connection() as own_conn:
                result = self.get_or_create_user(external_user_ref, conn=own_conn)
                own_conn.commit()
                return result

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO users (external_user_ref)
                VALUES (%s)
                ON CONFLICT (external_user_ref) DO UPDATE
                SET external_user_ref = EXCLUDED.external_user_ref
                RETURNING *
                """,
                (external_user_ref,),
            )
            return cur.fetchone()

    def get_or_create_account(self, user_id: int, code: str, name: str, account_type: str, conn=None) -> dict:
        owns_conn = conn is None
        if owns_conn:
            with get_db_connection() as own_conn:
                result = self.get_or_create_account(user_id, code, name, account_type, conn=own_conn)
                own_conn.commit()
                return result

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO accounts (user_id, code, name, account_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, code) DO UPDATE
                SET name = EXCLUDED.name,
                    account_type = EXCLUDED.account_type
                RETURNING *
                """,
                (user_id, code, name, account_type),
            )
            return cur.fetchone()

    def get_account_by_code(self, user_id: int, code: str, conn=None) -> dict | None:
        owns_conn = conn is None
        if owns_conn:
            with get_db_connection() as own_conn:
                return self.get_account_by_code(user_id, code, conn=own_conn)

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT *
                FROM accounts
                WHERE user_id = %s AND code = %s
                """,
                (user_id, code),
            )
            return cur.fetchone()

    def list_accounts(self, external_user_ref: str) -> list[dict]:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT a.*
                    FROM users u
                    JOIN accounts a ON a.user_id = u.id
                    WHERE u.external_user_ref = %s
                    ORDER BY a.code
                    """,
                    (external_user_ref,),
                )
                return cur.fetchall()

    def create_balanced_journal(
        self,
        *,
        user_ref: str,
        source: str,
        external_ref: str | None,
        transaction_type: str,
        description: str,
        occurred_at: str | None,
        metadata: dict | None,
        entries: list[dict],
    ) -> dict:
        if not entries:
            raise ValueError("At least one entry is required")

        with get_db_connection() as conn:
            user = self.get_or_create_user(user_ref, conn=conn)
            user_id = int(user["id"])

            # Enforce balance before write.
            debit_total = sum(int(e["amount_minor"]) for e in entries if e["direction"] == "debit")
            credit_total = sum(int(e["amount_minor"]) for e in entries if e["direction"] == "credit")
            if debit_total != credit_total:
                raise ValueError("Journal must be balanced (debits == credits)")

            account_cache: dict[str, dict] = {}
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO journal_transactions (
                        user_id, source, external_ref, transaction_type, description, occurred_at, metadata_json
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, NOW()), %s::jsonb
                    )
                    RETURNING *
                    """,
                    (user_id, source, external_ref, transaction_type, description, occurred_at, Json(metadata or {})),
                )
                journal = cur.fetchone()

                for entry in entries:
                    code = entry["account_code"]
                    acct_type = entry["account_type"]
                    account = account_cache.get(code)
                    if account is None:
                        account = self.get_or_create_account(
                            user_id=user_id,
                            code=code,
                            name=code.replace("_", " ").title(),
                            account_type=acct_type,
                            conn=conn,
                        )
                        account_cache[code] = account

                    cur.execute(
                        """
                        INSERT INTO ledger_entries (journal_transaction_id, account_id, direction, amount_minor)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (int(journal["id"]), int(account["id"]), entry["direction"], int(entry["amount_minor"])),
                    )

            conn.commit()
            return {
                "journal": journal,
                "entries": entries,
                "debit_total_minor": debit_total,
                "credit_total_minor": credit_total,
            }

    def get_balances(self, external_user_ref: str) -> list[dict]:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        a.code,
                        a.name,
                        a.account_type,
                        COALESCE(SUM(
                            CASE
                                WHEN a.account_type IN ('asset', 'expense', 'investment')
                                    THEN CASE WHEN le.direction = 'debit' THEN le.amount_minor ELSE -le.amount_minor END
                                ELSE CASE WHEN le.direction = 'credit' THEN le.amount_minor ELSE -le.amount_minor END
                            END
                        ), 0) AS balance_minor
                    FROM users u
                    JOIN accounts a ON a.user_id = u.id
                    LEFT JOIN ledger_entries le ON le.account_id = a.id
                    WHERE u.external_user_ref = %s
                    GROUP BY a.id
                    ORDER BY a.code
                    """,
                    (external_user_ref,),
                )
                return cur.fetchall()

    def get_transactions(self, external_user_ref: str, limit: int = 50, offset: int = 0) -> list[dict]:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        jt.id,
                        jt.transaction_type,
                        jt.source,
                        jt.external_ref,
                        jt.description,
                        jt.occurred_at,
                        jt.created_at,
                        jt.metadata_json,
                        COALESCE(SUM(CASE WHEN le.direction = 'debit' THEN le.amount_minor ELSE 0 END), 0) AS total_debit_minor,
                        COALESCE(SUM(CASE WHEN le.direction = 'credit' THEN le.amount_minor ELSE 0 END), 0) AS total_credit_minor
                    FROM users u
                    JOIN journal_transactions jt ON jt.user_id = u.id
                    LEFT JOIN ledger_entries le ON le.journal_transaction_id = jt.id
                    WHERE u.external_user_ref = %s
                    GROUP BY jt.id
                    ORDER BY jt.occurred_at DESC, jt.id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (external_user_ref, limit, offset),
                )
                return cur.fetchall()

    def get_report_window_summary(self, external_user_ref: str, days: int) -> dict:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN jt.transaction_type = 'income' THEN le.amount_minor ELSE 0 END), 0) AS income_minor,
                        COALESCE(SUM(CASE WHEN jt.transaction_type = 'expense' THEN le.amount_minor ELSE 0 END), 0) AS expense_minor,
                        COALESCE(SUM(CASE WHEN jt.transaction_type = 'investment' THEN le.amount_minor ELSE 0 END), 0) AS investment_minor
                    FROM users u
                    JOIN journal_transactions jt ON jt.user_id = u.id
                    JOIN ledger_entries le ON le.journal_transaction_id = jt.id
                    JOIN accounts a ON a.id = le.account_id
                    WHERE u.external_user_ref = %s
                      AND jt.occurred_at >= NOW() - (%s::text || ' days')::interval
                      AND (
                        (jt.transaction_type = 'income' AND a.account_type = 'asset' AND le.direction = 'debit') OR
                        (jt.transaction_type = 'expense' AND a.account_type = 'expense' AND le.direction = 'debit') OR
                        (jt.transaction_type = 'investment' AND a.account_type = 'investment' AND le.direction = 'debit')
                      )
                    """,
                    (external_user_ref, days),
                )
                return cur.fetchone() or {"income_minor": 0, "expense_minor": 0, "investment_minor": 0}

    def get_breakdown(self, external_user_ref: str, days: int, group_by: str) -> list[dict]:
        valid_group = {
            "account": "a.code",
            "payment_method": "COALESCE(jt.metadata_json->>'payment_method', 'unknown')",
            "category": "COALESCE(jt.metadata_json->>'category', 'uncategorized')",
        }
        if group_by not in valid_group:
            raise ValueError("Invalid group_by")

        sql_group_expr = valid_group[group_by]
        query = f"""
            SELECT
                {sql_group_expr} AS key,
                COALESCE(SUM(le.amount_minor), 0) AS amount_minor
            FROM users u
            JOIN journal_transactions jt ON jt.user_id = u.id
            JOIN ledger_entries le ON le.journal_transaction_id = jt.id
            JOIN accounts a ON a.id = le.account_id
            WHERE u.external_user_ref = %s
              AND jt.occurred_at >= NOW() - (%s::text || ' days')::interval
              AND jt.transaction_type IN ('expense', 'income', 'investment')
              AND (
                (jt.transaction_type = 'income' AND a.account_type = 'asset' AND le.direction = 'debit') OR
                (jt.transaction_type = 'expense' AND a.account_type = 'expense' AND le.direction = 'debit') OR
                (jt.transaction_type = 'investment' AND a.account_type = 'investment' AND le.direction = 'debit')
              )
            GROUP BY key
            ORDER BY amount_minor DESC
        """
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (external_user_ref, days))
                return cur.fetchall()

    def get_session(self, telegram_user_id: int) -> dict | None:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT * FROM telegram_sessions WHERE telegram_user_id = %s
                    """,
                    (telegram_user_id,),
                )
                return cur.fetchone()

    def upsert_session(self, telegram_user_id: int, state: str, payload: dict) -> None:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO telegram_sessions (telegram_user_id, state, payload_json, updated_at)
                    VALUES (%s, %s, %s::jsonb, NOW())
                    ON CONFLICT (telegram_user_id) DO UPDATE
                    SET state = EXCLUDED.state,
                        payload_json = EXCLUDED.payload_json,
                        updated_at = NOW()
                    """,
                    (telegram_user_id, state, Json(payload)),
                )
            conn.commit()
