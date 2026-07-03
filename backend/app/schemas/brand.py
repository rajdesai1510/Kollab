"""
Nexus — Brand Schemas
-----------------------------
Pydantic request/response models for brand profile operations.
Moved here from routers/brands.py for proper separation of concerns.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.brand_profile import BrandCategory


class BrandCreateRequest(BaseModel):
    """Body for POST /brands/profile — brand creates profile during onboarding."""

    business_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    instagram_handle: Optional[str] = None
    tagline: Optional[str] = None
    website_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "business_name": "Bloom Naturals",
                "category": "Beauty & Personal Care",
                "city": "Mumbai",
                "state": "Maharashtra",
            }
        }
    }


class BrandUpdateRequest(BaseModel):
    """Body for PUT /brands/profile — partial brand profile update."""

    business_name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    website_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class BrandProfileResponse(BaseModel):
    """Full brand profile — returned on all brand profile endpoints."""

    id: str
    user_id: str
    business_name: str
    tagline: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    category: Optional[str] = None
    website_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    total_connections: int = 0
    total_campaigns_posted: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
