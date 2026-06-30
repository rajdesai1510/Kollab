"""
Nexus — Notifications Router (Class-based)
-------------------------------------------------
In-app notification retrieval and read management.

Dependencies flow:
  NotificationRouter -> NotificationService -> DB (Beanie)
  Schemas imported from schemas/notification.py
"""

from typing import List

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import auth_middleware
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService


class NotificationRouter:
    """
    Class-based router for notification endpoints.

    Encapsulates:
        - NotificationService instance
        - All route handler methods
        - Route registration logic

    Usage:
        notification_router = NotificationRouter()
        app.include_router(notification_router.router, prefix="/api/notifications", tags=["Notifications"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self.notification_service = NotificationService()
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes on self.router."""
        self.router.add_api_route(
            "/",
            self.get_notifications,
            methods=["GET"],
            summary="Get unread notifications",
            response_model=List[NotificationResponse],
        )
        self.router.add_api_route(
            "/read",
            self.mark_notifications_read,
            methods=["POST"],
            summary="Mark all notifications as read",
        )

    # ─────────────────────────────────────────────────────────
    # Get Unread Notifications
    # ─────────────────────────────────────────────────────────

    async def get_notifications(
        self,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> List[NotificationResponse]:
        """Fetch the 20 most recent unread notifications for the current user."""
        notifications = await self.notification_service.get_unread(
            str(current_user.id)
        )
        return [
            NotificationResponse.model_validate(n.model_dump())
            for n in notifications
        ]

    # ─────────────────────────────────────────────────────────
    # Mark All as Read
    # ─────────────────────────────────────────────────────────

    async def mark_notifications_read(
        self,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> dict:
        """Mark all unread notifications as read for the current user."""
        count = await self.notification_service.mark_all_read(str(current_user.id))
        return {"marked_read": count}


# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
notification_router = NotificationRouter()
