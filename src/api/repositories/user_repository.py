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
        Returns user dict with id and clerk_user_id.
        """
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, clerk_user_id, email, full_name, avatar_url, default_account_id
                    FROM users
                    WHERE clerk_user_id = %s
                    """,
                    (clerk_user_id,)
                )
                row = cur.fetchone()
                
                if row:
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
                        "clerk_user_id": row[1],
                        "email": row[2],
                        "full_name": row[3],
                        "avatar_url": row[4],
                        "default_account_id": row[5],
                    }
                
                cur.execute(
                    """
                    INSERT INTO users (clerk_user_id, email, full_name, avatar_url)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, clerk_user_id, email, full_name, avatar_url, default_account_id
                    """,
                    (clerk_user_id, email, full_name, avatar_url)
                )
                row = cur.fetchone()
                conn.commit()
                _logger.info(f"Created new user from Clerk: {clerk_user_id}")
                return {
                    "id": row[0],
                    "clerk_user_id": row[1],
                    "email": row[2],
                    "full_name": row[3],
                    "avatar_url": row[4],
                    "default_account_id": row[5],
                }
    
    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[dict]:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, clerk_user_id, email, full_name, avatar_url, default_account_id
                    FROM users
                    WHERE clerk_user_id = %s
                    """,
                    (clerk_user_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "id": row[0],
                    "clerk_user_id": row[1],
                    "email": row[2],
                    "full_name": row[3],
                    "avatar_url": row[4],
                    "default_account_id": row[5],
                }

    def set_default_account(self, clerk_user_id: str, account_id: int):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users SET default_account_id = %s WHERE clerk_user_id = %s
                    """,
                    (account_id, clerk_user_id)
                )
                conn.commit()
