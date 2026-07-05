"""
Nexus — Brands Router (Class-based)
------------------------------------------
Brand profile creation, retrieval, and update.

Dependencies flow:
  BrandRouter -> BrandProfile (Beanie) -> DB
  Schemas imported from schemas/brand.py
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.core.logger import logger
from app.middleware.auth_middleware import auth_middleware
from app.models.brand_profile import BrandProfile
from app.models.user import User, UserRole
from app.schemas.brand import BrandCreateRequest, BrandProfileResponse, BrandUpdateRequest


class BrandRouter:
    """
    Class-based router for brand profile endpoints.

    Note: Brand profile logic is simple enough (no dedicated BrandService)
    that the router handles DB operations directly via Beanie.
    A BrandService can be extracted later if business logic grows.

    Usage:
        brand_router = BrandRouter()
        app.include_router(brand_router.router, prefix="/api/brands", tags=["Brands"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes on self.router."""
        self.router.add_api_route(
            "/profile",
            self.create_brand_profile,
            methods=["POST"],
            summary="Create brand profile",
            response_model=BrandProfileResponse,
            status_code=201,
        )
        self.router.add_api_route(
            "/profile",
            self.get_own_brand_profile,
            methods=["GET"],
            summary="Get own brand profile",
            response_model=BrandProfileResponse,
        )
        self.router.add_api_route(
            "/profile",
            self.update_brand_profile,
            methods=["PUT"],
            summary="Update brand profile",
            response_model=BrandProfileResponse,
        )
        self.router.add_api_route(
            "/sync-instagram",
            self.sync_instagram,
            methods=["POST"],
            summary="Manually trigger Instagram stat refresh for brand",
        )
        self.router.add_api_route(
            "/{brand_profile_id}",
            self.get_brand_profile,
            methods=["GET"],
            summary="Get brand public profile",
            response_model=BrandProfileResponse,
        )

    # ─────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────

    def _to_response(self, profile: BrandProfile) -> BrandProfileResponse:
        """Map a BrandProfile document to BrandProfileResponse."""
        return BrandProfileResponse(
            id=str(profile.id),
            user_id=profile.user_id,
            business_name=profile.business_name,
            tagline=getattr(profile, "tagline", None),
            description=getattr(profile, "description", None),
            logo_url=getattr(profile, "logo_url", None),
            category=getattr(profile, "category", None),
            website_url=getattr(profile, "website_url", None),
            instagram_handle=getattr(profile, "instagram_handle", None),
            instagram_followers=getattr(profile, "instagram_followers", 0),
            instagram_following=getattr(profile, "instagram_following", 0),
            instagram_post_count=getattr(profile, "instagram_post_count", 0),
            instagram_avg_likes=getattr(profile, "instagram_avg_likes", 0.0),
            instagram_avg_comments=getattr(profile, "instagram_avg_comments", 0.0),
            instagram_engagement_rate=getattr(profile, "instagram_engagement_rate", 0.0),
            instagram_profile_pic_url=getattr(profile, "instagram_profile_pic_url", None),
            instagram_last_synced=getattr(profile, "instagram_last_synced", None),
            city=getattr(profile, "city", None),
            state=getattr(profile, "state", None),
            total_connections=getattr(profile, "total_connections", 0),
            total_campaigns_posted=getattr(profile, "total_campaigns_posted", 0),
            created_at=profile.created_at,
        )

    # ─────────────────────────────────────────────────────────
    # Create Profile
    # ─────────────────────────────────────────────────────────

    async def create_brand_profile(
        self,
        body: BrandCreateRequest,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> BrandProfileResponse:
        """
        Create a brand profile during onboarding.
        Idempotent — returns existing profile if already created.
        """
        existing = await BrandProfile.find_one(
            BrandProfile.user_id == str(current_user.id)
        )
        if existing:
            return self._to_response(existing)

        profile = BrandProfile(
            user_id=str(current_user.id),
            business_name=body.business_name,
            category=body.category,
            tagline=body.tagline,
            description=body.description,
            website_url=body.website_url,
            instagram_handle=body.instagram_handle or getattr(current_user, "instagram_username", None),
            city=body.city,
            state=body.state,
        )
        await profile.insert()

        # Mark onboarding complete
        current_user.onboarding_complete = True
        await current_user.save()

        return self._to_response(profile)

    # ─────────────────────────────────────────────────────────
    # Get Own Profile
    # ─────────────────────────────────────────────────────────

    async def get_own_brand_profile(
        self,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> BrandProfileResponse:
        """Fetch the authenticated brand's own profile."""
        profile = await BrandProfile.find_one(
            BrandProfile.user_id == str(current_user.id)
        )
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Brand profile not found. Please complete onboarding.",
            )
        return self._to_response(profile)

    # ─────────────────────────────────────────────────────────
    # Get Public Profile
    # ─────────────────────────────────────────────────────────

    async def get_brand_profile(
        self,
        brand_profile_id: str,
    ) -> BrandProfileResponse:
        """Public brand profile — visible to all authenticated users."""
        profile = await BrandProfile.get(brand_profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Brand not found.")
        return self._to_response(profile)

    # ─────────────────────────────────────────────────────────
    # Update Profile
    # ─────────────────────────────────────────────────────────

    async def update_brand_profile(
        self,
        body: BrandUpdateRequest,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> BrandProfileResponse:
        """Partially update the authenticated brand's profile."""
        profile = await BrandProfile.find_one(
            BrandProfile.user_id == str(current_user.id)
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Brand profile not found.")

        update_fields = body.model_dump(exclude_none=True)
        for field, value in update_fields.items():
            setattr(profile, field, value)
        profile.updated_at = datetime.utcnow()
        await profile.save()

        return self._to_response(profile)

    # ─────────────────────────────────────────────────────────
    # Instagram Sync
    # ─────────────────────────────────────────────────────────

    async def sync_instagram(
        self,
        current_user: User = Depends(auth_middleware.require_role(UserRole.BRAND)),
    ) -> BrandProfileResponse:
        """
        Run an immediate Instagram stat sync for the brand and return the updated profile.
        Returns a descriptive error if sync fails — never swallows errors.
        """
        if not current_user.instagram_user_id:
            raise HTTPException(
                status_code=400,
                detail="No Instagram account connected. Please connect Instagram first.",
            )

        profile = await BrandProfile.find_one(
            BrandProfile.user_id == str(current_user.id)
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Brand profile not found.")

        from app.services.instagram_service import (
            InstagramService,
            InstagramTokenExpiredError,
            InstagramAPIError,
        )

        service = InstagramService()
        try:
            updated_profile = await service.sync_brand_stats(
                user_id=str(current_user.id),
                brand_profile_id=str(profile.id),
            )
            return self._to_response(updated_profile)
        except InstagramTokenExpiredError as e:
            logger.warning(f"Token expired for brand {current_user.id}: {e}")
            raise HTTPException(
                status_code=401,
                detail="Your Instagram session has expired. Please reconnect your Instagram account.",
            )
        except InstagramAPIError as e:
            logger.error(f"Instagram API error for brand {current_user.id}: {e}")
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected sync error for brand {current_user.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again later.",
            )
        finally:
            await service.close()



# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
brand_router = BrandRouter()
