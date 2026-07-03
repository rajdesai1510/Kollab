"""
Nexus — Brand Profile Document Model
-------------------------------------------
The `brand_profiles` collection stores all information specific to a brand/business:
their category, city, website, and discovery/connection metrics.

One-to-one relationship with the `users` collection via `user_id`.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field, HttpUrl


class BrandCategory(str, Enum):
    """Business category — used for creator niche matching suggestions."""
    FOOD_BEVERAGE = "Food & Beverage"
    FITNESS_WELLNESS = "Fitness & Wellness"
    FASHION_APPAREL = "Fashion & Apparel"
    BEAUTY_SKINCARE = "Beauty & Skincare"
    TECHNOLOGY = "Technology"
    EDUCATION = "Education"
    TRAVEL_HOSPITALITY = "Travel & Hospitality"
    HOME_DECOR = "Home & Decor"
    HEALTH_PHARMA = "Health & Pharma"
    FINANCE = "Finance"
    AUTOMOTIVE = "Automotive"
    REAL_ESTATE = "Real Estate"
    RETAIL = "Retail"
    ECOMMERCE = "E-Commerce / D2C"
    ENTERTAINMENT = "Entertainment"
    NON_PROFIT = "Non-Profit / NGO"
    OTHER = "Other"


class BrandProfile(Document):
    """
    Brand profile document. Stored in the `brand_profiles` collection.

    A brand is typically a business, startup, or local establishment
    looking to collaborate with micro-influencer creators in their region.
    """

    # ── Link to User ───────────────────────────────────────────
    user_id: Indexed(str)  # type: ignore[valid-type]

    # ── Brand Identity ─────────────────────────────────────────
    business_name: str
    tagline: Optional[str] = None          # Short description shown on card
    description: Optional[str] = None     # Longer description on full profile
    logo_url: Optional[str] = None        # Stored in Cloudflare R2
    category: Optional[str] = None

    # ── Online Presence ────────────────────────────────────────
    website_url: Optional[str] = None
    instagram_handle: Optional[str] = None  # Brand's own Instagram (optional)

    # ── Location (Geolocation + Named Fields) ──────────────────
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # ── Metrics ────────────────────────────────────────────────
    total_connections: int = 0           # Total accepted connections
    connections_this_month: int = 0      # Reserved for subscription limit enforcement
    total_campaigns_posted: int = 0      # Running count of campaign briefs posted

    # ── Timestamps ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "brand_profiles"
        use_state_management = True
        indexes = [
            "user_id",
            "category",
            "city",
            "state",
            [("latitude", 1), ("longitude", 1)],
        ]
