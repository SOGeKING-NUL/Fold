import re

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

    def get_or_create_account(
        self,
        user_id: int,
        code: str,
        name: str,
        account_type: str,
        institution_name: str | None = None,
        account_number_last4: str | None = None,
        is_digital: bool = False,
        conn=None,
    ) -> dict:
        owns_conn = conn is None
        if owns_conn:
            with get_db_connection() as own_conn:
                result = self.get_or_create_account(
                    user_id,
                    code,
                    name,
                    account_type,
                    institution_name=institution_name,
                    account_number_last4=account_number_last4,
                    is_digital=is_digital,
                    conn=own_conn,
                )
                own_conn.commit()
                return result

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO accounts (user_id, code, name, account_type, institution_name, account_number_last4, is_digital)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, code) DO UPDATE
                SET name = EXCLUDED.name,
                    account_type = EXCLUDED.account_type,
                    institution_name = COALESCE(EXCLUDED.institution_name, accounts.institution_name),
                    account_number_last4 = COALESCE(EXCLUDED.account_number_last4, accounts.account_number_last4),
                    is_digital = EXCLUDED.is_digital
                RETURNING *
                """,
                (user_id, code, name, account_type, institution_name, account_number_last4, is_digital),
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

    def has_onboarding_account(self, external_user_ref: str) -> bool:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM users u
                        JOIN accounts a ON a.user_id = u.id
                        WHERE u.external_user_ref = %s
                          AND a.account_type IN ('asset', 'liability')
                          AND a.account_number_last4 IS NOT NULL
                          AND length(a.account_number_last4) = 4
                    )
                    """,
                    (external_user_ref,),
                )
                row = cur.fetchone()
                return bool(row and row[0])

    def get_user_preferences(self, external_user_ref: str) -> dict:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    "SELECT preferences_json FROM users WHERE external_user_ref = %s",
                    (external_user_ref,),
                )
                row = cur.fetchone()
                if not row:
                    return {}
                pj = row.get("preferences_json")
                if pj is None:
                    return {}
                return dict(pj) if isinstance(pj, dict) else {}

    def merge_user_preferences(self, external_user_ref: str, patch: dict) -> None:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET preferences_json = COALESCE(preferences_json, '{}'::jsonb) || %s::jsonb
                    WHERE external_user_ref = %s
                    """,
                    (Json(patch), external_user_ref),
                )
            conn.commit()

    def list_real_funding_accounts(self, external_user_ref: str) -> list[dict]:
        """Asset/liability accounts the user set up with a 4-digit last4 (actual cards/banks)."""
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT a.code, a.name, a.account_type
                    FROM users u
                    JOIN accounts a ON a.user_id = u.id
                    WHERE u.external_user_ref = %s
                      AND a.account_type IN ('asset', 'liability')
                      AND a.account_number_last4 IS NOT NULL
                      AND length(trim(a.account_number_last4)) = 4
                      AND a.is_active = TRUE
                    ORDER BY a.code
                    """,
                    (external_user_ref,),
                )
                return list(cur.fetchall())

    def try_claim_telegram_update(self, update_id: int) -> bool:
        """
        Return True if this Telegram update_id is new and was recorded.
        Return False on replay (webhook retry) so handlers do not send duplicate messages.
        """
        if update_id <= 0:
            return True
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ingestion_events (source, external_event_id, payload_json)
                    VALUES ('telegram_update', %s, '{}'::jsonb)
                    ON CONFLICT (source, external_event_id) DO NOTHING
                    RETURNING id
                    """,
                    (str(update_id),),
                )
                row = cur.fetchone()
            conn.commit()
        return row is not None

    def create_or_update_payment_profile(
        self,
        *,
        user_ref: str,
        profile_type: str,
        provider: str,
        profile_name: str,
        handle_ref: str | None,
        linked_account_code: str,
    ) -> dict:
        with get_db_connection() as conn:
            user = self.get_or_create_user(user_ref, conn=conn)
            user_id = int(user["id"])
            linked_account = self.get_account_by_code(user_id=user_id, code=linked_account_code, conn=conn)
            if not linked_account:
                raise ValueError(f"Account not found: {linked_account_code}")

            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO payment_profiles (
                        user_id, profile_type, provider, profile_name, handle_ref, linked_account_id, is_active
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                    ON CONFLICT (user_id, profile_type, provider, profile_name) DO UPDATE
                    SET handle_ref = EXCLUDED.handle_ref,
                        linked_account_id = EXCLUDED.linked_account_id,
                        is_active = TRUE
                    RETURNING *
                    """,
                    (user_id, profile_type, provider.lower(), profile_name, handle_ref, int(linked_account["id"])),
                )
                profile = cur.fetchone()
            conn.commit()
            return profile

    def list_payment_profiles(self, user_ref: str) -> list[dict]:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        pp.id,
                        pp.profile_type,
                        pp.provider,
                        pp.profile_name,
                        pp.handle_ref,
                        pp.is_active,
                        a.code AS linked_account_code
                    FROM users u
                    JOIN payment_profiles pp ON pp.user_id = u.id
                    LEFT JOIN accounts a ON a.id = pp.linked_account_id
                    WHERE u.external_user_ref = %s
                    ORDER BY pp.provider, pp.profile_name
                    """,
                    (user_ref,),
                )
                return cur.fetchall()

    def resolve_funding_account_by_last4(
        self,
        user_ref: str,
        last4: str,
        institution_hint: str | None = None,
    ) -> dict | None:
        """
        Match a receipt line like "HDFC Bank 1751" to the user's asset/liability account
        with the same account_number_last4. If several accounts share last4 (rare), use
        institution_hint (e.g. "hdfc") against institution_name / account name.
        """
        digits = "".join(ch for ch in str(last4) if ch.isdigit())
        if len(digits) != 4:
            return None
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT a.code, a.account_type, a.institution_name, a.name
                    FROM users u
                    JOIN accounts a ON a.user_id = u.id
                    WHERE u.external_user_ref = %s
                      AND a.account_type IN ('asset', 'liability')
                      AND trim(a.account_number_last4) = %s
                      AND a.is_active = TRUE
                    """,
                    (user_ref, digits),
                )
                rows = list(cur.fetchall())
        if not rows:
            return None
        if len(rows) == 1:
            return {"code": rows[0]["code"], "account_type": rows[0]["account_type"]}
        if not institution_hint:
            return None
        hint = institution_hint.lower().strip()
        if not hint:
            return None

        def matches(row: dict) -> bool:
            iname = (row.get("institution_name") or "").lower()
            aname = (row.get("name") or "").lower()
            return hint in iname or hint in aname or iname.startswith(hint)

        scored = [r for r in rows if matches(r)]
        if len(scored) == 1:
            return {"code": scored[0]["code"], "account_type": scored[0]["account_type"]}
        return None

    def resolve_linked_account_for_provider(self, user_ref: str, profile_type: str, provider: str) -> dict | None:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        a.code,
                        a.account_type,
                        pp.provider,
                        pp.profile_name
                    FROM users u
                    JOIN payment_profiles pp ON pp.user_id = u.id
                    JOIN accounts a ON a.id = pp.linked_account_id
                    WHERE u.external_user_ref = %s
                      AND pp.profile_type = %s
                      AND pp.provider = %s
                      AND pp.is_active = TRUE
                    ORDER BY pp.id DESC
                    LIMIT 1
                    """,
                    (user_ref, profile_type, provider.lower()),
                )
                return cur.fetchone()

    def get_account_balance_minor(self, user_ref: str, account_code: str) -> int:
        """Current balance (in minor units) for one account, using normal debit/credit sign rules."""
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(
                        CASE
                            WHEN a.account_type IN ('asset', 'expense', 'investment')
                                THEN CASE WHEN le.direction = 'debit' THEN le.amount_minor ELSE -le.amount_minor END
                            ELSE CASE WHEN le.direction = 'credit' THEN le.amount_minor ELSE -le.amount_minor END
                        END
                    ), 0) AS balance_minor
                    FROM users u
                    JOIN accounts a ON a.user_id = u.id
                    LEFT JOIN ledger_entries le ON le.account_id = a.id
                    WHERE u.external_user_ref = %s AND a.code = %s
                    GROUP BY a.id
                    """,
                    (user_ref, account_code),
                )
                row = cur.fetchone()
                return int(row["balance_minor"]) if row else 0

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

    def get_daily_trend(self, external_user_ref: str, days: int) -> list[dict]:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        d.day::date AS day,
                        COALESCE(SUM(CASE WHEN jt.transaction_type = 'expense' THEN le.amount_minor ELSE 0 END), 0) AS expense_minor,
                        COALESCE(SUM(CASE WHEN jt.transaction_type = 'income'  THEN le.amount_minor ELSE 0 END), 0) AS income_minor
                    FROM generate_series(
                        (NOW() - (%s::text || ' days')::interval)::date,
                        NOW()::date,
                        '1 day'::interval
                    ) AS d(day)
                    LEFT JOIN users u ON u.external_user_ref = %s
                    LEFT JOIN journal_transactions jt
                        ON jt.user_id = u.id
                        AND jt.occurred_at::date = d.day::date
                        AND jt.transaction_type IN ('expense', 'income')
                    LEFT JOIN ledger_entries le
                        ON le.journal_transaction_id = jt.id
                        AND (
                            (jt.transaction_type = 'income'  AND le.direction = 'debit') OR
                            (jt.transaction_type = 'expense' AND le.direction = 'debit')
                        )
                    LEFT JOIN accounts a
                        ON a.id = le.account_id
                        AND (
                            (jt.transaction_type = 'income'  AND a.account_type = 'asset') OR
                            (jt.transaction_type = 'expense' AND a.account_type = 'expense')
                        )
                    GROUP BY d.day
                    ORDER BY d.day
                    """,
                    (days, external_user_ref),
                )
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

    def upsert_pending_expense_media(
        self,
        telegram_user_id: int,
        media_kind: str,
        mime_type: str | None,
        file_bytes: bytes,
    ) -> None:
        if media_kind not in ("image", "audio"):
            raise ValueError("media_kind must be image or audio")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO telegram_expense_pending_media (telegram_user_id, media_kind, mime_type, file_bytes)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (telegram_user_id) DO UPDATE
                    SET media_kind = EXCLUDED.media_kind,
                        mime_type = EXCLUDED.mime_type,
                        file_bytes = EXCLUDED.file_bytes,
                        updated_at = NOW()
                    """,
                    (telegram_user_id, media_kind, mime_type, file_bytes),
                )
            conn.commit()

    def fetch_pending_expense_media(self, telegram_user_id: int) -> dict | None:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT telegram_user_id, media_kind, mime_type, file_bytes, updated_at
                    FROM telegram_expense_pending_media
                    WHERE telegram_user_id = %s
                    """,
                    (telegram_user_id,),
                )
                return cur.fetchone()

    def delete_pending_expense_media(self, telegram_user_id: int) -> None:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM telegram_expense_pending_media WHERE telegram_user_id = %s",
                    (telegram_user_id,),
                )
            conn.commit()

    def insert_journal_media(
        self,
        journal_transaction_id: int,
        media_kind: str,
        mime_type: str | None,
        file_bytes: bytes,
    ) -> dict:
        if media_kind not in ("image", "audio"):
            raise ValueError("media_kind must be image or audio")
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO journal_media (journal_transaction_id, media_kind, mime_type, file_bytes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, journal_transaction_id, media_kind, mime_type, created_at
                    """,
                    (journal_transaction_id, media_kind, mime_type, file_bytes),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def reassign_expense_journal_category(
        self, *, user_ref: str, journal_transaction_id: int, new_category: str
    ) -> dict:
        """
        Update the category stored in metadata_json for an expense journal.
        Ledger entries stay on the pooled expense_operating account; only the tag changes.
        """
        valid = frozenset(
            {
                "education",
                "emi",
                "entertainment",
                "food",
                "healthcare",
                "investment",
                "shopping",
                "travel",
                "utilities",
                "misc",
                "friends",
            }
        )
        cat = new_category.lower().strip()
        if cat not in valid:
            raise ValueError(f"Invalid category '{new_category}'.")

        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT jt.id, jt.transaction_type
                    FROM journal_transactions jt
                    JOIN users u ON u.id = jt.user_id
                    WHERE u.external_user_ref = %s AND jt.id = %s
                    """,
                    (user_ref, journal_transaction_id),
                )
                jt = cur.fetchone()
                if not jt:
                    raise ValueError("Journal not found.")
                if jt["transaction_type"] != "expense":
                    raise ValueError("Only expense journals can be recategorized this way.")

                cur.execute(
                    """
                    UPDATE journal_transactions
                    SET metadata_json = COALESCE(metadata_json, '{}'::jsonb) || %s::jsonb
                    WHERE id = %s
                    """,
                    (Json({"category": cat, "category_user_corrected": True}), journal_transaction_id),
                )
            conn.commit()
        return {"journal_id": journal_transaction_id, "category": cat}
