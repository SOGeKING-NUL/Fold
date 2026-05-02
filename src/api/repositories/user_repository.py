"""
User Repository
===============
Handles user creation and retrieval with Clerk integration.
"""

import logging
from typing import Optional
from api.db.connection import get_db_connection

_logger = logging.getLogger(__name__)


class UserRepository:
    def get_or_create_user_from_clerk(
        self,
        clerk_user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> dict:
        """
        Get existing user by Clerk ID or create a new one.
        Also creates default accounts for new users.
        Returns user dict with id and external_user_ref.
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Try to find existing user by Clerk ID
                cur.execute(
                    """
                    SELECT id, external_user_ref, clerk_user_id, email, full_name, avatar_url
                    FROM users
                    WHERE clerk_user_id = %s
                    """,
                    (clerk_user_id,)
                )
                row = cur.fetchone()
                
                if row:
                    # Update user info if changed
                    cur.execute(
                        """
                        UPDATE users
                        SET email = COALESCE(%s, email),
                            full_name = COALESCE(%s, full_name),
                            avatar_url = COALESCE(%s, avatar_url),
                            updated_at = NOW()
                        WHERE clerk_user_id = %s
                        """,
                        (email, full_name, avatar_url, clerk_user_id)
                    )
                    conn.commit()
                    
                    return {
                        "id": row[0],
                        "external_user_ref": row[1],
                        "clerk_user_id": row[2],
                        "email": row[3],
                        "full_name": row[4],
                        "avatar_url": row[5],
                    }
                
                # Create new user
                # Use clerk_user_id as external_user_ref for consistency
                cur.execute(
                    """
                    INSERT INTO users (external_user_ref, clerk_user_id, email, full_name, avatar_url)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, external_user_ref, clerk_user_id, email, full_name, avatar_url
                    """,
                    (clerk_user_id, clerk_user_id, email, full_name, avatar_url)
                )
                row = cur.fetchone()
                user_id = row[0]
                
                # Create default accounts for new user
                self._create_default_accounts(cur, user_id, clerk_user_id)
                
                conn.commit()
                
                _logger.info(f"Created new user from Clerk: {clerk_user_id}")
                
                return {
                    "id": row[0],
                    "external_user_ref": row[1],
                    "clerk_user_id": row[2],
                    "email": row[3],
                    "full_name": row[4],
                    "avatar_url": row[5],
                }
    
    def _create_default_accounts(self, cur, user_id: int, user_ref: str):
        """
        Create only essential system accounts for a new user.
        Users will add payment methods (bank, credit card, etc.) on-demand.
        """
        # Only create system accounts needed for double-entry bookkeeping
        essential_accounts = [
            {
                "code": "expense_operating",
                "name": "Expenses",
                "account_type": "expense",
                "is_digital": False,
            },
            {
                "code": "income_operating",
                "name": "Income",
                "account_type": "income",
                "is_digital": False,
            },
            {
                "code": "equity_opening_balance",
                "name": "Opening Balance",
                "account_type": "equity",
                "is_digital": False,
            },
        ]
        
        for acc in essential_accounts:
            cur.execute(
                """
                INSERT INTO accounts (user_id, code, name, account_type, is_digital, currency)
                VALUES (%s, %s, %s, %s, %s, 'INR')
                ON CONFLICT (user_id, code) DO NOTHING
                """,
                (user_id, acc["code"], acc["name"], acc["account_type"], acc["is_digital"])
            )
        
        # No default funding account - user must add payment methods first
        _logger.info(f"Created essential system accounts for user {user_ref}")
    
    def get_user_by_ref(self, user_ref: str) -> Optional[dict]:
        """Get user by external_user_ref or clerk_user_id."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, external_user_ref, clerk_user_id, email, full_name, avatar_url
                    FROM users
                    WHERE external_user_ref = %s OR clerk_user_id = %s
                    """,
                    (user_ref, user_ref)
                )
                row = cur.fetchone()
                
                if not row:
                    return None
                
                return {
                    "id": row[0],
                    "external_user_ref": row[1],
                    "clerk_user_id": row[2],
                    "email": row[3],
                    "full_name": row[4],
                    "avatar_url": row[5],
                }
