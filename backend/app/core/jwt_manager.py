"""
Nexus — JWT Manager (Class-based)
-----------------------------------------
Wraps python-jose with a class-based interface for issuing
and verifying access and refresh tokens.

Token types:
  access  — short-lived (default 60 min), sent with every API request
  refresh — long-lived (default 30 days), used to obtain new access tokens

Usage:
    from app.core.jwt_manager import jwt_manager

    access_token = jwt_manager.create_access_token(user_id="abc", role="creator")
    payload = jwt_manager.verify_token(token)
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel

from app.config import settings
from app.core.logger import logger


# ─────────────────────────────────────────────────────────────
# Token Payload Schema
# ─────────────────────────────────────────────────────────────

class TokenPayload(BaseModel):
    """
    Validated payload returned after decoding a JWT.

    Fields:
        sub     — user ID (MongoDB ObjectId as string)
        role    — user role: 'creator' | 'brand' | 'admin'
        type    — token type: 'access' | 'refresh'
        exp     — expiry timestamp (Unix epoch)
        iat     — issued-at timestamp (Unix epoch)
    """
    sub: str            # User ID
    role: str           # User role
    type: str           # 'access' or 'refresh'
    exp: Optional[int] = None
    iat: Optional[int] = None


class TokenPair(BaseModel):
    """Response model for newly issued token pairs."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int     # Access token TTL in seconds


# ─────────────────────────────────────────────────────────────
# Exceptions
# ─────────────────────────────────────────────────────────────

class TokenExpiredError(Exception):
    """Raised when a token's `exp` claim is in the past."""
    pass


class TokenInvalidError(Exception):
    """Raised when a token cannot be decoded or has invalid claims."""
    pass


# ─────────────────────────────────────────────────────────────
# JWT Manager Class
# ─────────────────────────────────────────────────────────────

class JWTManager:
    """
    Manages JWT token creation and verification.

    Delegates all cryptographic operations to `python-jose`.
    Provides a clean, typed interface that decouples route handlers
    from JWT implementation details.
    """

    def __init__(self) -> None:
        self._secret_key = settings.JWT_SECRET_KEY
        self._algorithm = settings.JWT_ALGORITHM
        self._access_ttl = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        self._refresh_ttl = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    # ─────────────────────────────────────────────────────────
    # Token Creation
    # ─────────────────────────────────────────────────────────

    def create_access_token(self, user_id: str, role: str) -> str:
        """
        Issue a short-lived access token.

        Args:
            user_id: MongoDB ObjectId of the user (as string)
            role: 'creator' | 'brand' | 'admin'

        Returns:
            Signed JWT string
        """
        return self._create_token(
            user_id=user_id,
            role=role,
            token_type="access",
            ttl=self._access_ttl,
        )

    def create_refresh_token(self, user_id: str, role: str) -> str:
        """
        Issue a long-lived refresh token.

        Stored in an httpOnly cookie on the client.
        Used only on the /auth/refresh endpoint.

        Args:
            user_id: MongoDB ObjectId of the user (as string)
            role: 'creator' | 'brand' | 'admin'

        Returns:
            Signed JWT string
        """
        return self._create_token(
            user_id=user_id,
            role=role,
            token_type="refresh",
            ttl=self._refresh_ttl,
        )

    def create_token_pair(self, user_id: str, role: str) -> TokenPair:
        """
        Issue both access + refresh tokens in a single call.
        Used after login / OAuth callback.
        """
        return TokenPair(
            access_token=self.create_access_token(user_id, role),
            refresh_token=self.create_refresh_token(user_id, role),
            expires_in=int(self._access_ttl.total_seconds()),
        )

    def _create_token(
        self,
        user_id: str,
        role: str,
        token_type: str,
        ttl: timedelta,
    ) -> str:
        """Internal token builder — sets standard claims and signs the token."""
        now = datetime.utcnow()
        payload = {
            "sub": user_id,
            "role": role,
            "type": token_type,
            "iat": now,
            "exp": now + ttl,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    # ─────────────────────────────────────────────────────────
    # Token Verification
    # ─────────────────────────────────────────────────────────

    def verify_token(self, token: str, expected_type: str = "access") -> TokenPayload:
        """
        Decode and validate a JWT token.

        Args:
            token: Raw JWT string (from Authorization header or cookie)
            expected_type: 'access' or 'refresh'

        Returns:
            TokenPayload with validated claims

        Raises:
            TokenExpiredError: Token's exp is in the past
            TokenInvalidError: Token is malformed or has wrong type
        """
        try:
            raw_payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
        except ExpiredSignatureError:
            raise TokenExpiredError("Token has expired. Please log in again.")
        except JWTError as exc:
            logger.warning(f"JWT decode failed: {exc}")
            raise TokenInvalidError(f"Invalid token: {exc}")

        payload = TokenPayload(**raw_payload)

        # Ensure the token is the expected type
        if payload.type != expected_type:
            raise TokenInvalidError(
                f"Expected '{expected_type}' token but received '{payload.type}'."
            )

        return payload


# ─────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────
jwt_manager = JWTManager()
