"""
Nexus — MongoDB + Redis Database Connections
--------------------------------------------------
Initialises async connections to:
- MongoDB Atlas (via Motor + Beanie ODM)
- Redis (via redis-py async client)

Both connections are initialised once on app startup via FastAPI lifespan events
and torn down cleanly on shutdown.
"""

import redis.asyncio as aioredis
from beanie import init_beanie
from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.models.brand_profile import BrandProfile
from app.models.campaign import Campaign
from app.models.connection import Connection
from app.models.message import Message
from app.models.notification import Notification
from app.models.creator_profile import CreatorProfile
from app.models.user import User

# ─────────────────────────────────────────────────────────────
# Global client references (set during lifespan startup)
# ─────────────────────────────────────────────────────────────
_mongo_client: AsyncIOMotorClient | None = None
_redis_client: aioredis.Redis | None = None


async def connect_to_mongodb() -> None:
    """
    Create the MongoDB Motor client and initialise Beanie ODM.

    Beanie requires all document models to be registered here so it can
    set up their collections, indexes, and validators against the database.
    """
    global _mongo_client

    logger.info(f"Connecting to MongoDB ({settings.APP_ENV.value})...")

    _mongo_client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,  # Fail fast if Atlas is unreachable
        maxPoolSize=10,
        minPoolSize=1,
    )

    # Register all Beanie document models here.
    # The order matters for models with cross-references.
    await init_beanie(
        database=_mongo_client[settings.MONGODB_DB_NAME],
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
        f"MongoDB connected. DB: {settings.MONGODB_DB_NAME}"
    )


async def disconnect_from_mongodb() -> None:
    """Close the MongoDB Motor connection pool cleanly on app shutdown."""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        logger.info("MongoDB connection closed.")


async def connect_to_redis() -> None:
    """
    Create the async Redis client.

    In development, this connects to the local Docker Redis.
    In staging/production, this connects to Upstash Redis via TLS.
    """
    global _redis_client

    logger.info(f"Connecting to Redis ({settings.APP_ENV.value})...")

    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        max_connections=20,
    )

    # Ping to verify connection
    await _redis_client.ping()
    logger.success("Redis connected.")


async def disconnect_from_redis() -> None:
    """Close the Redis connection pool cleanly on app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        logger.info("Redis connection closed.")


def get_redis() -> aioredis.Redis:
    """
    Return the active Redis client.

    FastAPI dependency: use as Depends(get_redis) in route handlers
    that need direct Redis access (e.g. rate limiting, session lookup).
    """
    if _redis_client is None:
        raise RuntimeError(
            "Redis client is not initialised. "
            "Ensure connect_to_redis() was called during app startup."
        )
    return _redis_client
