"""
Nexus — Database Manager (Class-based)
---------------------------------------------
Wraps MongoDB (Motor + Beanie) and Redis connections in a single
`DatabaseManager` class. One instance is created at startup and
held for the application lifetime.

Usage:
    from app.core.database import db_manager

    # In lifespan:
    await db_manager.connect()
    await db_manager.disconnect()

    # In route handlers / services:
    redis = db_manager.redis
"""

import redis.asyncio as aioredis
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.core.logger import logger


class DatabaseManager:
    """
    Manages async connections to MongoDB Atlas and Redis.

    Lifecycle:
        connect()    → call once during FastAPI lifespan startup
        disconnect() → call once during FastAPI lifespan shutdown

    The instance exposes:
        self.mongo_client   — raw Motor client (rarely needed directly)
        self.db             — the active Motor database (for raw queries)
        self.redis          — async Redis client (for cache / session ops)
    """

    def __init__(self) -> None:
        self._mongo_client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None
        self._redis: aioredis.Redis | None = None

    # ─────────────────────────────────────────────────────────
    # MongoDB
    # ─────────────────────────────────────────────────────────

    async def connect_mongo(self) -> None:
        """
        Create the Motor client and initialise Beanie ODM.

        All Beanie Document models must be registered here.
        Beanie creates TTL indexes, validates schemas, and sets
        up collection-level settings on the target database.
        """
        # Import models here to avoid circular imports
        from app.models.brand_profile import BrandProfile
        from app.models.campaign import Campaign
        from app.models.connection import Connection
        from app.models.creator_profile import CreatorProfile
        from app.models.message import Message
        from app.models.notification import Notification
        from app.models.user import User

        logger.info(
            f"Connecting to MongoDB "
            f"[env={settings.APP_ENV.value}, db={settings.MONGODB_DB_NAME}]"
        )

        self._mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5_000,
            maxPoolSize=10,
            minPoolSize=1,
        )

        self._db = self._mongo_client[settings.MONGODB_DB_NAME]

        await init_beanie(
            database=self._db,
            document_models=[
                User,
                CreatorProfile,
                BrandProfile,
                Campaign,
                Connection,
                Message,
                Notification,
            ],
        )

        logger.success(
            f"MongoDB connected — database: '{settings.MONGODB_DB_NAME}'"
        )

    async def disconnect_mongo(self) -> None:
        """Close the Motor connection pool cleanly."""
        if self._mongo_client:
            self._mongo_client.close()
            logger.info("MongoDB connection closed.")

    @property
    def mongo_client(self) -> AsyncIOMotorClient:
        """Raw Motor client. Use `db` for most operations."""
        if self._mongo_client is None:
            raise RuntimeError("MongoDB is not connected. Call connect_mongo() first.")
        return self._mongo_client

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Active Motor database instance."""
        if self._db is None:
            raise RuntimeError("MongoDB is not connected. Call connect_mongo() first.")
        return self._db

    # ─────────────────────────────────────────────────────────
    # Redis
    # ─────────────────────────────────────────────────────────

    async def connect_redis(self) -> None:
        """
        Create the async Redis client and verify connectivity via PING.

        Dev: connects to local Docker Redis.
        Staging/Prod: connects to Upstash Redis via TLS (rediss://).
        """
        logger.info(
            f"Connecting to Redis [env={settings.APP_ENV.value}]"
        )

        self._redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            max_connections=20,
        )

        await self._redis.ping()
        logger.success("Redis connected.")

    async def disconnect_redis(self) -> None:
        """Close the Redis connection pool cleanly."""
        if self._redis:
            await self._redis.aclose()
            logger.info("Redis connection closed.")

    @property
    def redis(self) -> aioredis.Redis:
        """
        Active async Redis client.

        Use for:
          - Session token storage / lookup
          - Rate limiting counters
          - Short-lived cache (creator search results, etc.)
        """
        if self._redis is None:
            raise RuntimeError("Redis is not connected. Call connect_redis() first.")
        return self._redis

    # ─────────────────────────────────────────────────────────
    # Lifecycle helpers
    # ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect to all datastores. Called once in FastAPI lifespan startup."""
        await self.connect_mongo()
        await self.connect_redis()

    async def disconnect(self) -> None:
        """Disconnect from all datastores. Called once in FastAPI lifespan shutdown."""
        await self.disconnect_mongo()
        await self.disconnect_redis()

    # ─────────────────────────────────────────────────────────
    # Health Check
    # ─────────────────────────────────────────────────────────

    async def health(self) -> dict:
        """
        Ping both datastores and return health status.
        Used by the /api/health endpoint.
        """
        mongo_ok = False
        redis_ok = False

        try:
            await self.mongo_client.admin.command("ping")
            mongo_ok = True
        except Exception:
            logger.warning("MongoDB health check failed.")

        try:
            await self.redis.ping()
            redis_ok = True
        except Exception:
            logger.warning("Redis health check failed.")

        return {
            "mongodb": "ok" if mongo_ok else "error",
            "redis": "ok" if redis_ok else "error",
        }


# ─────────────────────────────────────────────────────────────
# Module-level singleton
# Import this in lifespan, routers, and services.
# ─────────────────────────────────────────────────────────────
db_manager = DatabaseManager()
