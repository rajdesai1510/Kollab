"""
Nexus — Pydantic Schemas: Creator
-----------------------------------------
Request/response schemas for creator profile endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.creator_profile import (
    CollabType,
    FollowerTier,
    Language,
    NicheCategory,
)


# ─────────────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────────────

class CreatorUpdateRequest(BaseModel):
    """
    Body for PUT /creators/profile.
    All fields are optional — only provided fields are updated.
    """
    display_name: Optional[str] = Field(None, min_length=2, max_length=80)
    bio: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    niches: Optional[List[NicheCategory]] = Field(None, max_length=5)
    languages: Optional[List[Language]] = None
    collab_types: Optional[List[CollabType]] = None
    rate_min: Optional[int] = Field(None, ge=0, le=10000000)
    rate_max: Optional[int] = Field(None, ge=0, le=10000000)
    open_to_collabs: Optional[bool] = None
    avatar_url: Optional[str] = None


class CreatorSearchFilters(BaseModel):
    """
    Query parameters for GET /creators/search.
    All filters are optional and combinable.
    """
    city: Optional[str] = None
    state: Optional[str] = None
    niches: Optional[List[NicheCategory]] = None
    follower_tier: Optional[FollowerTier] = None
    collab_types: Optional[List[CollabType]] = None
    min_engagement_rate: Optional[float] = Field(None, ge=0, le=100)
    max_rate: Optional[int] = Field(None, ge=0, le=10000000)
    open_to_collabs_only: bool = True


# ─────────────────────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────────────────────

class InstagramStatsResponse(BaseModel):
    """Instagram stats sub-object shown on creator profile."""
    handle: Optional[str] = None
    profile_pic_url: Optional[str] = None
    followers: int = 0
    following: int = 0
    post_count: int = 0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    engagement_rate: float = 0.0
    instagram_category: Optional[str] = None
    last_synced: Optional[datetime] = None


class CreatorCardResponse(BaseModel):
    """
    Compact creator card — shown in discovery grid.
    Minimal data for fast list rendering.
    """
    id: str
    display_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    niches: List[NicheCategory] = []
    collab_types: List[CollabType] = []
    instagram_handle: Optional[str] = None
    instagram_profile_pic_url: Optional[str] = None
    instagram_followers: int = 0
    instagram_engagement_rate: float = 0.0
    follower_tier: Optional[FollowerTier] = None
    rate_min: Optional[int] = None
    rate_max: Optional[int] = None
    open_to_collabs: bool = True
    is_featured: bool = False

    model_config = {"from_attributes": True}


class CreatorProfileResponse(BaseModel):
    """
    Full creator profile — shown on /creators/[id] page.
    Includes Instagram stats details and all profile fields.
    """
    id: str
    user_id: str
    display_name: str
    bio: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    niches: List[NicheCategory] = []
    languages: List[Language] = []
    collab_types: List[CollabType] = []
    instagram_handle: Optional[str] = None
    instagram_profile_pic_url: Optional[str] = None
    instagram_followers: int = 0
    instagram_following: int = 0
    instagram_post_count: int = 0
    instagram_avg_likes: float = 0.0
    instagram_avg_comments: float = 0.0
    instagram_engagement_rate: float = 0.0
    instagram_category: Optional[str] = None
    instagram_last_synced: Optional[datetime] = None
    follower_tier: Optional[FollowerTier] = None
    rate_min: Optional[int] = None
    rate_max: Optional[int] = None
    open_to_collabs: bool = True
    profile_views: int = 0
    total_connections: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CreatorSearchResponse(BaseModel):
    """Paginated creator discovery search response."""
    results: List[CreatorCardResponse]
    total: int
    page: int
    limit: int
    has_more: bool
