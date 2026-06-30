"""
Nexus — Instagram Sync Task (Class-based)
-------------------------------------------------
Celery task that synchronizes Instagram stats for creator profiles.

Architecture:
    InstagramSyncTask  — class encapsulating the async sync logic
    trigger_instagram_sync  — @celery_app.task function that runs the class

The class bridges the synchronous Celery worker world to the async
FastAPI/Beanie service layer using asyncio.run().

Called from:
    - AuthService.connect_instagram()  — on first Instagram token grant
    - CreatorRouter.sync_instagram()   — on manual refresh request

Usage:
    from app.tasks.instagram_sync import trigger_instagram_sync
    trigger_instagram_sync.delay(user_id=str(user.id), creator_profile_id=str(profile.id))
"""

import asyncio
import threading
from concurrent.futures import Future
from typing import Optional

from app.core.logger import logger
from app.tasks.celery_app import celery_app


class InstagramSyncTask:
    """
    Encapsulates the logic for syncing a single creator's Instagram stats.

    This class lives in a Celery worker process. It bridges:
        - The synchronous Celery task world
        - The async Motor/Beanie database layer

    Design:
        - run()  — synchronous entry point called by the Celery task function
        - _sync() — async method that calls InstagramService
        - Imports are lazy (inside methods) to avoid circular imports at module load
    """

    def run(self, user_id: str, creator_profile_id: Optional[str] = None) -> dict:
        """
        Synchronous entry point called by the Celery worker.

        Wraps the async _sync() method using asyncio.run() in a separate thread
        to avoid event loop conflicts when Celery is run in eager mode inside FastAPI.

        Args:
            user_id: User._id of the creator (used to fetch encrypted token)
            creator_profile_id: CreatorProfile._id to update.
                                 If None, looks up the profile by user_id.

        Returns:
            Dict with sync result summary: {user_id, profile_id, status, error?}
        """
        logger.info(
            f"InstagramSyncTask.run() started — "
            f"user_id={user_id}, profile_id={creator_profile_id}"
        )
        try:
            future = Future()
            def target():
                try:
                    res = asyncio.run(self._sync(user_id, creator_profile_id))
                    future.set_result(res)
                except Exception as e:
                    future.set_exception(e)
            
            t = threading.Thread(target=target)
            t.start()
            result = future.result()

            logger.success(
                f"InstagramSyncTask.run() complete — user_id={user_id}"
            )
            return result
        except Exception as exc:
            logger.error(
                f"InstagramSyncTask.run() failed — "
                f"user_id={user_id}: {exc}"
            )
            return {
                "user_id": user_id,
                "profile_id": creator_profile_id,
                "status": "error",
                "error": str(exc),
            }

    async def _sync(
        self,
        user_id: str,
        creator_profile_id: Optional[str] = None,
    ) -> dict:
        """
        Async core logic: resolve the profile_id if needed, then call InstagramService.

        Lazy imports prevent circular dependency issues at module import time.

        Args:
            user_id: User._id of the creator
            creator_profile_id: Explicit profile ID, or None to auto-resolve

        Returns:
            Dict with sync result summary
        """
        # Lazy import to avoid circular dependencies
        from app.core.database import db_manager
        from app.models.creator_profile import CreatorProfile
        from app.services.instagram_service import InstagramService

        # Ensure DB connection is open (Celery workers don't share the FastAPI lifespan)
        await db_manager.connect()

        # Resolve profile ID if not provided
        resolved_profile_id = creator_profile_id
        if not resolved_profile_id:
            profile = await CreatorProfile.find_one(
                CreatorProfile.user_id == user_id
            )
            if not profile:
                raise ValueError(
                    f"No CreatorProfile found for user_id={user_id}. "
                    f"Cannot sync Instagram stats."
                )
            resolved_profile_id = str(profile.id)

        # Run the sync
        service = InstagramService()
        try:
            updated_profile = await service.sync_creator_stats(
                user_id=user_id,
                creator_profile_id=resolved_profile_id,
            )
            return {
                "user_id": user_id,
                "profile_id": resolved_profile_id,
                "status": "success",
                "followers": updated_profile.instagram_followers,
                "engagement_rate": updated_profile.instagram_engagement_rate,
            }
        finally:
            await service.close()

    async def _sync_all(self) -> dict:
        """
        Async core logic: sync ALL active creators with connected Instagram.
        Called by the Beat-scheduled task (every 48h).

        Returns:
            Summary dict with counts of successes and failures
        """
        from app.core.database import db_manager
        from app.models.creator_profile import CreatorProfile
        from app.models.user import User
        from app.services.instagram_service import InstagramService

        await db_manager.connect()

        # Fetch all creators who have connected Instagram
        creators_with_ig = await User.find(
            User.instagram_access_token_encrypted != None  # noqa: E711
        ).to_list()

        success_count = 0
        failure_count = 0

        for user in creators_with_ig:
            try:
                result = await self._sync(str(user.id))
                if result["status"] == "success":
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as exc:
                logger.warning(
                    f"Batch sync failed for user_id={user.id}: {exc}"
                )
                failure_count += 1

        summary = {
            "total": len(creators_with_ig),
            "success": success_count,
            "failure": failure_count,
        }
        logger.info(f"Batch Instagram sync complete — {summary}")
        return summary


# ─────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────
instagram_sync_task = InstagramSyncTask()


# ─────────────────────────────────────────────────────────────
# Celery task registration
# ─────────────────────────────────────────────────────────────

@celery_app.task(
    name="tasks.instagram_sync.trigger_instagram_sync",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute before retry
)
def trigger_instagram_sync(
    self,
    user_id: str,
    creator_profile_id: Optional[str] = None,
) -> dict:
    """
    Celery task: sync Instagram stats for a single creator.

    Args:
        user_id: User._id of the creator
        creator_profile_id: Optional explicit profile ID

    Returns:
        Sync result summary dict

    Retries:
        Up to 3 times on failure, with 60s delay between retries
    """
    try:
        return instagram_sync_task.run(user_id, creator_profile_id)
    except Exception as exc:
        logger.error(f"trigger_instagram_sync failed (attempt {self.request.retries + 1}): {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="tasks.instagram_sync.trigger_instagram_sync_all",
    bind=True,
)
def trigger_instagram_sync_all(self) -> dict:
    """
    Celery Beat task: sync Instagram stats for ALL connected creators.
    Scheduled every 48 hours via beat_schedule in CeleryAppFactory.

    Returns:
        Summary dict with success/failure counts
    """
    try:
        return asyncio.run(instagram_sync_task._sync_all())
    except Exception as exc:
        logger.error(f"trigger_instagram_sync_all failed: {exc}")
        raise
