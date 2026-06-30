"""
Nexus — Messages Router (Class-based)
--------------------------------------------
REST message history + WebSocket real-time chat per connection room.

Classes in this module:
  ConnectionManager   — manages active WebSocket rooms (in-memory)
  MessageRouter       — FastAPI router class for REST + WebSocket endpoints

WebSocket auth: JWT passed as ?token=... query parameter.
WebSocket scale note: ConnectionManager is single-instance in-memory.
  Replace with Redis Pub/Sub for multi-instance horizontal scaling.
"""

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.core.jwt_manager import TokenExpiredError, TokenInvalidError, jwt_manager
from app.core.logger import logger
from app.middleware.auth_middleware import auth_middleware
from app.models.message import Message, MessageType
from app.models.user import User
from app.schemas.shared import MessageHistoryResponse, MessageResponse, MessageSendRequest
from app.services.connection_service import (
    ConnectionNotFoundError,
    ConnectionService,
    UnauthorizedActionError,
)
from app.services.notification_service import NotificationService


# ─────────────────────────────────────────────────────────────
# WebSocket Connection Manager (Class-based)
# ─────────────────────────────────────────────────────────────

class ConnectionManager:
    """
    Manages active WebSocket connections across all chat rooms.

    Structure:
        active_connections = {
            connection_id: {user_id: WebSocket}
        }

    In-memory only — fine for MVP with a single backend instance.
    For multi-instance scaling: replace with Redis pub/sub.

    All methods on this class are the sole interface for WebSocket
    lifecycle management — no direct dict manipulation outside this class.
    """

    def __init__(self) -> None:
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(
        self, connection_id: str, user_id: str, websocket: WebSocket
    ) -> None:
        """Accept the WebSocket and register the client in the room."""
        await websocket.accept()
        if connection_id not in self.active_connections:
            self.active_connections[connection_id] = {}
        self.active_connections[connection_id][user_id] = websocket
        logger.debug(f"WS connected — room={connection_id}, user={user_id}")

    def disconnect(self, connection_id: str, user_id: str) -> None:
        """Remove a client when they disconnect. Cleans up empty rooms."""
        if connection_id in self.active_connections:
            self.active_connections[connection_id].pop(user_id, None)
            if not self.active_connections[connection_id]:
                del self.active_connections[connection_id]
        logger.debug(f"WS disconnected — room={connection_id}, user={user_id}")

    def is_user_in_room(self, connection_id: str, user_id: str) -> bool:
        """Check if a user is currently connected to a specific room."""
        return user_id in self.active_connections.get(connection_id, {})

    async def send_to_room(self, connection_id: str, message: dict) -> None:
        """Broadcast a JSON message to all connected clients in a room."""
        if connection_id not in self.active_connections:
            return

        disconnected_users = []
        for user_id, websocket in self.active_connections[connection_id].items():
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected_users.append(user_id)

        # Clean up broken connections
        for user_id in disconnected_users:
            self.disconnect(connection_id, user_id)


# ─────────────────────────────────────────────────────────────
# Module-level singleton WebSocket manager
# ─────────────────────────────────────────────────────────────
ws_manager = ConnectionManager()


# ─────────────────────────────────────────────────────────────
# Messages Router (Class-based)
# ─────────────────────────────────────────────────────────────

class MessageRouter:
    """
    Class-based router for message history (REST) and real-time chat (WebSocket).

    Encapsulates:
        - ConnectionService instance (for access validation)
        - NotificationService instance (for message notifications)
        - ConnectionManager reference (shared module-level ws_manager)
        - All route handler methods
        - Route registration logic

    Usage:
        message_router = MessageRouter()
        app.include_router(message_router.router, prefix="/api/messages", tags=["Messages"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self.connection_service = ConnectionService()
        self.notification_service = NotificationService()
        self.ws_manager = ws_manager  # Reference to module-level singleton
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all REST routes. WebSocket is added separately."""
        self.router.add_api_route(
            "/{connection_id}",
            self.get_message_history,
            methods=["GET"],
            summary="Get message history",
            response_model=MessageHistoryResponse,
        )
        self.router.add_api_route(
            "/{connection_id}",
            self.send_message_rest,
            methods=["POST"],
            summary="Send message (REST fallback)",
            response_model=MessageResponse,
            status_code=201,
        )
        # WebSocket routes must use router.websocket(), not add_api_route
        self.router.add_websocket_route(
            "/ws/{connection_id}",
            self.websocket_chat,
        )

    # ─────────────────────────────────────────────────────────
    # REST — Message History
    # ─────────────────────────────────────────────────────────

    async def get_message_history(
        self,
        connection_id: str,
        page: int = Query(1, ge=1),
        limit: int = Query(30, ge=1, le=100),
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> MessageHistoryResponse:
        """Fetch paginated message history for a chat room."""
        try:
            await self.connection_service.get_connection_for_chat(
                connection_id=connection_id,
                user_id=str(current_user.id),
            )
        except (ConnectionNotFoundError, UnauthorizedActionError) as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        skip = (page - 1) * limit
        messages = (
            await Message.find(Message.connection_id == connection_id)
            .sort("-sent_at")
            .skip(skip)
            .limit(limit + 1)
            .to_list()
        )
        has_more = len(messages) > limit
        messages = messages[:limit]
        messages.reverse()  # Return in chronological order

        return MessageHistoryResponse(
            messages=[MessageResponse.model_validate(m.model_dump()) for m in messages],
            connection_id=connection_id,
            has_more=has_more,
        )

    # ─────────────────────────────────────────────────────────
    # REST — Send Message (Fallback)
    # ─────────────────────────────────────────────────────────

    async def send_message_rest(
        self,
        connection_id: str,
        body: MessageSendRequest,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> MessageResponse:
        """
        REST fallback for sending messages (when WebSocket is unavailable).
        Persists message to DB. Does NOT broadcast via WebSocket.
        """
        try:
            connection = await self.connection_service.get_connection_for_chat(
                connection_id=connection_id,
                user_id=str(current_user.id),
            )
        except (ConnectionNotFoundError, UnauthorizedActionError) as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        message = Message(
            connection_id=connection_id,
            sender_id=str(current_user.id),
            content=body.content,
            message_type=MessageType.TEXT,
        )
        await message.insert()

        # Notify recipient
        recipient_id = (
            connection.recipient_id
            if connection.requester_id == str(current_user.id)
            else connection.requester_id
        )
        await self.notification_service.notify_new_message(
            recipient_user_id=recipient_id,
            sender_user_id=str(current_user.id),
            connection_id=connection_id,
            message_preview=body.content,
        )

        return MessageResponse.model_validate(message.model_dump())

    # ─────────────────────────────────────────────────────────
    # WebSocket — Real-time Chat
    # ─────────────────────────────────────────────────────────

    async def websocket_chat(
        self,
        websocket: WebSocket,
        connection_id: str,
        token: str = Query(..., description="JWT access token"),
    ) -> None:
        """
        Real-time chat WebSocket endpoint.

        Authentication: JWT token passed as query parameter (?token=...).
        Authorization: User must be a party to an ACCEPTED connection.

        Message format (JSON):
            Client -> Server: {"content": "Hello!"}
            Server -> Client: {
                "id": "...", "sender_id": "...", "content": "Hello!",
                "sent_at": "...", "connection_id": "..."
            }
        """
        # Step 1: Authenticate via JWT
        try:
            payload = jwt_manager.verify_token(token, expected_type="access")
            current_user = await User.get(payload.sub)
            if not current_user or not current_user.is_active:
                await websocket.close(code=4001, reason="Unauthorized")
                return
        except (TokenExpiredError, TokenInvalidError):
            await websocket.close(code=4001, reason="Invalid or expired token")
            return

        # Step 2: Verify the user is a party to an ACCEPTED connection
        try:
            connection = await self.connection_service.get_connection_for_chat(
                connection_id=connection_id,
                user_id=str(current_user.id),
            )
        except (ConnectionNotFoundError, UnauthorizedActionError) as exc:
            await websocket.close(code=4003, reason=str(exc))
            return

        user_id = str(current_user.id)
        await self.ws_manager.connect(connection_id, user_id, websocket)

        # Determine recipient for smart notification logic
        recipient_id = (
            connection.recipient_id if connection.requester_id == user_id
            else connection.requester_id
        )

        try:
            while True:
                data = await websocket.receive_json()
                content = data.get("content", "").strip()
                if not content or len(content) > 5000:
                    continue

                # Persist message to DB
                message = Message(
                    connection_id=connection_id,
                    sender_id=user_id,
                    content=content,
                    message_type=MessageType.TEXT,
                )
                await message.insert()

                # Broadcast to all room members
                payload_out = {
                    "id": str(message.id),
                    "connection_id": connection_id,
                    "sender_id": user_id,
                    "content": content,
                    "sent_at": message.sent_at.isoformat(),
                    "is_read": False,
                }
                await self.ws_manager.send_to_room(connection_id, payload_out)

                # Notify recipient ONLY if they are NOT in the room
                if not self.ws_manager.is_user_in_room(connection_id, recipient_id):
                    await self.notification_service.notify_new_message(
                        recipient_user_id=recipient_id,
                        sender_user_id=user_id,
                        connection_id=connection_id,
                        message_preview=content,
                    )

        except WebSocketDisconnect:
            self.ws_manager.disconnect(connection_id, user_id)
            logger.debug(f"WS cleanly disconnected — room={connection_id}, user={user_id}")


# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
message_router = MessageRouter()
