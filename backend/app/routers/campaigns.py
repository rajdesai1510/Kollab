"""
Nexus — Campaigns Router (Class-based)
---------------------------------------------
Campaign brief CRUD and creator interest flow.

Dependencies flow:
  CampaignRouter -> Campaign (Beanie), BrandProfile, CreatorProfile, NotificationService
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.auth_middleware import auth_middleware
from app.models.brand_profile import BrandProfile
from app.models.campaign import Campaign, CampaignStatus
from app.models.creator_profile import CreatorProfile
from app.models.user import User, UserRole
from app.schemas.shared import (
    CampaignCardResponse,
    CampaignCreateRequest,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdateRequest,
)
from app.services.notification_service import NotificationService


class CampaignRouter:
    """
    Class-based router for campaign brief endpoints.

    Encapsulates:
        - NotificationService instance (for campaign interest notifications)
        - All route handler methods
        - Route registration logic

    Usage:
        campaign_router = CampaignRouter()
        app.include_router(campaign_router.router, prefix="/api/campaigns", tags=["Campaigns"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self.notification_service = NotificationService()
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes on self.router."""
        self.router.add_api_route(
            "/",
            self.list_campaigns,
            methods=["GET"],
            summary="List open campaigns",
            response_model=CampaignListResponse,
        )
        self.router.add_api_route(
            "/",
            self.create_campaign,
            methods=["POST"],
            summary="Create campaign brief",
            response_model=CampaignResponse,
            status_code=status.HTTP_201_CREATED,
        )
        self.router.add_api_route(
            "/{campaign_id}",
            self.get_campaign,
            methods=["GET"],
            summary="Get campaign detail",
            response_model=CampaignResponse,
        )
        self.router.add_api_route(
            "/{campaign_id}",
            self.update_campaign,
            methods=["PUT"],
            summary="Update campaign brief",
            response_model=CampaignResponse,
        )
        self.router.add_api_route(
            "/{campaign_id}",
            self.close_campaign,
            methods=["DELETE"],
            summary="Close campaign",
        )
        self.router.add_api_route(
            "/{campaign_id}/interest",
            self.express_interest,
            methods=["POST"],
            summary="Express interest in campaign",
        )
        self.router.add_api_route(
            "/{campaign_id}/interested",
            self.get_interested_creators,
            methods=["GET"],
            summary="Get interested creators",
        )

    # ─────────────────────────────────────────────────────────
    # List Campaigns (Public / Optional Auth)
    # ─────────────────────────────────────────────────────────

    async def list_campaigns(
        self,
        city: Optional[str] = Query(None),
        niche: Optional[str] = Query(None),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=50),
        viewer: Optional[User] = Depends(auth_middleware.get_optional_user),
    ) -> CampaignListResponse:
        """Browse the campaign board. Filter by city and niche."""
        query_conditions = [Campaign.status == CampaignStatus.OPEN]

        if city:
            query_conditions.append(
                {"target_city": {"$regex": f"^{city}$", "$options": "i"}}
            )
        if niche:
            query_conditions.append({"target_niches": niche})

        skip = (page - 1) * limit
        campaigns = (
            await Campaign.find(*query_conditions)
            .sort("-created_at")
            .skip(skip)
            .limit(limit + 1)
            .to_list()
        )
        has_more = len(campaigns) > limit
        campaigns = campaigns[:limit]

        return CampaignListResponse(
            results=[CampaignCardResponse.model_validate(c.model_dump()) for c in campaigns],
            total=len(campaigns),
            page=page,
            limit=limit,
            has_more=has_more,
        )

    # ─────────────────────────────────────────────────────────
    # Create Campaign
    # ─────────────────────────────────────────────────────────

    async def create_campaign(
        self,
        body: CampaignCreateRequest,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> CampaignResponse:
        """Brand posts a new campaign brief."""
        brand_profile = await BrandProfile.find_one(
            BrandProfile.user_id == str(current_user.id)
        )
        if not brand_profile:
            raise HTTPException(
                status_code=404,
                detail="Brand profile not found. Complete onboarding first.",
            )

        campaign = Campaign(
            brand_id=str(brand_profile.id),
            brand_user_id=str(current_user.id),
            **body.model_dump(),
        )
        await campaign.insert()

        # Increment brand campaign counter
        brand_profile.total_campaigns_posted += 1
        await brand_profile.save()

        return CampaignResponse.model_validate(campaign.model_dump())

    # ─────────────────────────────────────────────────────────
    # Get Campaign
    # ─────────────────────────────────────────────────────────

    async def get_campaign(self, campaign_id: str) -> CampaignResponse:
        """Get a campaign brief's full detail."""
        campaign = await Campaign.get(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        return CampaignResponse.model_validate(campaign.model_dump())

    # ─────────────────────────────────────────────────────────
    # Update Campaign
    # ─────────────────────────────────────────────────────────

    async def update_campaign(
        self,
        campaign_id: str,
        body: CampaignUpdateRequest,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> CampaignResponse:
        """Update a campaign brief. Only the owning brand can edit."""
        campaign = await Campaign.get(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if campaign.brand_user_id != str(current_user.id):
            raise HTTPException(
                status_code=403, detail="You can only edit your own campaigns."
            )

        update_fields = body.model_dump(exclude_none=True)
        for field, value in update_fields.items():
            setattr(campaign, field, value)
        campaign.updated_at = datetime.utcnow()
        await campaign.save()

        return CampaignResponse.model_validate(campaign.model_dump())

    # ─────────────────────────────────────────────────────────
    # Close Campaign
    # ─────────────────────────────────────────────────────────

    async def close_campaign(
        self,
        campaign_id: str,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> dict:
        """Close a campaign brief. Sets status to CLOSED."""
        campaign = await Campaign.get(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if campaign.brand_user_id != str(current_user.id):
            raise HTTPException(
                status_code=403, detail="You can only close your own campaigns."
            )

        campaign.status = CampaignStatus.CLOSED
        campaign.updated_at = datetime.utcnow()
        await campaign.save()

        return {"message": "Campaign closed successfully."}

    # ─────────────────────────────────────────────────────────
    # Express Interest (Creator)
    # ─────────────────────────────────────────────────────────

    async def express_interest(
        self,
        campaign_id: str,
        current_user: User = Depends(auth_middleware.require_role(UserRole.CREATOR)),
    ) -> dict:
        """Creator expresses interest in a brand's campaign brief."""
        campaign = await Campaign.get(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if campaign.status != CampaignStatus.OPEN:
            raise HTTPException(
                status_code=400,
                detail="This campaign is no longer accepting interest.",
            )

        creator_profile = await CreatorProfile.find_one(
            CreatorProfile.user_id == str(current_user.id)
        )
        if not creator_profile:
            raise HTTPException(
                status_code=404,
                detail="Creator profile not found. Complete onboarding first.",
            )

        creator_profile_id = str(creator_profile.id)
        if creator_profile_id in campaign.interested_creator_ids:
            raise HTTPException(
                status_code=400,
                detail="You have already expressed interest in this campaign.",
            )

        campaign.interested_creator_ids.append(creator_profile_id)
        campaign.interested_count += 1
        await campaign.save()

        # Notify brand
        await self.notification_service.notify_campaign_interest(
            brand_user_id=campaign.brand_user_id,
            creator_user_id=str(current_user.id),
            creator_profile_id=creator_profile_id,
            campaign_id=campaign_id,
            campaign_title=campaign.title,
        )

        return {"message": "Interest submitted! The brand will be notified."}

    # ─────────────────────────────────────────────────────────
    # Get Interested Creators (Brand Only)
    # ─────────────────────────────────────────────────────────

    async def get_interested_creators(
        self,
        campaign_id: str,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> dict:
        """Brand views the list of creators who expressed interest."""
        campaign = await Campaign.get(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if campaign.brand_user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied.")

        creators = await CreatorProfile.find(
            {"_id": {"$in": campaign.interested_creator_ids}}
        ).to_list()

        return {
            "campaign_id": campaign_id,
            "interested_count": campaign.interested_count,
            "creators": [c.model_dump() for c in creators],
        }


# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
campaign_router = CampaignRouter()
