"""
Nexus — Notification Service (Class-based)
--------------------------------------------------
Creates in-app notifications and optionally sends transactional emails.

Notification events currently handled:
  - connection_request  → creator receives alert
  - connection_accepted → brand receives alert
  - new_message         → other party in chat receives alert
  - campaign_interest   → brand receives alert when creator expresses interest

Email dispatch is via Resend API (only when RESEND_API_KEY is configured).
In development, emails are logged to console instead.

Usage:
    from app.services.notification_service import NotificationService
    svc = NotificationService()
    await svc.notify_connection_request(
        recipient_user_id="...",
        requester_user_id="...",
        connection_id="...",
    )
"""

from datetime import datetime
from typing import Optional

from app.config import settings
from app.core.logger import logger
from app.models.notification import Notification, NotificationType
from app.models.user import User


class NotificationService:
    """
    Central service for all in-app and email notifications.

    Design:
      - Always creates a Notification document (in-app bell)
      - If email is enabled and user has opted in → sends email via Resend
      - Email sending is fire-and-forget: failures are logged, never raised

    All methods are named `notify_<event>` for clarity.
    """

    # ─────────────────────────────────────────────────────────
    # Connection Events
    # ─────────────────────────────────────────────────────────

    async def notify_connection_request(
        self,
        recipient_user_id: str,
        requester_user_id: str,
        connection_id: str,
    ) -> None:
        """
        Notify a creator that a brand sent them a connection request.

        Args:
            recipient_user_id: Creator's User._id
            requester_user_id: Brand's User._id
            connection_id: The new Connection._id
        """
        requester = await User.get(requester_user_id)
        requester_name = requester.name if requester else "A brand"

        await self._create_and_send(
            user_id=recipient_user_id,
            notification_type=NotificationType.CONNECTION_REQUEST,
            title="New connection request",
            body=f"{requester_name} wants to connect with you!",
            data={
                "requester_id": requester_user_id,
                "requester_name": requester_name,
                "connection_id": connection_id,
            },
            action_url=f"/connections",
        )

    async def notify_connection_accepted(
        self,
        recipient_user_id: str,
        acceptor_user_id: str,
        connection_id: str,
    ) -> None:
        """
        Notify a brand that a creator accepted their connection request.
        Chat is now unlocked.

        Args:
            recipient_user_id: Brand's User._id
            acceptor_user_id: Creator's User._id
            connection_id: The accepted Connection._id
        """
        acceptor = await User.get(acceptor_user_id)
        acceptor_name = acceptor.name if acceptor else "A creator"

        await self._create_and_send(
            user_id=recipient_user_id,
            notification_type=NotificationType.CONNECTION_ACCEPTED,
            title="Connection accepted! 🎉",
            body=f"{acceptor_name} accepted your connection request. You can now chat!",
            data={
                "acceptor_id": acceptor_user_id,
                "acceptor_name": acceptor_name,
                "connection_id": connection_id,
            },
            action_url=f"/messages/{connection_id}",
        )

    # ─────────────────────────────────────────────────────────
    # Message Events
    # ─────────────────────────────────────────────────────────

    async def notify_new_message(
        self,
        recipient_user_id: str,
        sender_user_id: str,
        connection_id: str,
        message_preview: str,
    ) -> None:
        """
        Notify a user that they have a new unread message.

        The preview is truncated to 60 chars for the notification body.
        Full message is only in the chat room itself.

        Args:
            recipient_user_id: User._id of the message recipient
            sender_user_id: User._id of the message sender
            connection_id: Chat room (Connection._id)
            message_preview: First 60 chars of the message content
        """
        sender = await User.get(sender_user_id)
        sender_name = sender.name if sender else "Someone"
        preview = message_preview[:60] + ("..." if len(message_preview) > 60 else "")

        await self._create_and_send(
            user_id=recipient_user_id,
            notification_type=NotificationType.NEW_MESSAGE,
            title=f"New message from {sender_name}",
            body=preview,
            data={
                "sender_id": sender_user_id,
                "sender_name": sender_name,
                "connection_id": connection_id,
                "preview": preview,
            },
            action_url=f"/messages/{connection_id}",
        )

    # ─────────────────────────────────────────────────────────
    # Campaign Events
    # ─────────────────────────────────────────────────────────

    async def notify_campaign_interest(
        self,
        brand_user_id: str,
        creator_user_id: str,
        creator_profile_id: str,
        campaign_id: str,
        campaign_title: str,
    ) -> None:
        """
        Notify a brand that a creator expressed interest in their campaign.

        Args:
            brand_user_id: Brand's User._id (notification recipient)
            creator_user_id: Creator's User._id
            creator_profile_id: Creator's profile ID (for the action URL)
            campaign_id: Campaign._id
            campaign_title: Campaign title for the notification body
        """
        creator = await User.get(creator_user_id)
        creator_name = creator.name if creator else "A creator"

        await self._create_and_send(
            user_id=brand_user_id,
            notification_type=NotificationType.CAMPAIGN_INTEREST,
            title="New campaign interest!",
            body=f'{creator_name} is interested in your campaign "{campaign_title}".',
            data={
                "creator_id": creator_user_id,
                "creator_name": creator_name,
                "creator_profile_id": creator_profile_id,
                "campaign_id": campaign_id,
            },
            action_url=f"/campaigns/{campaign_id}",
        )

    # ─────────────────────────────────────────────────────────
    # Notification Retrieval
    # ─────────────────────────────────────────────────────────

    async def get_unread(self, user_id: str, limit: int = 20) -> list[Notification]:
        """
        Fetch the most recent unread notifications for a user.

        Args:
            user_id: User._id
            limit: Max notifications to return (default 20)

        Returns:
            List of unread Notification documents, newest first
        """
        return (
            await Notification.find(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
            )
            .sort("-created_at")
            .limit(limit)
            .to_list()
        )

    async def mark_all_read(self, user_id: str) -> int:
        """
        Mark all unread notifications as read for a user.

        Returns:
            Number of notifications marked read
        """
        result = await Notification.find(
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        ).update(
            {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
        )
        count = result.modified_count if hasattr(result, "modified_count") else 0
        logger.debug(f"Marked {count} notifications read for user_id={user_id}")
        return count

    # ─────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────

    async def _create_and_send(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: dict,
        action_url: Optional[str] = None,
    ) -> Notification:
        """
        Create a Notification document and optionally send email.
        Internal method — always call the specific `notify_*` methods above.
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
            action_url=action_url,
        )
        await notification.insert()

        # Attempt email if enabled — non-blocking failure
        if settings.email_enabled:
            await self._send_email_safe(user_id, title, body, action_url)

        return notification

    async def _send_email_safe(
        self,
        user_id: str,
        subject: str,
        body: str,
        action_url: Optional[str],
    ) -> None:
        """
        Send a transactional email via SMTP.
        Failures are logged but never raised — email is supplementary.
        """
        try:
            user = await User.get(user_id)
            if not user or not user.notifications_email:
                return

            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            cta_html = ""
            if action_url:
                full_url = f"{settings.FRONTEND_URL}{action_url}"
                cta_html = (
                    f'<p><a href="{full_url}" '
                    f'style="background:#6366f1;color:white;padding:10px 20px;'
                    f'border-radius:6px;text-decoration:none;">View on Nexus</a></p>'
                )

            html_content = (
                f"<p>Hi {user.name},</p>"
                f"<p>{body}</p>"
                f"{cta_html}"
                f"<p><br>— The {settings.APP_NAME} Team</p>"
            )

            msg = MIMEMultipart()
            msg['From'] = f"{settings.FROM_NAME} <{settings.FROM_EMAIL}>"
            msg['To'] = user.email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

        except Exception as e:
            logger.error(f"Failed to send email to user {user_id}: {str(e)}")
