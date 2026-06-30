"""
Nexus — Application Configuration
----------------------------------------
All configuration is driven by environment variables, loaded from the .env file.
The APP_ENV variable controls which behaviours are active per environment.

Usage:
    from app.config import settings
    print(settings.MONGODB_URL)
"""

from enum import Enum
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """The three deployment environments.

    - DEVELOPMENT: Local machine, Docker Compose, hot-reload, mocks enabled.
    - STAGING: Railway staging project, MongoDB Atlas dev cluster, test API keys.
    - PRODUCTION: Railway production project, Atlas M10+, live API keys, strict settings.
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Central settings object. All values are read from environment variables.
    Pydantic-settings automatically reads .env file and validates types.

    Priority (highest → lowest):
        1. Actual environment variables (injected by Railway / Docker)
        2. .env file in the working directory
        3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unknown env vars gracefully
    )

    # ─────────────────────────────────────────────────────────
    # Core Application
    # ─────────────────────────────────────────────────────────
    APP_ENV: Environment = Environment.DEVELOPMENT
    APP_NAME: str = "Nexus"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ─────────────────────────────────────────────────────────
    # Database — MongoDB
    # ─────────────────────────────────────────────────────────
    MONGODB_URL: str
    MONGODB_DB_NAME: str = "nexus_dev"

    # ─────────────────────────────────────────────────────────
    # Cache + Sessions — Redis
    # ─────────────────────────────────────────────────────────
    REDIS_URL: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # ─────────────────────────────────────────────────────────
    # JWT Authentication
    # ─────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ─────────────────────────────────────────────────────────
    # Google OAuth 2.0
    # ─────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str

    # ─────────────────────────────────────────────────────────
    # Instagram Graph API (Meta)
    # ─────────────────────────────────────────────────────────
    INSTAGRAM_APP_ID: str
    INSTAGRAM_APP_SECRET: str
    INSTAGRAM_REDIRECT_URI: str

    # ─────────────────────────────────────────────────────────
    # Frontend + CORS
    # ─────────────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:3000"

    # ─────────────────────────────────────────────────────────
    # Encryption (for storing Instagram access tokens)
    # ─────────────────────────────────────────────────────────
    ENCRYPTION_KEY: str

    # ─────────────────────────────────────────────────────────
    # File Storage — Cloudflare R2 (S3-compatible)
    # ─────────────────────────────────────────────────────────
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "nexus-dev"
    R2_PUBLIC_URL: str = ""

    # ─────────────────────────────────────────────────────────
    # Email — SMTP
    # ─────────────────────────────────────────────────────────
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "noreply@nexus.in"
    FROM_NAME: str = "Nexus"

    # ─────────────────────────────────────────────────────────
    # Error Tracking — Sentry
    # ─────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ─────────────────────────────────────────────────────────
    # Rate Limiting
    # ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_WHITELIST: str = "127.0.0.1,localhost"

    # ─────────────────────────────────────────────────────────
    # Computed Properties (derived from other settings)
    # ─────────────────────────────────────────────────────────

    @property
    def is_development(self) -> bool:
        """True when running locally in Docker Compose."""
        return self.APP_ENV == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        """True when deployed to the staging Railway project."""
        return self.APP_ENV == Environment.STAGING

    @property
    def is_production(self) -> bool:
        """True when deployed to the production Railway project."""
        return self.APP_ENV == Environment.PRODUCTION

    @property
    def allowed_origins(self) -> List[str]:
        """CORS allowed origins — strict in production, lenient in development."""
        if self.is_development:
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:8000",  # Swagger UI
            ]
        elif self.is_staging:
            return [
                self.FRONTEND_URL,
                "https://nexus-staging.vercel.app",
                "https://*.vercel.app",  # Vercel preview deployments
            ]
        else:
            # Production: only the real domain
            return [self.FRONTEND_URL]

    @property
    def sentry_enabled(self) -> bool:
        """Sentry is only active in staging and production."""
        return bool(self.SENTRY_DSN) and not self.is_development

    @property
    def email_enabled(self) -> bool:
        """Email sending only when SMTP server and credentials are configured."""
        return bool(self.SMTP_SERVER and self.SMTP_USERNAME and self.SMTP_PASSWORD)

    @property
    def r2_enabled(self) -> bool:
        """R2 file storage only when credentials are configured."""
        return bool(self.R2_ACCESS_KEY_ID and self.R2_SECRET_ACCESS_KEY)

    @property
    def instagram_auth_url(self) -> str:
        """Build the Instagram OAuth authorization URL."""
        return (
            "https://www.instagram.com/oauth/authorize"
            f"?client_id={self.INSTAGRAM_APP_ID}"
            f"&redirect_uri={self.INSTAGRAM_REDIRECT_URI}"
            "&scope=instagram_business_basic,instagram_business_manage_messages,instagram_business_manage_comments,instagram_business_content_publish,instagram_business_manage_insights"
            "&response_type=code"
            "&force_reauth=true"
        )

    @property
    def google_auth_url(self) -> str:
        """Build the Google OAuth authorization URL."""
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={self.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={self.GOOGLE_REDIRECT_URI}"
            "&response_type=code"
            "&scope=openid email profile"
            "&access_type=offline"
            "&prompt=select_account"
        )


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    Uses @lru_cache so the .env file is parsed exactly once on startup.
    FastAPI dependency injection: Depends(get_settings)
    """
    return Settings()


# Module-level singleton — import this directly in most cases
settings = get_settings()
