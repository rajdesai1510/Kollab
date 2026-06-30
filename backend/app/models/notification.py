"""
Nexus — Notification Document Model
-------------------------------------------
The `notifications` collection stores in-app notifications for users.

Notifications are created by the notification service when key events happen:
- Brand sends a connection request to a creator
- Creator accepts/declines a connection
- New message received (from WebSocket or REST fallback)
- Creator expresses interest in a brand's campaign

These are displayed in the in-app notification bell. If email is enabled,
the notification service also dispatches an email via Resend.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from beanie import Document, Indexed
from pydantic import Field


class NotificationType(str, Enum):
    """
    Notification event types.
    The `data` field carries event-specific payload for each type.
    """
    # Connection events
    CONNECTION_REQUEST = "connection_request"    # data: {requester_name, requester_id}
    CONNECTION_ACCEPTED = "connection_accepted"  # data: {acceptor_name, connection_id}
    CONNECTION_DECLINED = "connection_declined"  # data: {decliner_name}

    # Messaging events
    NEW_MESSAGE = "new_message"                  # data: {sender_name, connection_id, preview}

    # Campaign events
    CAMPAIGN_INTEREST = "campaign_interest"      # data: {creator_name, creator_id, campaign_id}

    # System
    WELCOME = "welcome"                          # data: {role}
    INSTAGRAM_SYNCED = "instagram_synced"        # data: {followers, engagement_rate}


class Notification(Document):
    """
    Notification document. Stored in the `notifications` collection.

    Queried on every page load for the notification bell badge count.
    Marked as read when user opens the notification dropdown.
    """

    # ── Target User ────────────────────────────────────────────
    user_id: Indexed(str)              # The user who should see this notification  # type: ignore[valid-type]

    # ── Content ────────────────────────────────────────────────
    notification_type: NotificationType
    title: str                         # Short title: "New connection request"
    body: str                          # Message body: "Zomato wants to connect with you"
    data: Dict[str, Any] = Field(default_factory=dict)  # Event-specific payload

    # ── Links ──────────────────────────────────────────────────
    action_url: Optional[str] = None   # Frontend URL to navigate to on click

    # ── Status ─────────────────────────────────────────────────
    is_read: bool = False

    # ── Email ──────────────────────────────────────────────────
    email_sent: bool = False           # Track if we already dispatched the email

    # ── Timestamps ─────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None

    class Settings:
        name = "notifications"
        use_state_management = True
        indexes = [
            # Primary query: unread notifications for a user, newest first
            [("user_id", 1), ("is_read", 1), ("created_at", -1)],
            "user_id",
            "is_read",
        ]
