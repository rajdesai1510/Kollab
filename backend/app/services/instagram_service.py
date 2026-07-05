"""
Nexus — Instagram Service (Class-based)
----------------------------------------------
Handles all communication with the Instagram Graph API.

The service ALWAYS attempts real API calls in every environment.
No dummy/mock data is returned — if the API fails, errors are propagated
so the caller can return a proper error message to the client.

Usage:
    from app.services.instagram_service import InstagramService
    service = InstagramService()
    await service.sync_creator_stats(user_id="...", creator_profile_id="...")
"""

from datetime import datetime

import httpx

from app.core.encryption import encryption_manager
from app.core.logger import logger
from app.models.brand_profile import BrandProfile
from app.models.creator_profile import CreatorProfile, FollowerTier
from app.models.user import User


class InstagramAPIError(Exception):
    """Raised when the Instagram Graph API returns an error response."""
    pass


class InstagramTokenExpiredError(InstagramAPIError):
    """Raised when Instagram returns OAuthException — token needs refresh."""
    pass


class InstagramService:
    """
    Wraps the Instagram Graph API.

    Behaves identically in dev / staging / production.
    Errors are always raised — never silently swallowed or replaced with mocks.
    """

    GRAPH_BASE_URL = "https://graph.instagram.com"
    MEDIA_FIELDS = "id,media_type,like_count,comments_count,timestamp"
    PROFILE_FIELDS = "id,username,account_type,media_count,followers_count,profile_picture_url"
    PROFILE_BASIC_FIELDS = "id,username,account_type,media_count"

    def __init__(self) -> None:
        self._http = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=15.0)
        return self._http

    # ------------------------------------------------------------------
    # Public sync entry points
    # ------------------------------------------------------------------

    async def sync_creator_stats(self, user_id: str, creator_profile_id: str) -> CreatorProfile:
        """Full sync: fetch Instagram stats and update the CreatorProfile document."""
        access_token = await self._get_access_token(user_id)

        creator = await CreatorProfile.get(creator_profile_id)
        if not creator:
            raise InstagramAPIError(f"CreatorProfile {creator_profile_id} not found.")

        profile_data = await self._fetch_profile(access_token)
        media_stats = await self._fetch_media_engagement(access_token)
        creator = await self._apply_stats(creator, profile_data, media_stats)

        logger.success(
            f"Instagram sync complete — creator={creator_profile_id}, "
            f"followers={creator.instagram_followers}, "
            f"engagement={creator.instagram_engagement_rate:.2f}%"
        )
        return creator

    async def sync_brand_stats(self, user_id: str, brand_profile_id: str) -> BrandProfile:
        """Full sync: fetch Instagram stats and update the BrandProfile document."""
        access_token = await self._get_access_token(user_id)

        brand = await BrandProfile.get(brand_profile_id)
        if not brand:
            raise InstagramAPIError(f"BrandProfile {brand_profile_id} not found.")

        profile_data = await self._fetch_profile(access_token)
        media_stats = await self._fetch_media_engagement(access_token)
        brand = await self._apply_stats(brand, profile_data, media_stats)

        logger.success(
            f"Instagram sync complete — brand={brand_profile_id}, "
            f"followers={brand.instagram_followers}, "
            f"engagement={brand.instagram_engagement_rate:.2f}%"
        )
        return brand

    # ------------------------------------------------------------------
    # Token helper
    # ------------------------------------------------------------------

    async def _get_access_token(self, user_id: str) -> str:
        user = await User.get(user_id)
        if not user:
            raise InstagramAPIError(f"User {user_id} not found.")
        if not user.instagram_access_token_encrypted:
            raise InstagramAPIError(
                "No Instagram account connected. Please connect Instagram first."
            )
        return encryption_manager.decrypt(user.instagram_access_token_encrypted)

    # ------------------------------------------------------------------
    # API fetch methods — real calls only, no mocks
    # ------------------------------------------------------------------

    async def _fetch_profile(self, access_token: str) -> dict:
        """
        Fetch profile info from Instagram Graph API.
        Tries full fields first, falls back to basic fields if needed.
        Raises on all errors — no mock fallback.
        """
        try:
            response = await self.http.get(
                f"{self.GRAPH_BASE_URL}/me",
                params={"fields": self.PROFILE_FIELDS, "access_token": access_token},
            )
            return self._handle_response(response)
        except InstagramTokenExpiredError:
            raise
        except (InstagramAPIError, Exception) as e:
            logger.warning(f"IG profile full-fields failed: {e}. Retrying with basic fields...")

        response_basic = await self.http.get(
            f"{self.GRAPH_BASE_URL}/me",
            params={"fields": self.PROFILE_BASIC_FIELDS, "access_token": access_token},
        )
        return self._handle_response(response_basic)

    async def _fetch_media_engagement(self, access_token: str) -> dict:
        """
        Fetch recent media and compute avg likes + comments.
        Falls back to basic fields (post count only) if engagement fields fail.
        Raises on all errors — no mock fallback.
        """
        try:
            response = await self.http.get(
                f"{self.GRAPH_BASE_URL}/me/media",
                params={"fields": self.MEDIA_FIELDS, "limit": 12, "access_token": access_token},
            )
            data = self._handle_response(response)
            media_list = data.get("data", [])

            if not media_list:
                return {"avg_likes": 0.0, "avg_comments": 0.0, "post_count": 0}

            total_likes = sum(m.get("like_count", 0) for m in media_list)
            total_comments = sum(m.get("comments_count", 0) for m in media_list)
            count = len(media_list)
            return {
                "avg_likes": round(total_likes / count, 2),
                "avg_comments": round(total_comments / count, 2),
                "post_count": count,
            }
        except InstagramTokenExpiredError:
            raise
        except (InstagramAPIError, Exception) as e:
            logger.warning(f"IG media engagement fetch failed: {e}. Retrying with basic fields...")

        response_basic = await self.http.get(
            f"{self.GRAPH_BASE_URL}/me/media",
            params={"fields": "id,media_type,timestamp", "limit": 12, "access_token": access_token},
        )
        data_basic = self._handle_response(response_basic)
        return {"avg_likes": 0.0, "avg_comments": 0.0, "post_count": len(data_basic.get("data", []))}

    # ------------------------------------------------------------------
    # Apply stats to profile document + save to MongoDB
    # ------------------------------------------------------------------

    async def _apply_stats(self, profile_doc, profile_data: dict, media_stats: dict):
        """
        Apply fetched stats to a profile doc (CreatorProfile or BrandProfile) and save.
        Always persists real data to MongoDB. No mocks in any environment.
        """
        if "username" in profile_data:
            profile_doc.instagram_handle = profile_data["username"]

        if "media_count" in profile_data:
            profile_doc.instagram_post_count = profile_data["media_count"]
        elif media_stats.get("post_count", 0) > 0:
            profile_doc.instagram_post_count = media_stats["post_count"]

        if "followers_count" in profile_data:
            profile_doc.instagram_followers = profile_data["followers_count"]

        if "follows_count" in profile_data:
            profile_doc.instagram_following = profile_data["follows_count"]

        profile_pic = profile_data.get("profile_picture_url") or profile_data.get("profile_pic_url")
        if profile_pic:
            profile_doc.instagram_profile_pic_url = profile_pic

        profile_doc.instagram_avg_likes = media_stats["avg_likes"]
        profile_doc.instagram_avg_comments = media_stats["avg_comments"]

        if profile_doc.instagram_followers > 0:
            total_interactions = media_stats["avg_likes"] + media_stats["avg_comments"]
            profile_doc.instagram_engagement_rate = round(
                (total_interactions / profile_doc.instagram_followers) * 100, 2
            )

        if isinstance(profile_doc, CreatorProfile):
            profile_doc.follower_tier = profile_doc.computed_follower_tier

        profile_doc.instagram_last_synced = datetime.utcnow()
        profile_doc.updated_at = datetime.utcnow()

        await profile_doc.save()
        logger.info(
            f"MongoDB updated — handle=@{profile_doc.instagram_handle}, "
            f"followers={profile_doc.instagram_followers}, "
            f"posts={profile_doc.instagram_post_count}"
        )
        return profile_doc

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code == 200:
            return response.json()

        try:
            error_data = response.json().get("error", {})
        except Exception:
            raise InstagramAPIError(f"Instagram API error ({response.status_code}): {response.text}")

        error_type = error_data.get("type", "")
        error_code = error_data.get("code", 0)
        error_message = error_data.get("message", response.text)
        error_subcode = error_data.get("error_subcode", 0)

        if error_type in ("OAuthException", "OAuthAccessTokenException") or error_code in (190, 102):
            raise InstagramTokenExpiredError(f"Instagram token expired or invalid: {error_message}")

        if error_code == 200 or error_subcode in (458, 459, 460, 463, 467):
            raise InstagramAPIError(
                f"Instagram permission error: {error_message}. Please reconnect your Instagram account."
            )

        raise InstagramAPIError(f"Instagram API error ({response.status_code}, code={error_code}): {error_message}")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def compute_follower_tier(self, followers: int) -> FollowerTier:
        if followers < 10_000:
            return FollowerTier.NANO
        elif followers < 100_000:
            return FollowerTier.MICRO
        elif followers < 500_000:
            return FollowerTier.MID
        return FollowerTier.MACRO

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()