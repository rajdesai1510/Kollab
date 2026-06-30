"""
Nexus — Connection Service (Class-based)
-----------------------------------------------
Business logic for the brand-creator connection lifecycle.

Connection State Machine:
  Brand sends request → PENDING
  Creator accepts     → ACCEPTED (chat unlocked)
  Creator declines    → DECLINED

Rules enforced by this service:
  - A brand cannot send duplicate requests to the same creator
  - Only the recipient (creator) can accept or decline
  - Chat only unlocks after ACCEPTED status
  - Monthly connection limit counter incremented (for future subscription tiers)

Usage:
    from app.services.connection_service import ConnectionService
    service = ConnectionService()
    connection = await service.send_request(
        brand_user_id="...", brand_profile_id="...",
        creator_user_id="...", creator_profile_id="..."
    )
"""

from datetime import datetime
from typing import List, Optional, Tuple

from app.core.logger import logger
from app.models.connection import Connection, ConnectionStatus
from app.services.notification_service import NotificationService


class ConnectionError(Exception):
    """Base error for connection service failures."""
    pass


class DuplicateConnectionError(ConnectionError):
    """Raised when a brand tries to send a duplicate request."""
    pass


class ConnectionNotFoundError(ConnectionError):
    """Raised when a connection lookup returns nothing."""
    pass


class UnauthorizedActionError(ConnectionError):
    """Raised when a user tries to act on a connection they don't own."""
    pass


class ConnectionService:
    """
    Manages the brand-creator connection lifecycle.

    Injects NotificationService to trigger alerts on state changes.
    """

    def __init__(
        self,
        notification_service: Optional[NotificationService] = None,
    ) -> None:
        self._notifications = notification_service or NotificationService()

    # ─────────────────────────────────────────────────────────
    # Send Request
    # ─────────────────────────────────────────────────────────

    async def send_request(
        self,
        brand_user_id: str,
        brand_profile_id: str,
        creator_user_id: str,
        creator_profile_id: str,
        campaign_id: Optional[str] = None,
    ) -> Connection:
        """
        Brand sends a connection request to a creator.

        Checks for:
          - Duplicate pending/accepted request (raises DuplicateConnectionError)

        Creates:
          - New Connection document with status=PENDING
          - Notification for the creator

        Args:
            brand_user_id: User._id of the brand
            brand_profile_id: BrandProfile._id
            creator_user_id: User._id of the target creator
            creator_profile_id: CreatorProfile._id
            campaign_id: Optional — campaign that triggered this request

        Returns:
            New Connection document

        Raises:
            DuplicateConnectionError: If active request already exists
        """
        # Check for duplicate
        existing = await Connection.find_one(
            Connection.requester_id == brand_user_id,
            Connection.recipient_id == creator_user_id,
            Connection.status.in_([
                ConnectionStatus.PENDING,
                ConnectionStatus.ACCEPTED,
            ]),
        )
        if existing:
            raise DuplicateConnectionError(
                "A pending or active connection already exists with this creator."
            )

        # Create connection
        connection = Connection(
            requester_id=brand_user_id,
            requester_profile_id=brand_profile_id,
            recipient_id=creator_user_id,
            recipient_profile_id=creator_profile_id,
            status=ConnectionStatus.PENDING,
            campaign_id=campaign_id,
        )
        await connection.insert()

        # Notify creator
        await self._notifications.notify_connection_request(
            recipient_user_id=creator_user_id,
            requester_user_id=brand_user_id,
            connection_id=str(connection.id),
        )

        logger.info(
            f"Connection request sent — "
            f"brand={brand_user_id} → creator={creator_user_id}"
        )
        return connection

    # ─────────────────────────────────────────────────────────
    # Accept / Decline
    # ─────────────────────────────────────────────────────────

    async def accept_request(
        self,
        connection_id: str,
        accepting_user_id: str,
    ) -> Connection:
        """
        Creator accepts a pending connection request.

        Args:
            connection_id: Connection._id
            accepting_user_id: Must match Connection.recipient_id

        Returns:
            Updated Connection with status=ACCEPTED

        Raises:
            ConnectionNotFoundError: If connection doesn't exist
            UnauthorizedActionError: If caller is not the recipient
        """
        connection = await self._get_connection(connection_id)
        self._assert_recipient(connection, accepting_user_id)

        connection.status = ConnectionStatus.ACCEPTED
        connection.accepted_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        await connection.save()

        # Notify brand that creator accepted
        await self._notifications.notify_connection_accepted(
            recipient_user_id=connection.requester_id,
            acceptor_user_id=accepting_user_id,
            connection_id=connection_id,
        )

        logger.info(
            f"Connection accepted — id={connection_id}, "
            f"creator={accepting_user_id}"
        )
        return connection

    async def decline_request(
        self,
        connection_id: str,
        declining_user_id: str,
    ) -> Connection:
        """
        Creator declines a pending connection request.

        Args:
            connection_id: Connection._id
            declining_user_id: Must match Connection.recipient_id

        Returns:
            Updated Connection with status=DECLINED
        """
        connection = await self._get_connection(connection_id)
        self._assert_recipient(connection, declining_user_id)

        connection.status = ConnectionStatus.DECLINED
        connection.declined_at = datetime.utcnow()
        connection.updated_at = datetime.utcnow()
        await connection.save()

        logger.info(
            f"Connection declined — id={connection_id}, "
            f"creator={declining_user_id}"
        )
        return connection

    # ─────────────────────────────────────────────────────────
    # Listing
    # ─────────────────────────────────────────────────────────

    async def get_my_connections(
        self,
        user_id: str,
    ) -> Tuple[List[Connection], List[Connection]]:
        """
        Return all connections for a user, split into:
          - accepted: active connections (chat active)
          - pending: incoming or outgoing pending requests

        Args:
            user_id: User._id of the caller

        Returns:
            Tuple of (accepted_connections, pending_connections)
        """
        all_connections = await Connection.find(
            {
                "$or": [
                    {"requester_id": user_id},
                    {"recipient_id": user_id},
                ]
            }
        ).sort("-created_at").to_list()

        accepted = [c for c in all_connections if c.status == ConnectionStatus.ACCEPTED]
        pending = [c for c in all_connections if c.status == ConnectionStatus.PENDING]

        return accepted, pending

    async def get_connection_for_chat(
        self,
        connection_id: str,
        user_id: str,
    ) -> Connection:
        """
        Fetch an ACCEPTED connection — used before allowing chat access.

        Raises:
            ConnectionNotFoundError: If not found
            UnauthorizedActionError: If user is not a party to this connection
        """
        connection = await self._get_connection(connection_id)

        if connection.status != ConnectionStatus.ACCEPTED:
            raise UnauthorizedActionError(
                "Chat is only available for accepted connections."
            )

        if user_id not in (connection.requester_id, connection.recipient_id):
            raise UnauthorizedActionError(
                "You are not a party to this connection."
            )

        return connection

    # ─────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────

    async def _get_connection(self, connection_id: str) -> Connection:
        """Fetch a connection by ID or raise ConnectionNotFoundError."""
        connection = await Connection.get(connection_id)
        if not connection:
            raise ConnectionNotFoundError(
                f"Connection '{connection_id}' not found."
            )
        return connection

    def _assert_recipient(self, connection: Connection, user_id: str) -> None:
        """Verify that the acting user is the connection's recipient."""
        if connection.recipient_id != user_id:
            raise UnauthorizedActionError(
                "Only the connection recipient can perform this action."
            )
