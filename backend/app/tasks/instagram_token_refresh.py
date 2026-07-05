"""
Nexus — Instagram Token Refresh Task
-----------------------------------------
Celery beat task that runs daily to automatically refresh Instagram
long-lived access tokens before they expire.

Instagram long-lived tokens:
  - Valid for 60 days from issue
  - Refreshable if they have NOT yet expired (can be refreshed any time after 24h)
  - Once expired they CANNOT be refreshed — user must re-authorize

Strategy:
  - Runs daily via Celery beat
  - Targets users whose token expires within the next 7 days
  - On success: updates token + new expiry in MongoDB
  - On failure (already expired): clears token fields so UI shows "reconnect"

Usage:
    from app.tasks.instagram_token_refresh import refresh_expiring_instagram_tokens
    refresh_expiring_instagram_tokens.delay()  # manual trigger
    # Automatically triggered by Celery beat (see celery_app.py)
"""

import asyncio
from datetime import datetime, timezone, timedelta

from app.tasks.celery_app import celery_app
from app.core.logger import logger


@celery_app.task(
    name="tasks.instagram_token_refresh.refresh_expiring_instagram_tokens",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def refresh_expiring_instagram_tokens(self) -> dict:
    """
    Celery task: refresh Instagram long-lived tokens expiring within 7 days.

    Runs daily via Celery beat. Queries all users with:
      - instagram_access_token_encrypted is set
      - instagram_token_expires_at within the next 7 days (or no expiry stored)

    Returns:
        dict with counts of refreshed, skipped, and failed users.
    """
    return asyncio.get_event_loop().run_until_complete(_do_refresh())


async def _do_refresh() -> dict:
    """Async implementation of the token refresh sweep."""
    from app.models.user import User
    from app.services.auth_service import AuthService, OAuthError
    from app.core.encryption import encryption_manager
    from beanie.operators import Exists, LTE

    auth_service = AuthService()
    now = datetime.now(tz=timezone.utc)
    refresh_window = now + timedelta(days=7)

    stats = {"refreshed": 0, "skipped": 0, "failed": 0, "cleared": 0}

    try:
        # Find all users with an Instagram token stored
        users = await User.find(
            Exists(User.instagram_access_token_encrypted, True),
        ).to_list()

        logger.info(
            f"[token_refresh] Starting sweep — {len(users)} users with Instagram connected"
        )

        for user in users:
            if not user.instagram_access_token_encrypted:
                continue

            # Check expiry: if expiry is unknown or within 7 days, attempt refresh
            if user.instagram_token_expires_at is not None:
                expires_at = user.instagram_token_expires_at
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)

                # Already expired — cannot refresh, must reconnect
                if expires_at <= now:
                    logger.warning(
                        f"[token_refresh] Token EXPIRED for user={user.id} "
                        f"(expired at {expires_at.isoformat()}) — clearing token"
                    )
                    user.instagram_access_token_encrypted = None
                    user.instagram_token_expires_at = None
                    # Keep instagram_user_id so we know they were connected before
                    await user.save()
                    stats["cleared"] += 1
                    continue

                # More than 7 days remaining — skip
                if expires_at > refresh_window:
                    stats["skipped"] += 1
                    continue

            # Attempt refresh
            try:
                updated = await auth_service.refresh_instagram_token(user)
                if updated:
                    stats["refreshed"] += 1
                    logger.info(
                        f"[token_refresh] Refreshed token for user={user.id}, "
                        f"new_expiry={updated.instagram_token_expires_at}"
                    )
                else:
                    stats["skipped"] += 1
            except OAuthError as e:
                logger.error(
                    f"[token_refresh] OAuthError refreshing token for user={user.id}: {e}"
                )
                stats["failed"] += 1
            except Exception as e:
                logger.error(
                    f"[token_refresh] Unexpected error for user={user.id}: {e}"
                )
                stats["failed"] += 1

    except Exception as e:
        logger.error(f"[token_refresh] Sweep failed with unexpected error: {e}")
        raise
    finally:
        await auth_service.close()

    logger.info(
        f"[token_refresh] Sweep complete — "
        f"refreshed={stats['refreshed']}, skipped={stats['skipped']}, "
        f"failed={stats['failed']}, cleared={stats['cleared']}"
    )
    return stats
