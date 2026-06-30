"""
Nexus — Message Document Model
---------------------------------------
The `messages` collection stores individual chat messages for each connection.

Messages are scoped to a `connection_id` — the ID of an ACCEPTED connection
between a brand and creator. Only parties to that connection can send/read messages.

The WebSocket router handles real-time delivery. This collection is the
persistent store — messages fetched on reconnect or page load from here.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field


class MessageType(str, Enum):
    """
    Type of message content.
    Kept simple for MVP — text only. Extend for attachments in V2.
    """
    TEXT = "text"
    SYSTEM = "system"   # System messages: "Connection accepted", "Chat started"


class Message(Document):
    """
    Message document. Stored in the `messages` collection.

    Each document represents one message in a connection's chat thread.
    Indexed on connection_id for efficient paginated history queries.
    """

    # ── Context ────────────────────────────────────────────────
    connection_id: Indexed(str)     # Connection._id — scopes the chat room  # type: ignore[valid-type]
    sender_id: str                  # User._id of the message sender

    # ── Content ────────────────────────────────────────────────
    message_type: MessageType = MessageType.TEXT
    content: str                    # The message text

    # ── Read Receipt ───────────────────────────────────────────
    is_read: bool = False
    read_at: Optional[datetime] = None

    # ── Timestamps ─────────────────────────────────────────────
    sent_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "messages"
        use_state_management = True
        indexes = [
            # Primary query: get all messages for a connection, sorted by time
            [("connection_id", 1), ("sent_at", 1)],
            "sender_id",
            "is_read",
        ]
