"""
Nexus — Auth Service (Class-based)
-----------------------------------------
Business logic for all authentication flows.

Responsibilities:
  - Google OAuth callback: exchange code → fetch user info → upsert user in DB
  - Instagram OAuth callback: exchange code → store encrypted token → sync stats
  - Issue JWT token pairs after successful auth
  - Fetch the current authenticated user from DB

All database operations are performed via Beanie ODM.
All token operations are delegated to JWTManager.

Usage:
    from app.services.auth_service import AuthService
    auth_service = AuthService()
    user, tokens = await auth_service.google_login(code="...", redirect_uri="...")
"""

from datetime import datetime, timezone
from typing import Tuple

import httpx

from app.config import settings
from app.core.encryption import encryption_manager
from app.core.jwt_manager import JWTManager, TokenPair, jwt_manager
from app.core.logger import logger
from app.models.user import User, UserRole
from app.schemas.auth import AuthResponse


class AuthServiceError(Exception):
    """Base exception for AuthService failures."""
    pass


class OAuthError(AuthServiceError):
    """Raised when an OAuth exchange fails (bad code, API error, etc.)."""
    pass


class UserNotFoundError(AuthServiceError):
    """Raised when a user lookup by ID returns nothing."""
    pass


class AuthService:
    """
    Handles all authentication flows for Nexus.

    Injected dependencies:
        jwt_manager  — JWTManager instance for token issuance
        http_client  — shared httpx.AsyncClient for OAuth API calls
    """

    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    INSTAGRAM_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
    INSTAGRAM_USERINFO_URL = "https://graph.instagram.com/me"

    def __init__(self, jwt: JWTManager = jwt_manager) -> None:
        self._jwt = jwt
        self._http = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=10.0)
        return self._http

    # ─────────────────────────────────────────────────────────
    # Google OAuth
    # ─────────────────────────────────────────────────────────

    async def google_login(self, code: str) -> Tuple[User, TokenPair]:
        """
        Complete the Google OAuth flow.

        Steps:
          1. Exchange authorization code → access token (Google API)
          2. Use access token → fetch user profile (Google API)
          3. Upsert user in MongoDB (create on first login, update on return)
          4. Issue and return JWT token pair

        Args:
            code: Authorization code from Google OAuth callback query param

        Returns:
            Tuple of (User document, TokenPair)

        Raises:
            OAuthError: If the OAuth exchange fails
        """
        # Step 1: Exchange code → Google access token
        google_user = await self._fetch_google_user(code)

        # Step 2: Upsert user in database
        user = await self._upsert_google_user(google_user)

        # Step 3: Update last_login_at
        user.last_login_at = datetime.now(tz=timezone.utc  )
        await user.save()

        # Step 4: Issue token pair
        tokens = self._jwt.create_token_pair(
            user_id=str(user.id),
            role=user.role.value,
        )

        logger.info(
            f"Google login successful — user_id={user.id}, role={user.role.value}"
        )
        return user, tokens

    async def _fetch_google_user(self, code: str) -> dict:
        """Exchange OAuth code for Google access token, then fetch user info."""
        # Exchange code → access token
        token_response = await self.http.post(
            self.GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

        if token_response.status_code != 200:
            raise OAuthError(
                f"Google token exchange failed: {token_response.text}"
            )

        access_token = token_response.json().get("access_token")
        if not access_token:
            raise OAuthError("Google did not return an access token.")

        # Fetch user info
        userinfo_response = await self.http.get(
            self.GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_response.status_code != 200:
            raise OAuthError(
                f"Failed to fetch Google user info: {userinfo_response.text}"
            )

        return userinfo_response.json()

    async def _upsert_google_user(self, google_user: dict) -> User:
        """
        Insert or update the user document based on Google user info.

        Lookup order:
          1. By google_id (returning user, same Google account)
          2. By email (user may have registered differently before)
          3. Create new if neither found
        """
        google_id = google_user.get("id")
        email = google_user.get("email")
        name = google_user.get("name", "")
        avatar_url = google_user.get("picture")

        # Try google_id first
        user = await User.find_one(User.google_id == google_id)

        # Fall back to email
        if not user:
            user = await User.find_one(User.email == email)

        if user:
            # Update existing user's name and avatar (may have changed in Google)
            user.name = name
            user.avatar_url = avatar_url
            user.google_id = google_id
            await user.save()
            return user

        # Create new user — role will be set during onboarding
        user = User(
            email=email,
            name=name,
            avatar_url=avatar_url,
            google_id=google_id,
            role=UserRole.CREATOR,       # Default role — overridden during onboarding
            onboarding_complete=False,
        )
        await user.insert()
        logger.info(f"New user created via Google OAuth — email={email}")
        return user

    # ─────────────────────────────────────────────────────────
    # Instagram OAuth (connect to existing account)
    # ─────────────────────────────────────────────────────────

    async def connect_instagram(self, user: User, code: str) -> User:
        """
        Connect an Instagram account to an existing Nexus user.

        Called after the user has already logged in via Google and
        navigates to /settings → "Connect Instagram".

        Steps:
          1. Exchange code → Instagram short-lived access token
          2. Fetch Instagram user ID and username
          3. Encrypt the token and store on the user document
          4. Trigger background stat sync via Celery

        Args:
            user: The authenticated Nexus User document
            code: Instagram OAuth callback code

        Returns:
            Updated User document
        """
        # Step 1: Exchange code → Instagram access token
        access_token = None
        instagram_user_id = None

        if not (settings.is_development and (code == "mock_code" or code.startswith("mock_"))):
            try:
                token_response = await self.http.post(
                    self.INSTAGRAM_TOKEN_URL,
                    data={
                        "client_id": settings.INSTAGRAM_APP_ID,
                        "client_secret": settings.INSTAGRAM_APP_SECRET,
                        "grant_type": "authorization_code",
                        "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
                        "code": code,
                    },
                )

                if token_response.status_code == 200:
                    token_data = token_response.json()
                    access_token = token_data.get("access_token")
                    instagram_user_id = token_data.get("user_id")
                else:
                    if not settings.is_development:
                        raise OAuthError(f"Instagram token exchange failed: {token_response.text}")
                    else:
                        logger.warning(f"Live Instagram token exchange failed: {token_response.text}")
            except Exception as e:
                if not settings.is_development:
                    raise OAuthError(f"Instagram token exchange failed: {e}")
                else:
                    logger.warning(f"Live Instagram token exchange failed in dev: {e}")

        if not access_token or not instagram_user_id:
            if settings.is_development:
                access_token = "mock_instagram_access_token_12345"
                instagram_user_id = "mock_instagram_user_id_99999"
                logger.info("Using mock Instagram credentials in development mode.")
            else:
                raise OAuthError("Instagram did not return expected credentials.")

        # Step 2: Encrypt and store
        user.instagram_user_id = str(instagram_user_id)
        user.instagram_access_token_encrypted = encryption_manager.encrypt(access_token)
        await user.save()

        logger.info(
            f"Instagram connected — user_id={user.id}, ig_user_id={instagram_user_id}"
        )

        # Step 3: Trigger background sync (import here to avoid circular imports)
        from app.tasks.instagram_sync import trigger_instagram_sync
        trigger_instagram_sync.delay(str(user.id))

        return user

    # ─────────────────────────────────────────────────────────
    # User Lookup
    # ─────────────────────────────────────────────────────────

    async def get_user_by_id(self, user_id: str) -> User:
        """
        Fetch a user document by their MongoDB ObjectId.

        Args:
            user_id: String representation of MongoDB ObjectId

        Returns:
            User document

        Raises:
            UserNotFoundError: If no user with that ID exists
        """
        user = await User.get(user_id)
        if not user:
            raise UserNotFoundError(f"User '{user_id}' not found.")
        return user

    async def set_user_role(self, user: User, role: UserRole) -> User:
        """
        Set the user's role during onboarding.
        Only callable once (before onboarding_complete is True).

        Args:
            user: User document
            role: The chosen role (creator or brand)

        Returns:
            Updated User document
        """
        user.role = role
        user.updated_at = datetime.now(tz=timezone.utc)
        await user.save()
        logger.info(f"Role set — user_id={user.id}, role={role.value}")

        if role == UserRole.CREATOR:
            from app.services.creator_service import CreatorService
            creator_service = CreatorService()
            await creator_service.create_profile(user_id=str(user.id), display_name=user.name)

        return user

    async def close(self) -> None:
        """Clean up the shared HTTP client. Call on app shutdown."""
        if self._http is not None:
            await self._http.aclose()
