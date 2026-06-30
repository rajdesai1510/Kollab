"""
Nexus — Connection Document Model
-----------------------------------------
The `connections` collection tracks the relationship between a brand and a creator.

Flow:
  Brand → sends request → status: PENDING
  Creator → accepts     → status: ACCEPTED → in-platform chat unlocks
  Creator → declines    → status: DECLINED → brand may send another request later

Once ACCEPTED, a connection is the "room" that scopes all messages
between this brand-creator pair.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document
from pydantic import Field


class ConnectionStatus(str, Enum):
    """
    State machine for a connection between a brand and creator.

    PENDING  → request sent, waiting for creator to respond
    ACCEPTED → both parties connected, chat unlocked
    DECLINED → creator declined, brand is notified
    BLOCKED  → admin action or abuse report (future)
    """
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    BLOCKED = "blocked"


class Connection(Document):
    """
    Connection document. Stored in the `connections` collection.

    One connection document per brand-creator pair.
    When status = ACCEPTED, this document's `_id` becomes the
    `connection_id` that scopes the Messages collection.
    """

    # ── Requester (always the Brand in MVP) ───────────────────
    requester_id: str           # User._id of the brand who sent the request
    requester_profile_id: str   # BrandProfile._id

    # ── Recipient (always the Creator in MVP) ─────────────────
    recipient_id: str           # User._id of the creator receiving the request
    recipient_profile_id: str   # CreatorProfile._id

    # ── Status ─────────────────────────────────────────────────
    status: ConnectionStatus = ConnectionStatus.PENDING  # indexed via Settings.indexes

    # ── Optional: which campaign triggered this request ────────
    # Set when the brand sends a request directly from a campaign's
    # "interested creators" list. Useful for analytics.
    campaign_id: Optional[str] = None

    # ── Timestamps ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    accepted_at: Optional[datetime] = None
    declined_at: Optional[datetime] = None

    class Settings:
        name = "connections"
        use_state_management = True
        indexes = [
            "requester_id",
            "recipient_id",
            "status",
            # Compound index: check if connection already exists between two users
            [("requester_id", 1), ("recipient_id", 1)],
            "campaign_id",
            "created_at",
        ]
