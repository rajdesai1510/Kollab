"""
Nexus — Auth Middleware (Class-based)
--------------------------------------------
Provides an AuthMiddleware class whose methods are FastAPI dependency callables
for extracting and validating the authenticated user from the Authorization header.

All methods on AuthMiddleware are async and designed to be passed to FastAPI's
Depends() injection system as bound methods:

    Depends(auth_middleware.get_current_user)
    Depends(auth_middleware.get_optional_user)
    Depends(auth_middleware.require_role(UserRole.BRAND))

A module-level singleton `auth_middleware` is exported for import by all routers.

Class hierarchy:
    BearerTokenExtractor    — extracts raw token string from Authorization header
    AuthMiddleware          — validates JWT, fetches User, enforces roles
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.jwt_manager import TokenExpiredError, TokenInvalidError, jwt_manager
from app.core.logger import logger
from app.models.user import User, UserRole


# ─────────────────────────────────────────────────────────────
# Bearer Token Extractor (Class-based)
# ─────────────────────────────────────────────────────────────

class BearerTokenExtractor:
    """
    Callable class that extracts the raw Bearer token string from the
    Authorization header.

    Overrides the default HTTPBearer behavior to return a clean 401 (not 403)
    when the header is missing, with a descriptive error message.

    Usage:
        _required_bearer = BearerTokenExtractor(auto_error=True)
        token: str = Depends(_required_bearer)
    """

    def __init__(self, auto_error: bool = True) -> None:
        self._bearer = HTTPBearer(auto_error=auto_error)
        self._auto_error = auto_error

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(
            HTTPBearer(auto_error=False)
        ),
    ) -> Optional[str]:
        """Extract and return the raw token string, or raise 401."""
        if credentials is None:
            if self._auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please log in.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        if credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected 'Bearer'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return credentials.credentials


# ─────────────────────────────────────────────────────────────
# Auth Middleware (Class-based)
# ─────────────────────────────────────────────────────────────

class AuthMiddleware:
    """
    FastAPI dependency provider class for authentication and authorization.

    Methods are designed to be used directly with FastAPI's Depends():

        async def my_route(user: User = Depends(auth_middleware.get_current_user)):
            ...

        async def brand_only(user: User = Depends(auth_middleware.require_role(UserRole.BRAND))):
            ...

    Encapsulates:
        - Bearer token extraction (via BearerTokenExtractor instances)
        - JWT verification (via JWTManager)
        - User document lookup (via Beanie)
        - Role enforcement (via require_role factory method)
    """

    def __init__(self) -> None:
        # Two extractor instances: one that errors on missing token, one that allows None
        self._required_bearer = BearerTokenExtractor(auto_error=True)
        self._optional_bearer = BearerTokenExtractor(auto_error=False)

    # ─────────────────────────────────────────────────────────
    # Required Auth
    # ─────────────────────────────────────────────────────────

    async def get_current_user(
        self,
        token: str = Depends(BearerTokenExtractor(auto_error=True)),
    ) -> User:
        """
        FastAPI dependency method: extract and validate JWT, fetch User from DB.

        Raises HTTP 401 if:
          - No Authorization header provided
          - Token is expired
          - Token is malformed or invalid
          - User not found in database (deleted account)
          - User account is suspended (is_active=False)

        Usage:
            async def route(user: User = Depends(auth_middleware.get_current_user)):
        """
        try:
            payload = jwt_manager.verify_token(token, expected_type="access")
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token has expired. Please refresh your session.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except TokenInvalidError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await User.get(payload.sub)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found. Please log in again.",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been suspended. Contact support@nexus.in.",
            )

        return user

    # ─────────────────────────────────────────────────────────
    # Optional Auth
    # ─────────────────────────────────────────────────────────

    async def get_optional_user(
        self,
        token: Optional[str] = Depends(BearerTokenExtractor(auto_error=False)),
    ) -> Optional[User]:
        """
        FastAPI dependency method: return the current user or None.

        Used on public endpoints (discovery, campaign board) where the response
        changes slightly if the user is authenticated (e.g., showing "Connect" button).
        Never raises — returns None for unauthenticated requests.

        Usage:
            async def route(viewer: Optional[User] = Depends(auth_middleware.get_optional_user)):
        """
        if not token:
            return None

        try:
            payload = jwt_manager.verify_token(token, expected_type="access")
            user = await User.get(payload.sub)
            return user if (user and user.is_active) else None
        except (TokenExpiredError, TokenInvalidError):
            return None

    # ─────────────────────────────────────────────────────────
    # Role Enforcement
    # ─────────────────────────────────────────────────────────

    def require_role(self, *roles: UserRole):
        """
        Dependency factory method: enforce that the current user has one of the
        specified roles.

        Returns a FastAPI-compatible async callable (closure) that can be used
        directly with Depends().

        Usage:
            async def route(user: User = Depends(auth_middleware.require_role(UserRole.BRAND))):

        Args:
            *roles: One or more UserRole enum values the caller must have

        Returns:
            Async dependency function that returns the authenticated User if role matches,
            or raises HTTP 403 if role does not match.
        """
        # Capture self.get_current_user as a bound method for the inner dependency
        get_user = self.get_current_user

        async def role_checker(
            current_user: User = Depends(get_user),
        ) -> User:
            if current_user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"This action requires one of the following roles: "
                        f"{', '.join(r.value for r in roles)}."
                    ),
                )
            return current_user

        return role_checker


# ─────────────────────────────────────────────────────────────
# Module-level singleton — import this everywhere
# ─────────────────────────────────────────────────────────────
auth_middleware = AuthMiddleware()

# ─────────────────────────────────────────────────────────────
# Convenience aliases — keeps existing import paths working
# and provides ergonomic shorthand in routers.
# ─────────────────────────────────────────────────────────────
get_current_user = auth_middleware.get_current_user
get_optional_user = auth_middleware.get_optional_user
require_role = auth_middleware.require_role
