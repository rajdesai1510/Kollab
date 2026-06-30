"""
Nexus — Campaign Document Model
---------------------------------------
The `campaigns` collection stores campaign briefs posted by brands.

A campaign brief is a "job posting" from a brand:
"I need 2 Instagram Reels and 3 Stories from a fitness creator in Bangalore,
 budget ₹10,000–₹20,000, by August 30."

Creators browse these and express interest. The brand then reviews
interested creators and sends connection requests to the ones they like.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from beanie import Document
from pydantic import Field

from app.models.creator_profile import NicheCategory


class DeliverableType(str, Enum):
    """The type of content deliverable the brand is requesting."""
    INSTAGRAM_REEL = "Instagram Reel"
    INSTAGRAM_POST = "Instagram Post"
    INSTAGRAM_STORY = "Instagram Story"
    INSTAGRAM_REEL_AND_STORY = "Instagram Reel + Stories"
    YOUTUBE_SHORT = "YouTube Short"
    YOUTUBE_VIDEO = "YouTube Video"
    BLOG_POST = "Blog Post"
    PODCAST_MENTION = "Podcast Mention"
    OTHER = "Other"


class CampaignStatus(str, Enum):
    """
    Lifecycle status of a campaign brief.
    - OPEN: Active, visible to creators, accepting expressions of interest
    - PAUSED: Temporarily hidden by the brand
    - CLOSED: Brand has found their creators / campaign ended
    """
    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class Campaign(Document):
    """
    Campaign brief document. Stored in the `campaigns` collection.

    Brands post these to describe what they're looking for.
    Creators browse them on the Campaign Board and express interest.
    """

    # ── Ownership ──────────────────────────────────────────────
    brand_id: str                  # References BrandProfile._id (indexed via Settings.indexes)
    brand_user_id: str             # References User._id (for auth checks)

    # ── Campaign Details ───────────────────────────────────────
    title: str                     # e.g., "Looking for fitness creators in Bangalore"
    description: str               # Full brief: what you need, what you offer, instructions
    deliverable_type: DeliverableType

    # ── Budget ─────────────────────────────────────────────────
    budget_min: Optional[int] = None    # Minimum budget in INR
    budget_max: Optional[int] = None    # Maximum budget in INR

    # ── Targeting ──────────────────────────────────────────────
    target_niches: List[NicheCategory] = Field(default_factory=list)
    target_city: Optional[str] = None   # Specific city e.g. "Bangalore"
    target_state: Optional[str] = None  # State e.g. "Karnataka"
    pan_india: bool = False             # True = open to creators from anywhere in India

    # ── Timeline ───────────────────────────────────────────────
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    # ── Interest Tracking ──────────────────────────────────────
    # List of creator_profile IDs who expressed interest.
    # Kept size-bounded — we don't expect thousands per campaign at MVP scale.
    interested_creator_ids: List[str] = Field(default_factory=list)
    interested_count: int = 0           # Denormalised count for display

    # ── Status ─────────────────────────────────────────────────
    status: CampaignStatus = CampaignStatus.OPEN  # indexed via Settings.indexes

    # ── Timestamps ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "campaigns"
        use_state_management = True
        indexes = [
            "brand_id",
            "brand_user_id",
            "status",
            "target_niches",
            "target_city",
            "target_state",
            "pan_india",
            "created_at",
        ]
