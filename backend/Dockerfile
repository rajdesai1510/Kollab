# ─────────────────────────────────────────
# Multi-stage Dockerfile for FastAPI backend
#
# Stages:
#   base        — shared Python + deps
#   development — local dev with hot-reload
#   production  — lean production image
# ─────────────────────────────────────────

# ── Stage 1: Base ──────────────────────────────────────────
FROM python:3.12-slim AS base

# Set working directory
WORKDIR /app

# Prevent Python from writing .pyc files / enable output buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (build tools for cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (layer caching — only re-installs on requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Development ───────────────────────────────────
FROM base AS development

# Install dev-only tools
RUN pip install --no-cache-dir watchfiles

# Source mounted at runtime via docker-compose volume (./backend:/app)
# Command set in docker-compose.yml: uvicorn ... --reload

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ── Stage 3: Production ────────────────────────────────────
FROM base AS production

# Copy application source
COPY . .

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

# Production: multiple workers, no reload
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--loop", "uvloop", \
     "--http", "httptools"]
