"""
Clerk Authentication Middleware
================================
Validates Clerk JWT tokens and extracts user information.
"""

import os
import logging
from typing import Optional
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

_logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class ClerkAuth:
    def __init__(self):
        self.clerk_secret_key = os.getenv("CLERK_SECRET_KEY", "")
        self.clerk_publishable_key = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")
        
        if not self.clerk_secret_key:
            _logger.warning("CLERK_SECRET_KEY not set - Clerk authentication disabled")
        
        # Extract instance ID from publishable key
        # Format: pk_test_<instance>.<domain>
        if self.clerk_publishable_key:
            try:
                parts = self.clerk_publishable_key.split("_")
                if len(parts) >= 3:
                    # Extract the base64 part and decode to get domain
                    import base64
                    encoded_part = parts[2]
                    # Add padding if needed
                    padding = 4 - len(encoded_part) % 4
                    if padding != 4:
                        encoded_part += "=" * padding
                    decoded = base64.b64decode(encoded_part).decode('utf-8')
                    self.clerk_domain = decoded
                else:
                    self.clerk_domain = "assured-bullfrog-8.clerk.accounts.dev"
            except Exception as e:
                _logger.warning(f"Could not parse Clerk domain from publishable key: {e}")
                self.clerk_domain = "assured-bullfrog-8.clerk.accounts.dev"
        else:
            self.clerk_domain = "assured-bullfrog-8.clerk.accounts.dev"
        
        self.jwks_url = f"https://{self.clerk_domain}/.well-known/jwks.json"
        _logger.info(f"Clerk JWKS URL: {self.jwks_url}")
        
        # Initialize JWKS client for token verification
        try:
            self.jwks_client = PyJWKClient(self.jwks_url)
        except Exception as e:
            _logger.error(f"Failed to initialize JWKS client: {e}")
            self.jwks_client = None

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify a Clerk JWT token and return the decoded payload.
        Returns None if verification fails.
        """
        if not self.jwks_client:
            _logger.error("JWKS client not initialized")
            return None
        
        try:
            # Get the signing key from Clerk's JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_exp": True}
            )
            
            return payload
        except jwt.ExpiredSignatureError:
            _logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            _logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            _logger.error(f"Token verification failed: {e}")
            return None

    async def get_current_user(self, request: Request) -> Optional[dict]:
        """
        Extract and verify Clerk token from request.
        Returns user info dict or None.
        """
        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        if not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        
        # Verify the token
        payload = self.verify_token(token)
        if not payload:
            return None
        
        # Extract user information from payload
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            return None
        
        return {
            "clerk_user_id": user_id,
            "email": email,
            "full_name": payload.get("name"),
            "avatar_url": payload.get("picture"),
        }

    async def require_auth(self, request: Request) -> dict:
        """
        Require authentication. Raises HTTPException if not authenticated.
        Returns user info dict.
        """
        user = await self.get_current_user(request)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


# Global instance
clerk_auth = ClerkAuth()
