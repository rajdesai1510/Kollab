"""
Nexus — Pydantic Schemas: Campaign, Connection, Message
--------------------------------------------------------------
Grouped here for brevity — each can be split into its own file as the
codebase grows.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus, DeliverableType
from app.models.connection import ConnectionStatus
from app.models.creator_profile import NicheCategory


# ════════════════════════════════════════════════════════════
# CAMPAIGN Schemas
# ════════════════════════════════════════════════════════════

class CampaignCreateRequest(BaseModel):
    """Body for POST /campaigns — brand posts a new brief."""
    title: str = Field(..., min_length=10, max_length=200)
    description: str = Field(..., min_length=30, max_length=3000)
    deliverable_type: DeliverableType
    budget_min: Optional[int] = Field(None, ge=0)
    budget_max: Optional[int] = Field(None, ge=0)
    target_niches: List[NicheCategory] = Field(default_factory=list, max_length=5)
    target_city: Optional[str] = Field(None, max_length=100)
    target_state: Optional[str] = Field(None, max_length=100)
    pan_india: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Looking for fitness creators in Bangalore",
                "description": "We're a D2C protein brand looking for...",
                "deliverable_type": "Instagram Reel",
                "budget_min": 5000,
                "budget_max": 15000,
                "target_niches": ["Fitness"],
                "target_city": "Bangalore",
            }
        }
    }


class CampaignUpdateRequest(BaseModel):
    """Body for PUT /campaigns/{id} — partial updates."""
    title: Optional[str] = Field(None, min_length=10, max_length=200)
    description: Optional[str] = Field(None, min_length=30, max_length=3000)
    budget_min: Optional[int] = Field(None, ge=0)
    budget_max: Optional[int] = Field(None, ge=0)
    target_niches: Optional[List[NicheCategory]] = None
    target_city: Optional[str] = None
    status: Optional[CampaignStatus] = None


class CampaignResponse(BaseModel):
    """Full campaign brief — shown on /campaigns/[id]."""
    id: str
    brand_id: str
    title: str
    description: str
    deliverable_type: DeliverableType
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    target_niches: List[NicheCategory] = []
    target_city: Optional[str] = None
    target_state: Optional[str] = None
    pan_india: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    interested_count: int = 0
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignCardResponse(BaseModel):
    """Compact campaign card for the campaign board list."""
    id: str
    brand_id: str
    title: str
    deliverable_type: DeliverableType
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    target_niches: List[NicheCategory] = []
    target_city: Optional[str] = None
    pan_india: bool = False
    interested_count: int = 0
    status: CampaignStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class CampaignListResponse(BaseModel):
    """Paginated campaign list."""
    results: List[CampaignCardResponse]
    total: int
    page: int
    limit: int
    has_more: bool


# ════════════════════════════════════════════════════════════
# CONNECTION Schemas
# ════════════════════════════════════════════════════════════

class ConnectionRequestBody(BaseModel):
    """Body for POST /connections/request."""
    recipient_profile_id: str       # Creator's profile ID
    campaign_id: Optional[str] = None  # Optional: which campaign triggered this


class ConnectionResponse(BaseModel):
    """Single connection record."""
    id: str
    requester_id: str
    requester_profile_id: str
    recipient_id: str
    recipient_profile_id: str
    status: ConnectionStatus
    campaign_id: Optional[str] = None
    created_at: datetime
    accepted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ConnectionsListResponse(BaseModel):
    """
    Split response for the /connections page.
    accepted: active connections with chat unlocked.
    pending: incoming + outgoing requests.
    """
    accepted: List[ConnectionResponse]
    pending: List[ConnectionResponse]


# ════════════════════════════════════════════════════════════
# MESSAGE Schemas
# ════════════════════════════════════════════════════════════

class MessageSendRequest(BaseModel):
    """Body for POST /messages/{connection_id} (REST fallback)."""
    content: str = Field(..., min_length=1, max_length=5000)


class MessageResponse(BaseModel):
    """Single message in a chat thread."""
    id: str
    connection_id: str
    sender_id: str
    content: str
    is_read: bool
    sent_at: datetime

    model_config = {"from_attributes": True}


class MessageHistoryResponse(BaseModel):
    """Paginated message history for a chat room."""
    messages: List[MessageResponse]
    connection_id: str
    has_more: bool
