from psycopg.rows import dict_row

from api.db.connection import get_db_connection


class LedgerRepository:
    def get_or_create_user(self, external_user_ref: str) -> dict:
        with get_db_connection() as conn:
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
                user = cur.fetchone()
            conn.commit()
        return user

    def get_or_create_account(self, user_id: int, code: str, name: str, account_type: str) -> dict:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO accounts (user_id, code, name, account_type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, code) DO UPDATE
                    SET name = EXCLUDED.name
                    RETURNING *
                    """,
                    (user_id, code, name, account_type),
                )
                account = cur.fetchone()
            conn.commit()
        return account

    def create_journal_transaction(
        self,
        user_id: int,
        source: str,
        external_ref: str | None,
        description: str,
    ) -> dict:
        with get_db_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO journal_transactions (user_id, source, external_ref, description)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (user_id, source, external_ref, description),
                )
                tx = cur.fetchone()
            conn.commit()
        return tx

    def insert_ledger_entry(
        self,
        journal_transaction_id: int,
        account_id: int,
        direction: str,
        amount_minor: int,
    ) -> None:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ledger_entries (journal_transaction_id, account_id, direction, amount_minor)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (journal_transaction_id, account_id, direction, amount_minor),
                )
            conn.commit()

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
                                WHEN le.direction = 'debit' THEN le.amount_minor
                                ELSE -le.amount_minor
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
