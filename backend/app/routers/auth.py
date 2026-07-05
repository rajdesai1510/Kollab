"""
Nexus — Auth Router (Class-based)
----------------------------------------
Handles: Google OAuth, Instagram OAuth connect, current user,
         logout, onboarding role selection, token refresh.

Dependencies flow:
  AuthRouter → AuthService → JWTManager, EncryptionManager, DB (Beanie)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.config import settings
from app.core.jwt_manager import TokenExpiredError, TokenInvalidError, jwt_manager
from app.core.token_store import token_store
from app.middleware.auth_middleware import auth_middleware
from app.models.user import User, UserRole
from app.schemas.auth import (
    AuthResponse,
    OnboardingRoleRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    UserResponse,
    InstagramConnectRequest,
    InstagramAuthUrlResponse,
)
from app.services.auth_service import AuthService, OAuthError


class AuthRouter:
    """
    Class-based router for all authentication-related endpoints.

    Encapsulates:
        - AuthService instance
        - All route handler methods
        - Route registration logic

    Usage:
        auth_router = AuthRouter()
        app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self.auth_service = AuthService()
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes on self.router using add_api_route."""
        # Google OAuth
        self.router.add_api_route(
            "/google",
            self.google_oauth_redirect,
            methods=["GET"],
            summary="Redirect to Google OAuth",
        )
        self.router.add_api_route(
            "/google/callback",
            self.google_oauth_callback,
            methods=["GET"],
            summary="Google OAuth callback",
            response_class=RedirectResponse,
        )
        # Instagram OAuth
        self.router.add_api_route(
            "/instagram/start",
            self.instagram_oauth_redirect,
            methods=["GET"],
            summary="Redirect to Instagram OAuth",
            response_class=RedirectResponse,
        )
        self.router.add_api_route(
            "/instagram/url",
            self.get_instagram_url,
            methods=["GET"],
            summary="Get Instagram Auth URL",
            response_model=InstagramAuthUrlResponse,
        )
        self.router.add_api_route(
            "/instagram/connect",
            self.connect_instagram,
            methods=["POST"],
            summary="Connect Instagram account",
            response_model=UserResponse,
        )
        # Current user
        self.router.add_api_route(
            "/me",
            self.get_me,
            methods=["GET"],
            summary="Get current user",
            response_model=UserResponse,
        )
        # Onboarding
        self.router.add_api_route(
            "/onboarding/role",
            self.set_role,
            methods=["POST"],
            summary="Set user role during onboarding",
            response_model=UserResponse,
        )
        # Token management
        self.router.add_api_route(
            "/refresh",
            self.refresh_token,
            methods=["POST"],
            summary="Refresh access token",
            response_model=TokenRefreshResponse,
        )
        self.router.add_api_route(
            "/logout",
            self.logout,
            methods=["POST"],
            summary="Logout",
        )

    # ─────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────

    def _build_user_response(self, user: User) -> UserResponse:
        """Map a User document to the public-safe UserResponse schema."""
        return UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            role=user.role.value,
            onboarding_complete=user.onboarding_complete,
            instagram_connected=bool(user.instagram_user_id),
            created_at=user.created_at,
        )

    # ─────────────────────────────────────────────────────────
    # Google OAuth
    # ─────────────────────────────────────────────────────────

    async def google_oauth_redirect(self) -> RedirectResponse:
        """Redirect the browser to Google's OAuth consent screen."""
        return RedirectResponse(url=settings.google_auth_url)

    async def google_oauth_callback(
        self,
        code: str = Query(..., description="Authorization code from Google"),
    ) -> RedirectResponse:
        """
        Exchange the Google authorization code for a user session.

        Steps:
          1. Exchange code -> Google access token -> user info
          2. Upsert user in DB
          3. Issue JWT token pair
          4. Return tokens + user info

        On first login, onboarding_complete is False — the frontend
        redirects new users to /onboarding for role selection.
        """
        try:
            user, tokens = await self.auth_service.google_login(code=code)
        except OAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )

        # Redirect back to the frontend callback page with both tokens in the URL
        frontend_callback_url = (
            f"{settings.FRONTEND_URL}/auth/callback"
            f"?token={tokens.access_token}"
            f"&refresh_token={tokens.refresh_token}"
        )
        return RedirectResponse(url=frontend_callback_url)

    # ─────────────────────────────────────────────────────────
    # Instagram Connect (requires authenticated user)
    # ─────────────────────────────────────────────────────────

    async def instagram_oauth_redirect(self) -> RedirectResponse:
        """Redirect the browser directly to Instagram's OAuth consent screen."""
        return RedirectResponse(url=settings.instagram_auth_url)

    async def get_instagram_url(self) -> InstagramAuthUrlResponse:
        """Get Instagram's OAuth consent screen URL (JSON — for programmatic use)."""
        return InstagramAuthUrlResponse(url=settings.instagram_auth_url)

    async def connect_instagram(
        self,
        request: InstagramConnectRequest,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> UserResponse:
        """
        Connect an Instagram account to the current user's Nexus profile.
        Triggers background Celery task to sync Instagram stats immediately.
        """
        try:
            updated_user = await self.auth_service.connect_instagram(
                user=current_user, code=request.code
            )
        except OAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            )

        return self._build_user_response(updated_user)

    # ─────────────────────────────────────────────────────────
    # Current User / Me
    # ─────────────────────────────────────────────────────────

    async def get_me(
        self,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> UserResponse:
        """Return the authenticated user's profile. Used on every app load."""
        return self._build_user_response(current_user)

    # ─────────────────────────────────────────────────────────
    # Onboarding — Set Role
    # ─────────────────────────────────────────────────────────

    async def set_role(
        self,
        body: OnboardingRoleRequest,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> UserResponse:
        """
        Set the user's role (creator or brand) during onboarding.
        Can only be called when onboarding_complete is False.
        """
        if current_user.onboarding_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Onboarding is already complete. Role cannot be changed.",
            )

        role = UserRole(body.role)
        updated_user = await self.auth_service.set_user_role(current_user, role)
        return self._build_user_response(updated_user)

    # ─────────────────────────────────────────────────────────
    # Token Refresh
    # ─────────────────────────────────────────────────────────

    async def refresh_token(
        self,
        body: TokenRefreshRequest,
    ) -> TokenRefreshResponse:
        """
        Issue a new access token using a valid refresh token.

        Validation:
          1. JWT signature + expiry (python-jose)
          2. jti exists in Redis (not revoked)

        Rotation:
          - Old refresh token is deleted from Redis
          - A new refresh token is issued and stored in Redis
          - Both new tokens are returned to the client
        """
        # Step 1: Validate JWT structure + expiry
        try:
            payload = jwt_manager.verify_token(
                body.refresh_token, expected_type="refresh"
            )
        except TokenExpiredError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired. Please log in again.",
            )
        except TokenInvalidError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )

        # Step 2: Validate jti exists in Redis (reuse / stolen token check)
        if not payload.jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token (missing jti). Please log in again.",
            )

        is_valid = await token_store.is_refresh_token_valid(
            user_id=payload.sub, jti=payload.jti
        )
        if not is_valid:
            # Token was already used or explicitly revoked — possible token theft
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked. Please log in again.",
            )

        # Step 3: Rotate — revoke old token, issue a new pair
        await token_store.revoke_refresh_token(user_id=payload.sub, jti=payload.jti)
        new_pair = await jwt_manager.create_token_pair(
            user_id=payload.sub, role=payload.role
        )

        return TokenRefreshResponse(
            access_token=new_pair.access_token,
            refresh_token=new_pair.refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ─────────────────────────────────────────────────────────
    # Logout
    # ─────────────────────────────────────────────────────────

    async def logout(
        self,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> dict:
        """
        Revoke all refresh tokens for the current user in Redis, then log out.

        The access token remains technically valid until it expires (60 min),
        but without a valid refresh token the session cannot be renewed.
        For stricter security, add access token revocation via a Redis blocklist.
        """
        await token_store.revoke_all_refresh_tokens(user_id=str(current_user.id))
        return {"message": "Logged out successfully."}


# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
auth_router = AuthRouter()
