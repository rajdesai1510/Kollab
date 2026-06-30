"""
Nexus — User Document Model
-----------------------------------
The `users` collection stores authentication data and account-level information
for all three roles: creator, brand, and admin.

Profile-specific data (follower counts, business info, etc.) lives in the
corresponding `creator_profiles` or `brand_profiles` collections, linked
via `user_id`. This separation keeps auth data lean and easy to reason about.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pydantic import EmailStr, Field


class UserRole(str, Enum):
    """Determines which profile type and which permissions the user has."""
    CREATOR = "creator"
    BRAND = "brand"
    ADMIN = "admin"


class User(Document):
    """
    Core user document. Stored in the `users` collection.

    One user → one role → one profile document (CreatorProfile or BrandProfile).
    OAuth tokens are stored encrypted via the encryption utility.
    """

    # ── Identity ──────────────────────────────────────────────
    email: Indexed(EmailStr, unique=True)          # type: ignore[valid-type]
    name: str
    avatar_url: Optional[str] = None
    role: UserRole

    # ── Google OAuth ──────────────────────────────────────────
    google_id: Optional[Indexed(str, unique=True)] = None  # type: ignore[valid-type]

    # ── Instagram OAuth (stored after user connects Instagram) ─
    # Encrypted at rest using the Fernet symmetric key (ENCRYPTION_KEY env var)
    instagram_user_id: Optional[str] = None
    instagram_access_token_encrypted: Optional[str] = None  # Encrypted
    instagram_token_expires_at: Optional[datetime] = None

    # ── Account Status ─────────────────────────────────────────
    is_active: bool = True           # Can log in and use the platform
    is_verified: bool = False        # Admin-verified (optional trust layer)
    onboarding_complete: bool = False  # Has completed the role-specific onboarding flow

    # ── Preferences ────────────────────────────────────────────
    notifications_email: bool = True  # Opt-in to email notifications

    # ── Timestamps ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None

    class Settings:
        name = "users"              # MongoDB collection name
        use_state_management = True # Enables .save() change tracking
        indexes = [
            "email",
            "google_id",
            "role",
            "is_active",
            "created_at",
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "email": "creator@example.com",
                "name": "Priya Sharma",
                "role": "creator",
                "is_active": True,
                "onboarding_complete": False,
            }
        }
