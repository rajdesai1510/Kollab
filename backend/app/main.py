"""
Nexus — FastAPI Application Entry Point
----------------------------------------------
Creates and configures the FastAPI application instance.

Responsibilities:
  - Create the FastAPI app with metadata (title, version, docs URL)
  - Register all API routers under /api
  - Configure CORS (environment-aware allowed origins)
  - Set up startup/shutdown lifecycle via DatabaseManager (MongoDB + Redis)
  - Configure Sentry error tracking (staging + production only)
  - Configure CollabLogger (Loguru) before startup
  - Mount the health check endpoint

Class-based architecture:
  All imports use module-level singleton instances from each router/core module.
  No legacy module-level function imports (old app/database.py is no longer used here).
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.database import db_manager
from app.core.logger import logger
from app.routers.admin import admin_router
from app.routers.auth import auth_router
from app.routers.brands import brand_router
from app.routers.campaigns import campaign_router
from app.routers.connections import connection_router
from app.routers.creators import creator_router
from app.routers.messages import message_router
from app.routers.notifications import notification_router


# ─────────────────────────────────────────────────────────────
# Logger Configuration
# ─────────────────────────────────────────────────────────────
# Configure CollabLogger before anything else runs
logger.configure(app_env=settings.APP_ENV.value)


# ─────────────────────────────────────────────────────────────
# Sentry Setup (staging + production only)
# ─────────────────────────────────────────────────────────────
if settings.sentry_enabled:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV.value,
        traces_sample_rate=0.1 if settings.is_production else 1.0,
        send_default_pii=False,
    )
    logger.info(f"Sentry enabled for environment: {settings.APP_ENV.value}")


# ─────────────────────────────────────────────────────────────
# Application Lifespan (startup + shutdown)
# ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.
    Code before `yield` runs on startup; code after `yield` runs on shutdown.

    Startup:
        1. Connect to MongoDB Atlas (Motor async client + Beanie ODM init)
        2. Connect to Redis (async client + ping verification)

    Shutdown:
        1. Close MongoDB connection pool
        2. Close Redis connection pool

    Uses DatabaseManager (db_manager) — the class-based core singleton.
    """
    logger.info(
        f"Starting Nexus API "
        f"[env={settings.APP_ENV.value}, version={settings.APP_VERSION}]"
    )

    # Startup — delegate to DatabaseManager
    await db_manager.connect()

    logger.success("All services connected. Nexus API is ready.")

    yield  # Application serves requests here

    # Shutdown — delegate to DatabaseManager
    logger.info("Shutting down Nexus API...")
    await db_manager.disconnect()
    logger.info("Nexus API shut down cleanly.")


# ─────────────────────────────────────────────────────────────
# FastAPI App Factory
# ─────────────────────────────────────────────────────────────
def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Separating app creation into a factory function makes it easy to create
    test instances with overridden settings without affecting the real app.

    Router imports use class-based singleton instances:
        auth_router.router, creator_router.router, etc.
    """
    # Disable Swagger / ReDoc in production for security
    docs_url = "/docs" if not settings.is_production else None
    redoc_url = "/redoc" if not settings.is_production else None
    openapi_url = "/openapi.json" if not settings.is_production else None

    application = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "Creator-brand matchmaking platform API. "
            "Connects Indian micro-influencers with local D2C brands."
        ),
        version=settings.APP_VERSION,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
    )

    # ── CORS Middleware ───────────────────────────────────────
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )
    
    # ── Rate Limit Middleware ─────────────────────────────────
    from app.middleware.rate_limit_middleware import rate_limit_middleware
    from starlette.middleware.base import BaseHTTPMiddleware
    application.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

    # ── API Routers ───────────────────────────────────────────
    # All routes are prefixed with /api — versioning via branch/deployment.
    # Each router is a class-based singleton: XxxRouter().router
    API_PREFIX = "/api"

    application.include_router(
        auth_router.router, prefix=f"{API_PREFIX}/auth", tags=["Auth"]
    )
    application.include_router(
        creator_router.router, prefix=f"{API_PREFIX}/creators", tags=["Creators"]
    )
    application.include_router(
        brand_router.router, prefix=f"{API_PREFIX}/brands", tags=["Brands"]
    )
    application.include_router(
        campaign_router.router, prefix=f"{API_PREFIX}/campaigns", tags=["Campaigns"]
    )
    application.include_router(
        connection_router.router, prefix=f"{API_PREFIX}/connections", tags=["Connections"]
    )
    application.include_router(
        message_router.router, prefix=f"{API_PREFIX}/messages", tags=["Messages"]
    )
    application.include_router(
        notification_router.router, prefix=f"{API_PREFIX}/notifications", tags=["Notifications"]
    )
    application.include_router(
        admin_router.router, prefix=f"{API_PREFIX}/admin", tags=["Admin"]
    )

    return application


# ─────────────────────────────────────────────────────────────
# Application Instance
# ─────────────────────────────────────────────────────────────
app = create_application()


# ─────────────────────────────────────────────────────────────
# Health Check (always public — used by Railway and Docker HEALTHCHECK)
# ─────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"], include_in_schema=False)
async def health_check() -> dict:
    """
    Basic health check endpoint.
    Returns 200 OK when the API is up and running.
    Used by Railway health checks and Docker HEALTHCHECK instruction.
    """
    return {
        "status": "ok",
        "environment": settings.APP_ENV.value,
        "version": settings.APP_VERSION,
        "app": settings.APP_NAME,
    }
