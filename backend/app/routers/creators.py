"""
Nexus — Creators Router (Class-based)
--------------------------------------------
Creator profile management and discovery search.

Dependencies flow:
  CreatorRouter -> CreatorService -> DB (Beanie)
"""

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from app.core.logger import logger
from app.middleware.auth_middleware import auth_middleware
from app.models.creator_profile import CollabType, FollowerTier, NicheCategory
from app.models.user import User, UserRole
from app.schemas.creator import (
    CreatorCardResponse,
    CreatorProfileResponse,
    CreatorSearchFilters,
    CreatorSearchResponse,
    CreatorUpdateRequest,
)
from app.services.creator_service import CreatorNotFoundError, CreatorService


class CreatorRouter:
    """
    Class-based router for all creator-related endpoints.

    Encapsulates:
        - CreatorService instance
        - All route handler methods
        - Route registration logic

    Usage:
        creator_router = CreatorRouter()
        app.include_router(creator_router.router, prefix="/api/creators", tags=["Creators"])
    """

    def __init__(self) -> None:
        self.router = APIRouter()
        self.creator_service = CreatorService()
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all routes on self.router."""
        self.router.add_api_route(
            "/search",
            self.search_creators,
            methods=["GET"],
            summary="Discover creators",
            response_model=CreatorSearchResponse,
        )
        self.router.add_api_route(
            "/profile",
            self.update_creator_profile,
            methods=["PUT"],
            summary="Update creator profile",
            response_model=CreatorProfileResponse,
        )
        self.router.add_api_route(
            "/toggle-collab",
            self.toggle_open_to_collabs,
            methods=["PATCH"],
            summary="Toggle open to collabs",
        )
        self.router.add_api_route(
            "/sync-instagram",
            self.sync_instagram,
            methods=["POST"],
            summary="Manually trigger Instagram stat refresh",
        )
        # Profile by ID last — avoids capturing /profile, /search etc.
        self.router.add_api_route(
            "/{profile_id}",
            self.get_creator_profile,
            methods=["GET"],
            summary="Get creator public profile",
            response_model=CreatorProfileResponse,
        )

    # ─────────────────────────────────────────────────────────
    # Discovery Search
    # ─────────────────────────────────────────────────────────

    async def search_creators(
        self,
        city: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        niches: Optional[List[NicheCategory]] = Query(None),
        follower_tier: Optional[FollowerTier] = Query(None),
        collab_types: Optional[List[CollabType]] = Query(None),
        min_engagement_rate: Optional[float] = Query(None, ge=0, le=100),
        max_rate: Optional[int] = Query(None, ge=0),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=50),
        viewer: Optional[User] = Depends(auth_middleware.get_optional_user),
    ) -> CreatorSearchResponse:
        """
        Search and filter verified creators for brand discovery.
        Public endpoint — shows results to both authenticated and anonymous users.
        """
        filters = CreatorSearchFilters(
            city=city, state=state, niches=niches,
            follower_tier=follower_tier, collab_types=collab_types,
            min_engagement_rate=min_engagement_rate, max_rate=max_rate,
        )
        skip = (page - 1) * limit
        results = await self.creator_service.search(filters=filters, skip=skip, limit=limit + 1)
        has_more = len(results) > limit
        results = results[:limit]

        return CreatorSearchResponse(
            results=[CreatorCardResponse.model_validate(c.model_dump()) for c in results],
            total=len(results),
            page=page,
            limit=limit,
            has_more=has_more,
        )

    # ─────────────────────────────────────────────────────────
    # Profile — Get
    # ─────────────────────────────────────────────────────────

    async def get_creator_profile(
        self,
        profile_id: str,
        background_tasks: BackgroundTasks,
        viewer: Optional[User] = Depends(auth_middleware.get_optional_user),
    ) -> CreatorProfileResponse:
        """Return a creator's full public profile. Increments view counter in background."""
        logger.info(f"get_creator_profile called with profile_id={profile_id}, viewer_id={str(viewer.id) if viewer else 'None'}")
        try:
            if profile_id == "me":
                if not viewer:
                    logger.warning("get_creator_profile: 'me' requested but no viewer authenticated")
                    raise HTTPException(status_code=401, detail="Authentication required.")
                profile = await self.creator_service.get_by_user_id(str(viewer.id))
                logger.info(f"get_creator_profile: resolved 'me' to profile ID {profile.id} for user {viewer.id}")
            else:
                profile = await self.creator_service.get_by_profile_id(profile_id)
                logger.info(f"get_creator_profile: resolved profile_id={profile_id} to user_id={profile.user_id}")
        except CreatorNotFoundError as e:
            logger.warning(f"get_creator_profile: CreatorNotFoundError for profile_id={profile_id}: {e}")
            raise HTTPException(status_code=404, detail="Creator not found.")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"get_creator_profile: unexpected error for profile_id={profile_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

        # Track profile view in background (non-blocking)
        background_tasks.add_task(self.creator_service.increment_profile_views, str(profile.id))

        return CreatorProfileResponse.model_validate(profile.model_dump())

    # ─────────────────────────────────────────────────────────
    # Profile — Update
    # ─────────────────────────────────────────────────────────

    async def update_creator_profile(
        self,
        body: CreatorUpdateRequest,
        current_user: User = Depends(auth_middleware.require_role(UserRole.CREATOR)),
    ) -> CreatorProfileResponse:
        """Update the authenticated creator's profile."""
        try:
            profile = await self.creator_service.update_profile(
                user_id=str(current_user.id), update_data=body
            )
        except CreatorNotFoundError:
            raise HTTPException(status_code=404, detail="Creator profile not found.")
        
        # Mark onboarding complete
        if not current_user.onboarding_complete:
            current_user.onboarding_complete = True
            await current_user.save()

        return CreatorProfileResponse.model_validate(profile.model_dump())

    # ─────────────────────────────────────────────────────────
    # Collab Toggle
    # ─────────────────────────────────────────────────────────

    async def toggle_open_to_collabs(
        self,
        current_user: User = Depends(auth_middleware.require_role(UserRole.CREATOR)),
    ) -> dict:
        """Toggle the creator's discoverability in brand searches."""
        try:
            profile = await self.creator_service.toggle_open_to_collabs(str(current_user.id))
        except CreatorNotFoundError:
            raise HTTPException(status_code=404, detail="Creator profile not found.")
        return {
            "open_to_collabs": profile.open_to_collabs,
            "message": (
                f"You are now {'visible to' if profile.open_to_collabs else 'hidden from'} brands."
            ),
        }

    # ─────────────────────────────────────────────────────────
    # Instagram Sync
    # ─────────────────────────────────────────────────────────

    async def sync_instagram(
        self,
        current_user: User = Depends(auth_middleware.require_role(UserRole.CREATOR)),
    ) -> CreatorProfileResponse:
        """
        Run an immediate Instagram stat sync for the creator and return the updated profile.
        Returns a descriptive error if sync fails — never swallows errors.
        """
        if not current_user.instagram_user_id:
            raise HTTPException(
                status_code=400,
                detail="No Instagram account connected. Please connect Instagram first.",
            )

        try:
            profile = await self.creator_service.get_by_user_id(str(current_user.id))
        except CreatorNotFoundError:
            raise HTTPException(status_code=404, detail="Creator profile not found.")

        from app.services.instagram_service import (
            InstagramService,
            InstagramTokenExpiredError,
            InstagramAPIError,
        )

        service = InstagramService()
        try:
            updated_profile = await service.sync_creator_stats(
                user_id=str(current_user.id),
                creator_profile_id=str(profile.id),
            )
            return CreatorProfileResponse.model_validate(updated_profile.model_dump())
        except InstagramTokenExpiredError as e:
            logger.warning(f"Token expired for creator {current_user.id}: {e}")
            raise HTTPException(
                status_code=401,
                detail="Your Instagram session has expired. Please reconnect your Instagram account.",
            )
        except InstagramAPIError as e:
            logger.error(f"Instagram API error for creator {current_user.id}: {e}")
            raise HTTPException(status_code=502, detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected sync error for creator {current_user.id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred. Please try again later.",
            )
        finally:
            await service.close()



# ─────────────────────────────────────────────────────────────
# Module-level singleton — imported by main.py
# ─────────────────────────────────────────────────────────────
creator_router = CreatorRouter()
