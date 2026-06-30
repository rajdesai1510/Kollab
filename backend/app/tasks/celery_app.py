"""
Nexus — Celery Application Factory (Class-based)
-------------------------------------------------------
CeleryAppFactory creates and configures the Celery application instance.

All task modules import `celery_app` from here:
    from app.tasks.celery_app import celery_app

The factory is separate from the tasks to avoid circular imports
(task modules need celery_app; celery_app must not import task modules).

Configuration:
    - Broker:  Redis DB 1 (CELERY_BROKER_URL)
    - Backend: Redis DB 2 (CELERY_RESULT_BACKEND)
    - Tasks auto-discovered from app.tasks.*

Usage:
    celery_factory = CeleryAppFactory()
    celery_app = celery_factory.app
"""

from celery import Celery

from app.config import settings


class CeleryAppFactory:
    """
    Encapsulates Celery application creation and configuration.

    Creates a single Celery app instance (singleton via the module-level
    `celery_app` export) and applies all project-specific settings.

    Methods:
        create()  — build and configure the Celery app
        app       — property returning the cached Celery instance
    """

    def __init__(self) -> None:
        self._app: Celery | None = None

    def create(self) -> Celery:
        """
        Build and configure the Celery application.

        Returns:
            Configured Celery instance
        """
        app = Celery(
            "nexus",
            broker=settings.CELERY_BROKER_URL,
            backend=settings.CELERY_RESULT_BACKEND,
            include=[
                "app.tasks.instagram_sync",
            ],
        )

        app.conf.update(
            # Serialization
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            # Timezone
            timezone="Asia/Kolkata",
            enable_utc=True,
            # Task behavior
            task_acks_late=True,          # Acknowledge after task completes (safer)
            task_reject_on_worker_lost=True,
            task_track_started=True,
            task_always_eager=False,
            # Result TTL: keep results for 1 hour
            result_expires=3600,
            # Worker concurrency (override via docker-compose command)
            worker_prefetch_multiplier=1,  # Fair task distribution
            # Beat schedule — Instagram stat refresh every 48 hours
            beat_schedule={
                "refresh-instagram-stats-48h": {
                    "task": "tasks.instagram_sync.trigger_instagram_sync_all",
                    "schedule": 48 * 60 * 60,  # 48 hours in seconds
                },
            },
        )

        return app

    @property
    def app(self) -> Celery:
        """Lazy-initialized Celery app instance (created once on first access)."""
        if self._app is None:
            self._app = self.create()
        return self._app


# ─────────────────────────────────────────────────────────────
# Module-level singleton — import this in all task modules
# ─────────────────────────────────────────────────────────────
celery_factory = CeleryAppFactory()
celery_app = celery_factory.app
