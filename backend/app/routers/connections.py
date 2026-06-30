"""
Nexus — Connections Router (Class-based)
-----------------------------------------------
Brand-creator connection lifecycle: request, accept, decline, list.

Dependencies flow:
  ConnectionRouter -> ConnectionService -> DB (Beanie), NotificationService
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.auth_middleware import auth_middleware
from app.models.brand_profile import BrandProfile
from app.models.creator_profile import CreatorProfile
from app.models.user import User, UserRole
from app.schemas.shared import (
    ConnectionRequestBody,
    ConnectionResponse,
    ConnectionsListResponse,
)
from app.services.connection_service import (
    ConnectionNotFoundError,
    ConnectionService,
    DuplicateConnectionError,
    UnauthorizedActionError,
)


class ConnectionRouter:
    """
    Class-based router for the brand-creator connection lifecycle.

    State machine enforced by ConnectionService:
        PENDING -> ACCEPTED (chat unlocked)
        PENDING -> DECLINED

    Usage:
        connection_router = ConnectionRouter()
        app.include_router(connection_router.router, prefix="/api/connections", tags=["Connections"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self.connection_service = ConnectionService()
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes on self.router."""
        self.router.add_api_route(
            "/request",
            self.send_connection_request,
            methods=["POST"],
            summary="Send connection request",
            response_model=ConnectionResponse,
            status_code=status.HTTP_201_CREATED,
        )
        self.router.add_api_route(
            "/{connection_id}/accept",
            self.accept_connection,
            methods=["POST"],
            summary="Accept connection request",
            response_model=ConnectionResponse,
        )
        self.router.add_api_route(
            "/{connection_id}/decline",
            self.decline_connection,
            methods=["POST"],
            summary="Decline connection request",
            response_model=ConnectionResponse,
        )
        self.router.add_api_route(
            "/",
            self.list_connections,
            methods=["GET"],
            summary="List my connections",
            response_model=ConnectionsListResponse,
        )

    # ─────────────────────────────────────────────────────────
    # Send Request (Brand Only)
    # ─────────────────────────────────────────────────────────

    async def send_connection_request(
        self,
        body: ConnectionRequestBody,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> ConnectionResponse:
        """
        Brand sends a connection request to a creator.
        Only BRAND role users can initiate requests.
        """
        if current_user.role != UserRole.BRAND:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only brands can send connection requests.",
            )

        brand_profile = await BrandProfile.find_one(
            BrandProfile.user_id == str(current_user.id)
        )
        if not brand_profile:
            raise HTTPException(
                status_code=404,
                detail="Brand profile not found. Complete onboarding first.",
            )

        creator_profile = await CreatorProfile.get(body.recipient_profile_id)
        if not creator_profile:
            raise HTTPException(status_code=404, detail="Creator not found.")

        try:
            connection = await self.connection_service.send_request(
                brand_user_id=str(current_user.id),
                brand_profile_id=str(brand_profile.id),
                creator_user_id=creator_profile.user_id,
                creator_profile_id=str(creator_profile.id),
                campaign_id=body.campaign_id,
            )
        except DuplicateConnectionError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

        return ConnectionResponse.model_validate(connection.model_dump())

    # ─────────────────────────────────────────────────────────
    # Accept Request (Creator Only)
    # ─────────────────────────────────────────────────────────

    async def accept_connection(
        self,
        connection_id: str,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> ConnectionResponse:
        """Creator accepts a pending connection request. Unlocks in-platform chat."""
        try:
            connection = await self.connection_service.accept_request(
                connection_id=connection_id,
                accepting_user_id=str(current_user.id),
            )
        except ConnectionNotFoundError:
            raise HTTPException(status_code=404, detail="Connection not found.")
        except UnauthorizedActionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        return ConnectionResponse.model_validate(connection.model_dump())

    # ─────────────────────────────────────────────────────────
    # Decline Request (Creator Only)
    # ─────────────────────────────────────────────────────────

    async def decline_connection(
        self,
        connection_id: str,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> ConnectionResponse:
        """Creator declines a pending connection request."""
        try:
            connection = await self.connection_service.decline_request(
                connection_id=connection_id,
                declining_user_id=str(current_user.id),
            )
        except ConnectionNotFoundError:
            raise HTTPException(status_code=404, detail="Connection not found.")
        except UnauthorizedActionError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

        return ConnectionResponse.model_validate(connection.model_dump())

    # ─────────────────────────────────────────────────────────
    # List Connections
    # ─────────────────────────────────────────────────────────

    async def list_connections(
        self,
        current_user: User = Depends(auth_middleware.get_current_user),
    ) -> ConnectionsListResponse:
        """Return all accepted connections and pending requests for the current user."""
        accepted, pending = await self.connection_service.get_my_connections(
            str(current_user.id)
        )
        return ConnectionsListResponse(
            accepted=[ConnectionResponse.model_validate(c.model_dump()) for c in accepted],
            pending=[ConnectionResponse.model_validate(c.model_dump()) for c in pending],
        )


# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
connection_router = ConnectionRouter()
