"""
Nexus — Pydantic Schemas: Auth
--------------------------------------
Request/response schemas for all auth-related endpoints.

Separated from Beanie models so that:
  - API contracts stay stable even if DB schema changes
  - Sensitive fields (encrypted tokens, password hashes) never leak in responses
  - We can version API schemas independently of DB documents
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ─────────────────────────────────────────────────────────────
# Responses
# ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Public-safe user representation. Never includes tokens or hashes."""
    id: str
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None
    role: str
    onboarding_complete: bool
    instagram_connected: bool   # True if instagram_user_id is set
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Returned after successful login or token refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int             # Seconds until access token expiry
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    """Body for the POST /auth/refresh endpoint."""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """New access token issued after refresh."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class OnboardingRoleRequest(BaseModel):
    """
    Body for POST /auth/onboarding/role.
    Sets the user's role on first login (creator or brand).
    """
    role: str = Field(pattern="^(creator|brand)$")

    model_config = {
        "json_schema_extra": {
            "example": {"role": "creator"}
        }
    }


class InstagramConnectRequest(BaseModel):
    """Body for POST /auth/instagram/connect (REST fallback)."""
    code: str   # OAuth callback code from Instagram

class InstagramAuthUrlResponse(BaseModel):
    """Response containing the Instagram OAuth authorization URL."""
    url: str
