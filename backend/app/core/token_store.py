"""
Nexus — Token Store (Redis-backed Refresh Token Registry)
-----------------------------------------------------------
Manages refresh token storage and validation in Redis.

Why Redis?
  - Enables true token revocation (logout invalidates the token server-side)
  - Token rotation: old refresh token is deleted the moment a new one is issued
  - Automatic expiry via Redis TTL — no manual cleanup needed
  - Scales horizontally: all API instances share the same token state

Key schema:
    rt:<user_id>:<jti>  →  "1"   (TTL = refresh token lifetime)

Lookup strategy:
  - On refresh: decode JWT → extract user_id + jti → check Redis key exists
  - On logout:  delete all rt:<user_id>:* keys (revoke all sessions)

Usage:
    from app.core.token_store import token_store
    await token_store.save_refresh_token(user_id, jti, ttl_seconds)
    exists = await token_store.is_refresh_token_valid(user_id, jti)
    await token_store.revoke_refresh_token(user_id, jti)
    await token_store.revoke_all_refresh_tokens(user_id)
"""

from app.core.database import db_manager
from app.core.logger import logger


class TokenStore:
    """
    Redis-backed store for refresh token lifecycle management.

    Keys are namespaced as:  rt:<user_id>:<jti>
    TTL is set to the refresh token's remaining lifetime in seconds.
    """

    KEY_PREFIX = "rt"

    def _key(self, user_id: str, jti: str) -> str:
        """Build the Redis key for a specific refresh token."""
        return f"{self.KEY_PREFIX}:{user_id}:{jti}"

    def _pattern(self, user_id: str) -> str:
        """Build a glob pattern to match all refresh tokens for a user."""
        return f"{self.KEY_PREFIX}:{user_id}:*"

    async def save_refresh_token(
        self,
        user_id: str,
        jti: str,
        ttl_seconds: int,
    ) -> None:
        """
        Store a new refresh token in Redis with an expiry TTL.

        Args:
            user_id:     MongoDB ObjectId string of the user
            jti:         JWT ID claim — unique identifier for this token
            ttl_seconds: Seconds until the token expires (matches JWT exp)
        """
        key = self._key(user_id, jti)
        redis = db_manager.redis
        await redis.set(key, "1", ex=ttl_seconds)
        logger.debug(f"[token_store] Saved refresh token — user={user_id}, jti={jti}, ttl={ttl_seconds}s")

    async def is_refresh_token_valid(self, user_id: str, jti: str) -> bool:
        """
        Check whether a refresh token is still valid (exists in Redis).

        Returns False if the token has expired, been revoked, or never existed.

        Args:
            user_id: MongoDB ObjectId string of the user
            jti:     JWT ID claim from the incoming refresh token

        Returns:
            True if the token is valid, False otherwise
        """
        key = self._key(user_id, jti)
        redis = db_manager.redis
        exists = await redis.exists(key)
        return bool(exists)

    async def revoke_refresh_token(self, user_id: str, jti: str) -> None:
        """
        Revoke a single refresh token (used during token rotation).

        Called when a new token pair is issued — the old refresh token
        is immediately deleted so it cannot be reused.

        Args:
            user_id: MongoDB ObjectId string of the user
            jti:     JWT ID claim of the token to revoke
        """
        key = self._key(user_id, jti)
        redis = db_manager.redis
        deleted = await redis.delete(key)
        if deleted:
            logger.debug(f"[token_store] Revoked refresh token — user={user_id}, jti={jti}")
        else:
            logger.warning(f"[token_store] Tried to revoke non-existent token — user={user_id}, jti={jti}")

    async def revoke_all_refresh_tokens(self, user_id: str) -> int:
        """
        Revoke ALL refresh tokens for a user (called on logout).

        Uses SCAN to find all matching keys safely (avoids KEYS blocking).

        Args:
            user_id: MongoDB ObjectId string of the user

        Returns:
            Number of tokens revoked
        """
        pattern = self._pattern(user_id)
        redis = db_manager.redis

        revoked = 0
        async for key in redis.scan_iter(match=pattern, count=100):
            await redis.delete(key)
            revoked += 1

        if revoked > 0:
            logger.info(f"[token_store] Revoked {revoked} refresh token(s) — user={user_id}")
        else:
            logger.debug(f"[token_store] No refresh tokens to revoke — user={user_id}")

        return revoked


# Module-level singleton — import this in auth router and JWT manager
token_store = TokenStore()
