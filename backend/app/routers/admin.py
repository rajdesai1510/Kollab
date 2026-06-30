"""
Nexus — Admin Router (Class-based)
-----------------------------------------
User management, campaign moderation, and platform analytics.
All endpoints are admin-only — enforced via auth_middleware.require_role(UserRole.ADMIN).

Admin schemas (AdminUserResponse, PlatformAnalytics) are kept inline here
because they are admin-exclusive with no reuse elsewhere.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.middleware.auth_middleware import auth_middleware
from app.models.brand_profile import BrandProfile
from app.models.campaign import Campaign, CampaignStatus
from app.models.connection import Connection, ConnectionStatus
from app.models.creator_profile import CreatorProfile
from app.models.message import Message
from app.models.user import User, UserRole


# ─────────────────────────────────────────────────────────────
# Admin-Only Schemas
# (kept inline — admin-exclusive, no cross-module reuse)
# ─────────────────────────────────────────────────────────────

class AdminUserResponse(BaseModel):
    """Full user record for admin user management table."""

    id: str
    email: str
    name: str
    role: str
    is_active: bool
    is_verified: bool
    onboarding_complete: bool
    instagram_connected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PlatformAnalytics(BaseModel):
    """High-level platform statistics for the admin dashboard."""

    total_users: int
    total_creators: int
    total_brands: int
    total_connections: int
    accepted_connections: int
    total_campaigns: int
    open_campaigns: int
    total_messages: int


# ─────────────────────────────────────────────────────────────
# Admin Router (Class-based)
# ─────────────────────────────────────────────────────────────

class AdminRouter:
    """
    Class-based router for admin-only operations.

    All routes are protected by require_role(UserRole.ADMIN).
    No service layer — admin operations interact directly with Beanie
    models (queries are admin-specific, not reusable business logic).

    Usage:
        admin_router = AdminRouter()
        app.include_router(admin_router.router, prefix="/api/admin", tags=["Admin"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes on self.router."""
        # User management
        self.router.add_api_route(
            "/users",
            self.list_users,
            methods=["GET"],
            summary="List all users",
            response_model=List[AdminUserResponse],
        )
        self.router.add_api_route(
            "/users/{user_id}/suspend",
            self.toggle_user_suspension,
            methods=["PATCH"],
            summary="Suspend or unsuspend user",
        )
        self.router.add_api_route(
            "/users/{user_id}/verify",
            self.verify_user,
            methods=["PATCH"],
            summary="Verify a user account",
        )
        # Campaign moderation
        self.router.add_api_route(
            "/campaigns",
            self.admin_list_campaigns,
            methods=["GET"],
            summary="List all campaigns (admin)",
        )
        self.router.add_api_route(
            "/campaigns/{campaign_id}",
            self.remove_campaign,
            methods=["DELETE"],
            summary="Remove inappropriate campaign",
        )
        # Analytics
        self.router.add_api_route(
            "/analytics",
            self.platform_analytics,
            methods=["GET"],
            summary="Platform analytics",
            response_model=PlatformAnalytics,
        )

    # ─────────────────────────────────────────────────────────
    # User Management
    # ─────────────────────────────────────────────────────────

    async def list_users(
        self,
        role: Optional[str] = Query(None),
        is_active: Optional[bool] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=100),
        admin: User = Depends(auth_middleware.require_role(UserRole.ADMIN)),
    ) -> List[AdminUserResponse]:
        """List all users with optional role and active status filters."""
        conditions = {}
        if role:
            conditions["role"] = role
        if is_active is not None:
            conditions["is_active"] = is_active

        skip = (page - 1) * limit
        users = (
            await User.find(conditions)
            .sort("-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        return [
            AdminUserResponse(
                id=str(u.id),
                email=u.email,
                name=u.name,
                role=u.role.value,
                is_active=u.is_active,
                is_verified=u.is_verified,
                onboarding_complete=u.onboarding_complete,
                instagram_connected=bool(u.instagram_user_id),
                created_at=u.created_at,
            )
            for u in users
        ]

    async def toggle_user_suspension(
        self,
        user_id: str,
        admin: User = Depends(auth_middleware.require_role(UserRole.ADMIN)),
    ) -> dict:
        """Toggle a user's is_active status. Suspended users cannot log in."""
        user = await User.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        if user.role == UserRole.ADMIN:
            raise HTTPException(
                status_code=400, detail="Cannot suspend another admin."
            )

        user.is_active = not user.is_active
        await user.save()

        action = "suspended" if not user.is_active else "reactivated"
        return {"user_id": user_id, "is_active": user.is_active, "action": action}

    async def verify_user(
        self,
        user_id: str,
        admin: User = Depends(auth_middleware.require_role(UserRole.ADMIN)),
    ) -> dict:
        """Mark a creator or brand as verified (admin trust badge)."""
        user = await User.get(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        user.is_verified = True
        await user.save()
        return {"user_id": user_id, "is_verified": True}

    # ─────────────────────────────────────────────────────────
    # Campaign Moderation
    # ─────────────────────────────────────────────────────────

    async def admin_list_campaigns(
        self,
        status: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(50, ge=1, le=100),
        admin: User = Depends(auth_middleware.require_role(UserRole.ADMIN)),
    ) -> dict:
        """Admin: list all campaigns regardless of status."""
        conditions = {}
        if status:
            conditions["status"] = status

        skip = (page - 1) * limit
        campaigns = (
            await Campaign.find(conditions)
            .sort("-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )
        return {"campaigns": [c.model_dump() for c in campaigns], "page": page}

    async def remove_campaign(
        self,
        campaign_id: str,
        admin: User = Depends(auth_middleware.require_role(UserRole.ADMIN)),
    ) -> dict:
        """Admin: force-close an inappropriate campaign brief."""
        campaign = await Campaign.get(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        campaign.status = CampaignStatus.CLOSED
        await campaign.save()
        return {"message": "Campaign removed.", "campaign_id": campaign_id}

    # ─────────────────────────────────────────────────────────
    # Platform Analytics
    # ─────────────────────────────────────────────────────────

    async def platform_analytics(
        self,
        admin: User = Depends(auth_middleware.require_role(UserRole.ADMIN)),
    ) -> PlatformAnalytics:
        """Return high-level platform statistics for the admin dashboard."""
        total_users = await User.count()
        creator_count = await User.find(User.role == UserRole.CREATOR).count()
        brand_count = await User.find(User.role == UserRole.BRAND).count()
        total_connections = await Connection.count()
        accepted_connections = await Connection.find(
            Connection.status == ConnectionStatus.ACCEPTED
        ).count()
        total_campaigns = await Campaign.count()
        open_campaigns = await Campaign.find(
            Campaign.status == CampaignStatus.OPEN
        ).count()
        total_messages = await Message.count()

        return PlatformAnalytics(
            total_users=total_users,
            total_creators=creator_count,
            total_brands=brand_count,
            total_connections=total_connections,
            accepted_connections=accepted_connections,
            total_campaigns=total_campaigns,
            open_campaigns=open_campaigns,
            total_messages=total_messages,
        )


# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
admin_router = AdminRouter()
