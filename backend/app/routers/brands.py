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


# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
brand_router = BrandRouter()
