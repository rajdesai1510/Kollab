"""
Nexus — Creator Profile Document Model
----------------------------------------------
The `creator_profiles` collection stores everything specific to a creator:
Instagram stats (auto-synced from the Graph API), niche tags, city/geolocation,
rate card, collaboration preferences, and discovery metrics.

One-to-one relationship with the `users` collection via `user_id`.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, Link
from pydantic import Field

from app.models.user import User


class NicheCategory(str, Enum):
    """Standardised niche categories for discovery filtering."""
    FOOD = "Food"
    FITNESS = "Fitness"
    FASHION = "Fashion"
    BEAUTY = "Beauty"
    TECHNOLOGY = "Technology"
    TRAVEL = "Travel"
    LIFESTYLE = "Lifestyle"
    GAMING = "Gaming"
    EDUCATION = "Education"
    FINANCE = "Finance"
    PARENTING = "Parenting"
    MUSIC = "Music"
    COMEDY = "Comedy"
    HEALTH = "Health"
    AUTOMOTIVE = "Automotive"
    REAL_ESTATE = "Real Estate"
    OTHER = "Other"


class CollabType(str, Enum):
    """Types of collaborations the creator is open to."""
    PAID_POST = "Paid Post"
    PRODUCT_SEEDING = "Product Seeding"
    LONG_TERM_AMBASSADOR = "Long-term Ambassador"
    BARTER = "Barter"
    AFFILIATE = "Affiliate"
    EVENT_COVERAGE = "Event Coverage"


class FollowerTier(str, Enum):
    """
    Follower tier classification.
    Used for discovery filtering — brands often target specific tiers.
    """
    NANO = "nano"       # 1K   – 10K followers
    MICRO = "micro"     # 10K  – 100K followers
    MID = "mid"         # 100K – 500K followers
    MACRO = "macro"     # 500K – 1M followers


class Language(str, Enum):
    """Languages the creator produces content in."""
    ENGLISH = "English"
    HINDI = "Hindi"
    BENGALI = "Bengali"
    TAMIL = "Tamil"
    TELUGU = "Telugu"
    MARATHI = "Marathi"
    GUJARATI = "Gujarati"
    KANNADA = "Kannada"
    MALAYALAM = "Malayalam"
    PUNJABI = "Punjabi"
    OTHER = "Other"


class InstagramStats(dict):
    """
    Nested model for Instagram statistics.
    These are auto-populated by the Celery background sync task
    and refreshed every 48 hours.
    """
    handle: str = ""
    profile_pic_url: Optional[str] = None
    followers: int = 0
    following: int = 0
    post_count: int = 0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    engagement_rate: float = 0.0  # (avg_likes + avg_comments) / followers * 100
    instagram_category: Optional[str] = None  # e.g., "Personal Blog", "Fitness"
    last_synced: Optional[datetime] = None


class CreatorProfile(Document):
    """
    Creator profile document. Stored in the `creator_profiles` collection.

    Instagram stats are stored denormalised here (not fetched live on every
    discovery request) for performance. The Celery task refreshes them periodically.
    """

    # ── Link to User ───────────────────────────────────────────
    user_id: Indexed(str)  # type: ignore[valid-type]

    # ── Display Info ───────────────────────────────────────────
    display_name: str
    bio: Optional[str] = None

    # ── Location (Geolocation + Named Fields) ──────────────────
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # ── Niche + Content ────────────────────────────────────────
    niches: List[NicheCategory] = Field(default_factory=list)
    languages: List[Language] = Field(default=[Language.ENGLISH])
    collab_types: List[CollabType] = Field(default_factory=list)

    # ── Rate Card (Optional) ───────────────────────────────────
    rate_min: Optional[int] = None   # Minimum fee in INR
    rate_max: Optional[int] = None   # Maximum fee in INR

    # ── Instagram Stats (Auto-synced) ──────────────────────────
    instagram_handle: Optional[str] = None
    instagram_followers: int = 0
    instagram_following: int = 0
    instagram_post_count: int = 0
    instagram_avg_likes: float = 0.0
    instagram_avg_comments: float = 0.0
    instagram_engagement_rate: float = 0.0
    instagram_profile_pic_url: Optional[str] = None
    instagram_category: Optional[str] = None
    instagram_last_synced: Optional[datetime] = None

    # ── Computed Tier (set by sync task) ──────────────────────
    follower_tier: Optional[FollowerTier] = None

    # ── Discoverability ────────────────────────────────────────
    open_to_collabs: bool = True    # Brands can only see/contact when True
    is_featured: bool = False       # Admin-curated featured creators

    # ── Metrics (updated by background tasks) ─────────────────
    profile_views: int = 0
    total_connections: int = 0
    connections_this_month: int = 0    # Reserved for future subscription limits

    # ── Timestamps ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "creator_profiles"
        use_state_management = True
        indexes = [
            "user_id",
            "niches",
            "follower_tier",
            "instagram_engagement_rate",
            "open_to_collabs",
            "city",
            "state",
            [("latitude", 1), ("longitude", 1)],  # 2D index for geo queries
            "is_featured",
            "instagram_followers",
        ]

    @property
    def computed_follower_tier(self) -> FollowerTier:
        """Compute the follower tier from the current Instagram follower count."""
        if self.instagram_followers < 10_000:
            return FollowerTier.NANO
        elif self.instagram_followers < 100_000:
            return FollowerTier.MICRO
        elif self.instagram_followers < 500_000:
            return FollowerTier.MID
        else:
            return FollowerTier.MACRO
