"""
Nexus — Custom Logger (Class-based)
------------------------------------------
Wraps Loguru with a class-based interface.

Features:
  - Structured log format with environment + module context
  - Separate log levels per environment (DEBUG in dev, INFO in prod)
  - JSON output in staging/production (structured log ingestion)
  - Human-readable coloured output in development
  - File rotation in production (7-day retention)

Usage:
    from app.core.logger import logger

    logger.info("User signed up", user_id="abc123")
    logger.error("Instagram sync failed", creator_id="xyz", exc_info=True)
"""

import sys
from pathlib import Path

from loguru import logger as _loguru_logger


class CollabLogger:
    """
    Custom logger class wrapping Loguru.

    Inherits Loguru's full interface via delegation while adding
    application-specific configuration and context binding.

    Environments:
      development — coloured, human-readable, DEBUG level
      staging     — JSON structured, INFO level
      production  — JSON structured, WARNING level, file rotation
    """

    def __init__(self) -> None:
        self._logger = _loguru_logger
        self._configured = False

    def configure(self, app_env: str, debug: bool = False) -> None:
        """
        Configure the logger for the given environment.
        Call once during application startup (before lifespan).

        Args:
            app_env: One of 'development', 'staging', 'production'
            debug: If True, force DEBUG level regardless of environment
        """
        if self._configured:
            return  # Idempotent — safe to call multiple times

        # Remove Loguru's default handler
        self._logger.remove()

        if app_env == "development":
            self._configure_development(debug=True)
        elif app_env == "staging":
            self._configure_staging()
        else:
            self._configure_production()

        self._configured = True
        self._logger.info(
            f"Logger configured [env={app_env}, debug={debug}]"
        )

    def _configure_development(self, debug: bool = True) -> None:
        """
        Development: coloured, human-readable output to stdout.
        Level: DEBUG — shows all logs including verbose query logs.
        """
        self._logger.add(
            sys.stdout,
            level="DEBUG" if debug else "INFO",
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
            backtrace=True,      # Full traceback on exceptions
            diagnose=True,       # Variable values in tracebacks
        )
        # Also write dev logs to a file for analysis
        log_path = Path("logs") / "dev.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger.add(
            str(log_path),
            level="DEBUG" if debug else "INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            colorize=False,
            backtrace=True,
            diagnose=True,
        )

    def _configure_staging(self) -> None:
        """
        Staging: JSON structured output to stdout.
        Railway / Grafana Loki picks this up for log aggregation.
        Level: INFO.
        """
        self._logger.add(
            sys.stdout,
            level="INFO",
            format="{message}",
            serialize=True,      # Output as JSON
            colorize=False,
            backtrace=True,
            diagnose=False,      # No variable values (may contain PII)
        )

    def _configure_production(self) -> None:
        """
        Production: JSON to stdout + rotating file.
        Level: INFO (WARNING for file sink — only record significant events).
        """
        # Stdout sink (Railway log drain / Grafana)
        self._logger.add(
            sys.stdout,
            level="INFO",
            format="{message}",
            serialize=True,
            colorize=False,
            backtrace=False,
            diagnose=False,
        )

        # File sink: ERROR+ only, 7-day retention, 10MB rotation
        log_path = Path("logs") / "nexus_{time:YYYY-MM-DD}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self._logger.add(
            str(log_path),
            level="ERROR",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            serialize=True,
            backtrace=True,
            diagnose=False,
        )

    # ─────────────────────────────────────────────────────────
    # Delegate all standard log methods to Loguru
    # ─────────────────────────────────────────────────────────

    def debug(self, message: str, **kwargs) -> None:  # type: ignore[override]
        self._logger.opt(depth=1).debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:  # type: ignore[override]
        self._logger.opt(depth=1).info(message, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        self._logger.opt(depth=1).success(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:  # type: ignore[override]
        self._logger.opt(depth=1).warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:  # type: ignore[override]
        self._logger.opt(depth=1).error(message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:  # type: ignore[override]
        self._logger.opt(depth=1).critical(message, **kwargs)

    def exception(self, message: str, **kwargs) -> None:  # type: ignore[override]
        """Log an error with the full exception traceback attached."""
        self._logger.opt(depth=1, exception=True).error(message, **kwargs)

    def bind(self, **kwargs):  # type: ignore[override]
        """Return a contextually-bound logger (e.g., per request, per user)."""
        return self._logger.bind(**kwargs)


# ─────────────────────────────────────────────────────────────
# Module-level singleton — import this everywhere
# ─────────────────────────────────────────────────────────────
logger = CollabLogger()
