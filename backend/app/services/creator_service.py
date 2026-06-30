"""
Nexus — Creator Service (Class-based)
--------------------------------------------
Business logic for creator profile operations:
  - Create profile on first onboarding
  - Update profile (niche, city, rate card, toggle)
  - Discovery search with filters and sorting
  - Track profile view counts

All heavy I/O (Instagram stat fetches) go through InstagramService + Celery.
This service handles only synchronous-friendly DB operations.

Usage:
    from app.services.creator_service import CreatorService
    service = CreatorService()
    results = await service.search(filters=SearchFilters(...))
"""

from datetime import datetime
from typing import List, Optional

from beanie.odm.operators.find.comparison import In
from beanie.odm.operators.find.logical import And

from app.core.logger import logger
from app.models.creator_profile import (
    CollabType,
    CreatorProfile,
    FollowerTier,
    NicheCategory,
)
from app.schemas.creator import CreatorSearchFilters, CreatorUpdateRequest


class CreatorNotFoundError(Exception):
    """Raised when a creator profile lookup returns nothing."""
    pass


class CreatorService:
    """
    Handles all creator profile business logic.

    Methods are async and use Beanie ODM for MongoDB operations.
    Heavy background tasks (IG sync) are triggered as Celery tasks,
    never awaited inline.
    """

    # ─────────────────────────────────────────────────────────
    # Profile Management
    # ─────────────────────────────────────────────────────────

    async def create_profile(self, user_id: str, display_name: str) -> CreatorProfile:
        """
        Create a blank CreatorProfile for a new creator.
        Called at the start of creator onboarding.

        Args:
            user_id: String of User._id
            display_name: The creator's chosen display name

        Returns:
            New CreatorProfile document
        """
        # Check if profile already exists (idempotent)
        existing = await CreatorProfile.find_one(
            CreatorProfile.user_id == user_id
        )
        if existing:
            logger.warning(
                f"CreatorProfile already exists for user_id={user_id}"
            )
            return existing

        profile = CreatorProfile(
            user_id=user_id,
            display_name=display_name,
        )
        await profile.insert()
        logger.info(f"CreatorProfile created — user_id={user_id}")
        return profile

    async def get_by_user_id(self, user_id: str) -> CreatorProfile:
        """
        Fetch a creator's profile by their User._id.
        Creates a profile lazily if it doesn't exist yet but the User does.

        Raises:
            CreatorNotFoundError: If the user does not exist or profile creation fails
        """
        profile = await CreatorProfile.find_one(
            CreatorProfile.user_id == user_id
        )
        if not profile:
            from app.models.user import User
            user = await User.get(user_id)
            if user:
                profile = await self.create_profile(user_id=user_id, display_name=user.name)
            else:
                raise CreatorNotFoundError(
                    f"No creator profile found for user_id={user_id}"
                )
        return profile

    async def get_by_profile_id(self, profile_id: str) -> CreatorProfile:
        """
        Fetch a creator's profile by their CreatorProfile._id.

        Raises:
            CreatorNotFoundError: If the profile ID is invalid
        """
        profile = await CreatorProfile.get(profile_id)
        if not profile:
            raise CreatorNotFoundError(
                f"CreatorProfile '{profile_id}' not found."
            )
        return profile

    async def update_profile(
        self,
        user_id: str,
        update_data: "CreatorUpdateRequest",
    ) -> CreatorProfile:
        """
        Apply profile updates from the settings page.
        Only non-None fields in update_data are applied.

        Args:
            user_id: User._id of the authenticated creator
            update_data: Pydantic schema with optional update fields

        Returns:
            Updated CreatorProfile document
        """
        profile = await self.get_by_user_id(user_id)

        update_fields = update_data.model_dump(exclude_none=True)

        if "avatar_url" in update_fields:
            avatar_url = update_fields.pop("avatar_url")
            profile.instagram_profile_pic_url = avatar_url
            from app.models.user import User
            user = await User.get(user_id)
            if user:
                user.avatar_url = avatar_url
                await user.save()

        for field, value in update_fields.items():
            setattr(profile, field, value)

        profile.updated_at = datetime.utcnow()
        await profile.save()

        logger.info(
            f"CreatorProfile updated — user_id={user_id}, "
            f"fields={list(update_fields.keys())}"
        )
        return profile

    async def toggle_open_to_collabs(self, user_id: str) -> CreatorProfile:
        """
        Toggle the `open_to_collabs` flag on the creator's profile.
        When False, the creator is hidden from brand discovery searches.

        Returns:
            Updated CreatorProfile with new toggle state
        """
        profile = await self.get_by_user_id(user_id)
        profile.open_to_collabs = not profile.open_to_collabs
        profile.updated_at = datetime.utcnow()
        await profile.save()

        status = "OPEN" if profile.open_to_collabs else "CLOSED"
        logger.info(
            f"Collab toggle → {status} — user_id={user_id}"
        )
        return profile

    async def increment_profile_views(self, profile_id: str) -> None:
        """
        Increment the profile_views counter.
        Called every time a brand views a creator's full profile.
        Fire-and-forget — does not block the response.
        """
        await CreatorProfile.find_one(
            CreatorProfile.id == profile_id
        ).update({"$inc": {"profile_views": 1}})

    # ─────────────────────────────────────────────────────────
    # Discovery Search
    # ─────────────────────────────────────────────────────────

    async def search(
        self,
        filters: "CreatorSearchFilters",
        skip: int = 0,
        limit: int = 20,
    ) -> List[CreatorProfile]:
        """
        Execute a filtered, sorted creator discovery search.

        Filters applied (all optional — any combination):
          - city: exact match (case-insensitive)
          - state: exact match
          - niches: at least one niche from the list must match
          - follower_tier: exact enum match
          - collab_types: at least one collab type must match
          - open_to_collabs: if True, only return open creators
          - min_engagement_rate: lower bound on engagement rate
          - max_rate: upper bound on creator's rate_max

        Default sort: engagement rate descending (highest quality first).
        Secondary sort: follower count descending (within same engagement tier).

        Args:
            filters: CreatorSearchFilters schema
            skip: Pagination offset
            limit: Max results (capped at 50)

        Returns:
            List of matching CreatorProfile documents
        """
        limit = min(limit, 50)  # Hard cap at 50 per page

        query_conditions = []

        # Only discoverable creators
        query_conditions.append(CreatorProfile.open_to_collabs == True)  # noqa: E712

        # City filter (case-insensitive)
        if filters.city:
            query_conditions.append(
                {"city": {"$regex": f"^{filters.city}$", "$options": "i"}}
            )

        # State filter
        if filters.state:
            query_conditions.append(
                {"state": {"$regex": f"^{filters.state}$", "$options": "i"}}
            )

        # Niche filter (creator must have at least one matching niche)
        if filters.niches:
            query_conditions.append(
                CreatorProfile.niches.in_(filters.niches)
            )

        # Follower tier filter
        if filters.follower_tier:
            query_conditions.append(
                CreatorProfile.follower_tier == filters.follower_tier
            )

        # Collab type filter
        if filters.collab_types:
            query_conditions.append(
                CreatorProfile.collab_types.in_(filters.collab_types)
            )

        # Engagement rate lower bound
        if filters.min_engagement_rate is not None:
            query_conditions.append(
                CreatorProfile.instagram_engagement_rate >= filters.min_engagement_rate
            )

        # Rate upper bound (based on creator's rate_max)
        if filters.max_rate is not None:
            query_conditions.append(
                CreatorProfile.rate_min <= filters.max_rate
            )

        # Build and execute query
        query = CreatorProfile.find(*query_conditions)

        # Sort: engagement rate desc, then followers desc
        results = (
            await query
            .sort(
                [
                    ("-instagram_engagement_rate", 1),
                    ("-instagram_followers", 1),
                ]
            )
            .skip(skip)
            .limit(limit)
            .to_list()
        )

        return results

    async def get_featured(self, limit: int = 8) -> List[CreatorProfile]:
        """
        Return admin-curated featured creators for the landing page.
        Only returns creators who are open to collabs.
        """
        return (
            await CreatorProfile.find(
                CreatorProfile.is_featured == True,  # noqa: E712
                CreatorProfile.open_to_collabs == True,  # noqa: E712
            )
            .sort("-instagram_engagement_rate")
            .limit(limit)
            .to_list()
        )
