"""
Nexus — Notification Schemas
-------------------------------------
Pydantic response models for notification endpoints.
Moved here from routers/notifications.py for proper separation of concerns.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    """Single notification item returned to the client."""

    id: str
    notification_type: str
    title: str
    body: str
    action_url: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""

    notifications: List[NotificationResponse]
    unread_count: int
