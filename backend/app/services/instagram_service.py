"""
Nexus — Instagram Service (Class-based)
----------------------------------------------
Handles all communication with the Instagram Basic Display API.

Responsibilities:
  - Fetch creator profile info (username, bio, profile pic)
  - Fetch media list and calculate engagement rate
  - Compute follower tier from follower count
  - Update CreatorProfile document with fresh stats

The Celery task (`tasks/instagram_sync.py`) calls this service —
never call it inline from a request handler (it can take 2–5 seconds).

Usage:
    from app.services.instagram_service import InstagramService
    service = InstagramService()
    await service.sync_creator_stats(user_id="...", creator_profile_id="...")
"""

from datetime import datetime
from typing import Optional

import httpx

from app.config import settings
from app.core.encryption import encryption_manager
from app.core.logger import logger
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
    Wraps the Instagram Basic Display API.

    Fields fetched per creator sync:
      - account_type, username, media_count, followers_count, follows_count
      - Recent media: like_count, comments_count (to compute avg engagement)

    Note: Instagram Basic Display API does NOT expose follower counts directly.
    We use the `instagram_graph_api` endpoint (requires Business/Creator account
    linked to Facebook Page) for full stats. For Basic Display API users,
    we use media engagement as a proxy.

    The service gracefully degrades — if follower count is unavailable,
    engagement rate is still computed from available media data.
    """

    GRAPH_BASE_URL = "https://graph.instagram.com"
    MEDIA_FIELDS = "id,media_type,like_count,comments_count,timestamp"
    PROFILE_FIELDS = "id,username,account_type,media_count,followers_count,profile_picture_url"

    def __init__(self) -> None:
        self._http = None

    @property
    def http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=15.0)
        return self._http

    async def sync_creator_stats(self, user_id: str, creator_profile_id: str) -> CreatorProfile:
        """
        Full sync: fetch Instagram stats and update the CreatorProfile document.

        This is the main entry point called by the Celery task.

        Args:
            user_id: The User._id (to retrieve encrypted token)
            creator_profile_id: The CreatorProfile._id to update

        Returns:
            Updated CreatorProfile document

        Raises:
            InstagramAPIError: If the API call fails
            InstagramTokenExpiredError: If the token needs refresh
        """
        # Load user and decrypt token
        user = await User.get(user_id)
        if not user or not user.instagram_access_token_encrypted:
            raise InstagramAPIError(
                f"User {user_id} has no Instagram token stored."
            )

        access_token = encryption_manager.decrypt(
            user.instagram_access_token_encrypted
        )

        # Load creator profile
        creator = await CreatorProfile.get(creator_profile_id)
        if not creator:
            raise InstagramAPIError(
                f"CreatorProfile {creator_profile_id} not found."
            )

        # Fetch profile and media data
        profile_data = await self._fetch_profile(access_token)
        media_stats = await self._fetch_media_engagement(access_token)

        # Update the creator profile document
        creator = await self._apply_stats(creator, profile_data, media_stats)

        logger.success(
            f"Instagram sync complete — creator={creator_profile_id}, "
            f"followers={creator.instagram_followers}, "
            f"engagement={creator.instagram_engagement_rate:.2f}%"
        )
        return creator

    async def _fetch_profile(self, access_token: str) -> dict:
        """Fetch basic profile information from Instagram Graph API."""
        if settings.is_development:
            try:
                # 1. Try fetching with advanced fields (followers_count, profile_picture_url)
                response = await self.http.get(
                    f"{self.GRAPH_BASE_URL}/me",
                    params={
                        "fields": self.PROFILE_FIELDS,
                        "access_token": access_token,
                    },
                )
                if response.status_code == 200:
                    return self._handle_response(response)

                # 2. Try fetching with basic fields
                logger.info("Instagram profile fetch with advanced fields failed. Retrying with basic fields...")
                response_basic = await self.http.get(
                    f"{self.GRAPH_BASE_URL}/me",
                    params={
                        "fields": "id,username,account_type,media_count",
                        "access_token": access_token,
                    },
                )
                if response_basic.status_code == 200:
                    return self._handle_response(response_basic)
            except Exception as e:
                logger.warning(f"Failed to fetch live Instagram profile in dev mode, falling back to mock: {e}")

            return {
                "username": "mock_creator_insta",
                "media_count": 48,
                "followers_count": 24500,
                "profile_pic_url": "https://api.dicebear.com/7.x/adventurer/svg?seed=Priya",
            }

        # Staging / Production mode
        try:
            response = await self.http.get(
                f"{self.GRAPH_BASE_URL}/me",
                params={
                    "fields": self.PROFILE_FIELDS,
                    "access_token": access_token,
                },
            )
            if response.status_code == 200:
                return self._handle_response(response)
        except Exception as e:
            logger.warning(f"Instagram profile fetch with advanced fields failed: {e}. Retrying with basic fields...")

        response_basic = await self.http.get(
            f"{self.GRAPH_BASE_URL}/me",
            params={
                "fields": "id,username,account_type,media_count",
                "access_token": access_token,
            },
        )
        return self._handle_response(response_basic)

    async def _fetch_media_engagement(self, access_token: str) -> dict:
        """
        Fetch recent media and compute average likes + comments.

        Uses the last 12 posts to compute the engagement rate.
        Returns a dict with avg_likes, avg_comments, post_count.
        """
        if settings.is_development:
            try:
                # 1. Try fetching with live insights (likes, comments)
                response = await self.http.get(
                    f"{self.GRAPH_BASE_URL}/me/media",
                    params={
                        "fields": self.MEDIA_FIELDS,
                        "limit": 12,
                        "access_token": access_token,
                    },
                )
                if response.status_code == 200:
                    data = self._handle_response(response)
                    media_list = data.get("data", [])
                    if media_list:
                        total_likes = sum(m.get("like_count", 0) for m in media_list)
                        total_comments = sum(m.get("comments_count", 0) for m in media_list)
                        count = len(media_list)
                        return {
                            "avg_likes": round(total_likes / count, 2),
                            "avg_comments": round(total_comments / count, 2),
                            "post_count": count,
                        }

                # 2. If first call failed/non-200, try with basic fields
                logger.info("Live Instagram media insights fetch failed. Retrying with basic fields (no likes/comments)...")
                response_basic = await self.http.get(
                    f"{self.GRAPH_BASE_URL}/me/media",
                    params={
                        "fields": "id,media_type,timestamp",
                        "limit": 12,
                        "access_token": access_token,
                    },
                )
                if response_basic.status_code == 200:
                    data_basic = self._handle_response(response_basic)
                    media_list_basic = data_basic.get("data", [])
                    return {
                        "avg_likes": 0.0,
                        "avg_comments": 0.0,
                        "post_count": len(media_list_basic),
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch live Instagram media in dev mode, falling back to mock: {e}")

            return {
                "avg_likes": 842.0,
                "avg_comments": 45.0,
                "post_count": 12,
            }

        # Staging / Production mode
        try:
            response = await self.http.get(
                f"{self.GRAPH_BASE_URL}/me/media",
                params={
                    "fields": self.MEDIA_FIELDS,
                    "limit": 12,
                    "access_token": access_token,
                },
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
        except Exception as e:
            logger.warning(f"Instagram media insights fetch failed. Retrying with basic fields: {e}")
            try:
                response_basic = await self.http.get(
                    f"{self.GRAPH_BASE_URL}/me/media",
                    params={
                        "fields": "id,media_type,timestamp",
                        "limit": 12,
                        "access_token": access_token,
                    },
                )
                data_basic = self._handle_response(response_basic)
                media_list_basic = data_basic.get("data", [])
                return {
                    "avg_likes": 0.0,
                    "avg_comments": 0.0,
                    "post_count": len(media_list_basic),
                }
            except Exception as exc_inner:
                logger.error(f"Failed to fetch basic Instagram media in production: {exc_inner}")
                return {"avg_likes": 0.0, "avg_comments": 0.0, "post_count": 0}

    async def _apply_stats(
        self,
        creator: CreatorProfile,
        profile_data: dict,
        media_stats: dict,
    ) -> CreatorProfile:
        """
        Apply fetched statistics to the CreatorProfile document and save.

        Engagement rate = (avg_likes + avg_comments) / followers * 100
        NOTE: If follower count is 0 or unavailable, engagement rate stays 0.
        """
        # Update profile fields
        creator.instagram_handle = profile_data.get("username", creator.instagram_handle)
        creator.instagram_post_count = profile_data.get("media_count", creator.instagram_post_count)

        if "followers_count" in profile_data:
            creator.instagram_followers = profile_data["followers_count"]
        elif settings.is_development and (not creator.instagram_followers or creator.instagram_followers == 0):
            creator.instagram_followers = 24500

        profile_pic = profile_data.get("profile_picture_url") or profile_data.get("profile_pic_url")
        if profile_pic:
            creator.instagram_profile_pic_url = profile_pic
        elif settings.is_development and not creator.instagram_profile_pic_url:
            creator.instagram_profile_pic_url = "https://api.dicebear.com/7.x/adventurer/svg?seed=Priya"

        # Update engagement metrics
        creator.instagram_avg_likes = media_stats["avg_likes"]
        creator.instagram_avg_comments = media_stats["avg_comments"]

        # Compute engagement rate (use existing follower count if no new data)
        if creator.instagram_followers > 0:
            total_interactions = media_stats["avg_likes"] + media_stats["avg_comments"]
            creator.instagram_engagement_rate = round(
                (total_interactions / creator.instagram_followers) * 100, 2
            )

        # Update follower tier
        creator.follower_tier = creator.computed_follower_tier

        # Sync timestamp
        creator.instagram_last_synced = datetime.utcnow()
        creator.updated_at = datetime.utcnow()

        await creator.save()
        return creator

    def _handle_response(self, response: httpx.Response) -> dict:
        """
        Parse an Instagram API response.

        Raises:
            InstagramTokenExpiredError: On OAuth token errors
            InstagramAPIError: On other non-200 responses
        """
        if response.status_code == 200:
            return response.json()

        error_data = response.json().get("error", {})
        error_type = error_data.get("type", "")
        error_message = error_data.get("message", response.text)

        if error_type in ("OAuthException", "OAuthAccessTokenException"):
            raise InstagramTokenExpiredError(
                f"Instagram token expired or invalid: {error_message}"
            )

        raise InstagramAPIError(
            f"Instagram API error ({response.status_code}): {error_message}"
        )

    def compute_follower_tier(self, followers: int) -> FollowerTier:
        """
        Utility: compute the follower tier from a raw follower count.
        Stateless — can be called without an instance for batch operations.
        """
        if followers < 10_000:
            return FollowerTier.NANO
        elif followers < 100_000:
            return FollowerTier.MICRO
        elif followers < 500_000:
            return FollowerTier.MID
        return FollowerTier.MACRO

    async def close(self) -> None:
        """Clean up the HTTP client."""
        if self._http is not None:
            await self._http.aclose()
