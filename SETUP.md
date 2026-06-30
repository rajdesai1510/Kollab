# Nexus — Project Setup Guide

Complete, step-by-step instructions for setting up the **Nexus** backend in any environment.

**Package manager:** [`uv`](https://docs.astral.sh/uv/) — the fast Rust-based Python package and project manager  
**Code quality:** [`ruff`](https://docs.astral.sh/ruff/) (lint + format), [`mypy`](https://mypy.readthedocs.io/) (type-check), [`black`](https://black.readthedocs.io/) (format)

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Setup](#2-repository-setup)
3. [Python Environment — `uv`](#3-python-environment--uv)
4. [Environment Variables](#4-environment-variables)
5. [Generate Secrets](#5-generate-secrets)
6. [External Services Setup](#6-external-services-setup)
7. [Local Development — Docker Compose](#7-local-development--docker-compose)
8. [Local Development — Bare Metal (no Docker)](#8-local-development--bare-metal-no-docker)
9. [Code Quality Toolchain](#9-code-quality-toolchain)
10. [Running Tests](#10-running-tests)
11. [Staging Deployment — Railway](#11-staging-deployment--railway)
12. [Production Deployment — Railway](#12-production-deployment--railway)
13. [Common Commands Reference](#13-common-commands-reference)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Prerequisites

Install these tools before anything else.

### Required

| Tool | Version | Install |
|------|---------|---------|
| **Python** | ≥ 3.12 | [python.org/downloads](https://www.python.org/downloads/) |
| **uv** | latest | See below |
| **Docker Desktop** | latest | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| **Git** | ≥ 2.40 | [git-scm.com](https://git-scm.com/) |

### Install `uv`

`uv` is the **only** package manager used in this project. Do **not** use `pip` directly for managing project dependencies.

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify install:**
```bash
uv --version
# uv 0.x.x (...)
```

> **Why `uv`?** Up to 100× faster than pip for dependency resolution, built-in virtual environment management, lock files, and a single binary with zero dependencies.

---

## 2. Repository Setup

```bash
# Clone the repository
git clone https://github.com/your-org/nexus.git
cd nexus

# Project structure
nexus/
├── backend/           ← FastAPI backend (this guide covers this)
│   ├── app/           ← Application source code
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── SETUP.md           ← You are here
```

---

## 3. Python Environment — `uv`

All Python commands are run from the `backend/` directory.

```bash
cd backend
```

### 3.1 — Create a Virtual Environment

```bash
uv venv --python 3.12
```

This creates a `.venv/` directory inside `backend/`.

**Activate the environment:**

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat
```

Verify Python is from the venv:
```bash
python --version
# Python 3.12.x

which python   # macOS/Linux → /path/to/backend/.venv/bin/python
where python   # Windows → \path\to\backend\.venv\Scripts\python.exe
```

### 3.2 — Install Dependencies

```bash
# Install all dependencies from requirements.txt
uv pip install -r requirements.txt
```

### 3.3 — Install Code Quality Tools

```bash
# Install dev/quality tools (ruff, black, mypy — already in requirements.txt)
uv pip install ruff black mypy
```

> These are already listed in `requirements.txt` under `# Code Quality`. The command above is a no-op if you already ran `uv pip install -r requirements.txt`.

### 3.4 — Sync After Pulling Changes

Whenever `requirements.txt` changes (after a `git pull`):

```bash
uv pip sync requirements.txt
```

> `uv pip sync` is stricter than `install` — it removes packages **not** in requirements.txt and installs missing ones. Use it to keep your environment clean.

### 3.5 — Add a New Dependency

```bash
# Install and immediately add to requirements.txt
uv pip install some-package
uv pip freeze | grep some-package >> requirements.txt
```

Or add the pinned line to `requirements.txt` manually, then sync:
```bash
# requirements.txt
some-package==1.2.3

# Sync environment
uv pip sync requirements.txt
```

---

## 4. Environment Variables

The app uses **per-environment `.env` files**. The config system reads from the file matching the current environment.

### 4.1 — Create Your `.env` File

```bash
cd backend

# Copy the example template
cp .env.example .env.development    # For local development
cp .env.example .env.staging        # For staging (fill in real values)
cp .env.example .env.production     # For production (fill in real values)
```

> **Never commit `.env.development`, `.env.staging`, or `.env.production` to Git.**  
> They are already in `.gitignore`.

### 4.2 — Environment Files by Context

| File | Used by | Contains |
|------|---------|---------|
| `.env.example` | Template only | Placeholder values |
| `.env.development` | Docker Compose + local dev | Local URLs, dummy secrets |
| `.env.staging` | Railway staging | Real Atlas/Upstash URLs, staging API keys |
| `.env.production` | Railway production | Production secrets, live API keys |

### 4.3 — Full Variable Reference

Below is every variable with its purpose, default, and where to get it.

```ini
# ─── Application ──────────────────────────────────────────────
APP_ENV=development           # Options: development | staging | production
APP_NAME=Nexus
DEBUG=true                    # Set false in staging/production

# ─── MongoDB ──────────────────────────────────────────────────
# Development (local Docker — matches docker-compose.yml):
MONGODB_URL=mongodb://admin:local_dev_password@localhost:27017/nexus_dev?authSource=admin

# Staging / Production (MongoDB Atlas):
# MONGODB_URL=mongodb+srv://<user>:<password>@cluster.mongodb.net/nexus_staging?retryWrites=true&w=majority

MONGODB_DB_NAME=nexus_dev  # Change per environment

# ─── Redis ────────────────────────────────────────────────────
# Development (local Docker):
REDIS_URL=redis://:local_redis_password@localhost:6379/0

# Staging / Production (Upstash):
# REDIS_URL=rediss://:<password>@<host>.upstash.io:6379

CELERY_BROKER_URL=redis://:local_redis_password@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:local_redis_password@localhost:6379/2

# ─── JWT ──────────────────────────────────────────────────────
JWT_SECRET_KEY=<generate — see Section 5>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# ─── Google OAuth 2.0 ─────────────────────────────────────────
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# ─── Instagram / Meta ─────────────────────────────────────────
INSTAGRAM_APP_ID=<from Meta Developer Portal>
INSTAGRAM_APP_SECRET=<from Meta Developer Portal>
INSTAGRAM_REDIRECT_URI=http://localhost:8000/api/auth/instagram/callback

# ─── Frontend / CORS ──────────────────────────────────────────
FRONTEND_URL=http://localhost:3000

# ─── Encryption ───────────────────────────────────────────────
ENCRYPTION_KEY=<generate — see Section 5>

# ─── Cloudflare R2 (optional in development) ──────────────────
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=nexus-dev
R2_PUBLIC_URL=

# ─── Resend Email (optional in development) ───────────────────
RESEND_API_KEY=
FROM_EMAIL=noreply@nexus.in
FROM_NAME=Nexus

# ─── Sentry (disabled in development when empty) ──────────────
SENTRY_DSN=

# ─── Rate Limiting ────────────────────────────────────────────
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_AUTH_PER_MINUTE=10
```

---

## 5. Generate Secrets

Run these **once** per environment and paste the output into your `.env` file.

### JWT Secret Key

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Example output: `Kx9mP2vQr8nT4wYjLbZ0sHdFgAeU6cXoI1qM3kVy7pN5hCwRlJtBuEiOaDnSfZ`

Paste as: `JWT_SECRET_KEY=<output>`

### Fernet Encryption Key (for Instagram token storage)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Example output: `abc123...` (44-character base64 string)

Paste as: `ENCRYPTION_KEY=<output>`

> **Critical:** Use a **different** key per environment. Losing the production encryption key means all stored Instagram tokens become unreadable.

---

## 6. External Services Setup

### 6.1 — Google OAuth 2.0

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. **New Project** → Name: `Nexus Dev`
3. **APIs & Services → OAuth consent screen**
   - User Type: **External**, App name: `Nexus`
   - Scopes: `openid`, `email`, `profile`
4. **APIs & Services → Credentials → Create Credentials → OAuth Client ID**
   - Application type: **Web application**
   - Authorized redirect URIs:
     - `http://localhost:8000/api/auth/google/callback` (dev)
     - `https://api-staging.nexus.in/api/auth/google/callback` (staging)
     - `https://api.nexus.in/api/auth/google/callback` (production)
5. Copy **Client ID** → `GOOGLE_CLIENT_ID`
6. Copy **Client Secret** → `GOOGLE_CLIENT_SECRET`

### 6.2 — Instagram / Meta Graph API

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. **My Apps → Create App → Consumer**
3. Add product: **Instagram Basic Display**
4. **Instagram Basic Display → Basic Display:**
   - Valid OAuth Redirect URIs:
     - `http://localhost:8000/api/auth/instagram/callback` (dev)
     - `https://api.nexus.in/api/auth/instagram/callback` (production)
   - Deauthorize callback URL: `https://api.nexus.in/api/auth/instagram/deauth`
5. Copy **Instagram App ID** → `INSTAGRAM_APP_ID`
6. Copy **Instagram App Secret** → `INSTAGRAM_APP_SECRET`
7. In development, add your personal IG account under **Roles → Instagram Testers**

### 6.3 — MongoDB Atlas (Staging / Production)

1. Create account at [mongodb.com/atlas](https://www.mongodb.com/cloud/atlas)
2. **Build a Database**:
   - Staging: **M0 Free Tier** (or M10 for better performance)
   - Production: **M10+** (dedicated cluster, replica set)
3. **Security → Database Access → Add Database User**
   - Username: `nexus_app`
   - Role: `readWrite` on database `nexus_staging`
4. **Security → Network Access → Add IP Address**
   - Add your Railway egress IPs (or `0.0.0.0/0` for development)
5. **Connect → Connect your application → Python 3.6+**
   - Copy the connection string → `MONGODB_URL`

### 6.4 — Redis / Upstash (Staging / Production)

1. Create account at [upstash.com](https://upstash.com/)
2. **Create Database**:
   - Name: `nexus-staging`
   - Region: `ap-south-1` (Mumbai — closest to India users)
   - Enable **TLS**
3. Copy **REST URL** and **Password** → Build:
   ```
   REDIS_URL=rediss://:<password>@<host>.upstash.io:6379
   CELERY_BROKER_URL=rediss://:<password>@<host>.upstash.io:6379
   CELERY_RESULT_BACKEND=rediss://:<password>@<host>.upstash.io:6379
   ```
   > Note the `rediss://` (with double `s`) — this enables TLS which Upstash requires.

### 6.5 — Cloudflare R2 (Optional)

1. [Cloudflare Dashboard](https://dash.cloudflare.com/) → **R2 Object Storage → Create Bucket**
2. **Manage R2 API Tokens → Create API Token**
   - Permissions: Object Read & Write on the bucket
3. Copy **Account ID**, **Access Key ID**, **Secret Access Key**
4. Copy **Public bucket URL** → `R2_PUBLIC_URL`

### 6.6 — Resend (Email, Optional)

1. [resend.com](https://resend.com/) → Sign up → **API Keys → Create API Key**
2. Add and verify your domain (`nexus.in`) in **Domains**
3. Copy API key → `RESEND_API_KEY`

### 6.7 — Sentry (Error Tracking, Optional)

1. [sentry.io](https://sentry.io/) → New Project → **Python FastAPI**
2. Copy **DSN** → `SENTRY_DSN`
3. Create separate projects for staging and production

---

## 7. Local Development — Docker Compose

This is the **recommended** path. Everything runs in containers — no manual MongoDB/Redis install needed.

### Prerequisites

- Docker Desktop running
- `.env.development` file created and filled (Section 4–5)

### Start All Services

```bash
# From the project root (nexus/)
docker-compose up --build
```

This starts:
| Container | Port | Description |
|-----------|------|-------------|
| `nexus_api` | `8000` | FastAPI with hot-reload |
| `nexus_worker` | — | Celery worker |
| `nexus_beat` | — | Celery beat scheduler |
| `nexus_mongo` | `27017` | MongoDB 7.0 |
| `nexus_redis` | `6379` | Redis 7.2 |
| `nexus_frontend` | `3000` | Next.js (if implemented) |

### Verify Everything Works

```bash
# API health check
curl http://localhost:8000/api/health
# → {"status": "ok", "environment": "development", ...}

# Swagger UI (disabled in production, available in dev)
open http://localhost:8000/docs
```

### Useful Docker Commands

```bash
# Start in background
docker-compose up -d

# View real-time logs from API
docker-compose logs -f api

# View all service logs
docker-compose logs -f

# Restart just the API (after code changes that aren't hot-reloaded)
docker-compose restart api

# Stop all services (keeps volumes)
docker-compose down

# Stop and DELETE all data volumes (full reset)
docker-compose down -v

# Rebuild a single service (after requirements.txt changes)
docker-compose up --build api

# Open a shell inside the API container
docker-compose exec api bash

# Run a management command inside the container
docker-compose exec api python -c "from app.config import settings; print(settings.APP_ENV)"
```

### Rebuild After Dependency Changes

Whenever you add packages to `requirements.txt`:

```bash
docker-compose up --build api worker beat
```

---

## 8. Local Development — Bare Metal (no Docker)

Use this if you prefer not to run Docker. You'll need MongoDB and Redis installed locally or available remotely.

### 8.1 — Install MongoDB Locally

**macOS (Homebrew):**
```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Ubuntu/Debian:**
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update && sudo apt-get install -y mongodb-org
sudo systemctl start mongod
```

**Windows:** Download [MongoDB Community Server](https://www.mongodb.com/try/download/community) installer.

### 8.2 — Install Redis Locally

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**Windows:** Use [Redis for Windows](https://github.com/microsoftarchive/redis/releases) or Docker for Redis only:
```bash
docker run -d -p 6379:6379 redis:7.2-alpine
```

### 8.3 — Update `.env.development` for Bare Metal

```ini
# No auth for local MongoDB (bare metal default)
MONGODB_URL=mongodb://localhost:27017/nexus_dev

# No password for local Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### 8.4 — Run the API

```bash
cd backend

# Activate venv (if not already active)
source .venv/bin/activate    # macOS/Linux
# OR
.venv\Scripts\Activate.ps1   # Windows

# Set the env file (pydantic-settings reads .env by default)
# Rename or symlink .env.development to .env:
cp .env.development .env

# Start FastAPI with hot-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 8.5 — Run Celery Worker (Separate Terminal)

```bash
cd backend
source .venv/bin/activate

celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

### 8.6 — Run Celery Beat (Separate Terminal)

```bash
cd backend
source .venv/bin/activate

celery -A app.tasks.celery_app beat --loglevel=info
```

---

## 9. Code Quality Toolchain

All quality tools are pre-configured and ready to use. Run them from the `backend/` directory.

### 9.1 — Tool Overview

| Tool | Purpose | Config |
|------|---------|--------|
| **ruff** | Linting + import sorting + fast formatting | `pyproject.toml` or `ruff.toml` |
| **black** | Opinionated Python code formatter | `pyproject.toml` |
| **mypy** | Static type checking | `pyproject.toml` or `mypy.ini` |

### 9.2 — Ruff (Lint + Format)

`ruff` is the primary code quality tool — it replaces flake8, isort, and pyupgrade in a single fast binary.

```bash
# Check for lint errors (no changes made)
ruff check app/

# Auto-fix all fixable lint issues
ruff check app/ --fix

# Format code (like black, but faster)
ruff format app/

# Check formatting without applying changes (for CI)
ruff format app/ --check

# Check + fix everything in one pass
ruff check app/ --fix && ruff format app/

# Check a single file
ruff check app/routers/auth.py
ruff format app/routers/auth.py
```

**Ruff configuration** — create `backend/ruff.toml`:
```toml
# ruff.toml
line-length = 100
target-version = "py312"
indent-width = 4

[lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "N",    # pep8-naming
    "SIM",  # flake8-simplify
    "TCH",  # flake8-type-checking
]
ignore = [
    "E501",  # line-too-long — handled by formatter
    "B008",  # do not perform function calls in default arguments (FastAPI Depends)
    "N805",  # first argument of a method should be named 'self' — conflicts with pydantic validators
]

[lint.isort]
known-first-party = ["app"]
force-sort-within-sections = true

[format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

### 9.3 — Black (Formatter)

```bash
# Format all files in-place
black app/

# Check without changing (for CI)
black app/ --check

# Show diff of what would change
black app/ --diff

# Format a single file
black app/routers/auth.py
```

**Black configuration** — add to `backend/pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ["py312"]
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | __pycache__
  | \.mypy_cache
)/
'''
```

> **Note:** If both `ruff format` and `black` are configured, use **one or the other** per CI run to avoid conflicts. `ruff format` is recommended for speed. Run `black` for additional compatibility with tools that expect black-style formatting.

### 9.4 — Mypy (Type Checker)

```bash
# Type-check the entire app
mypy app/

# Type-check a single module
mypy app/routers/auth.py

# Show error codes (useful for suppressing specific errors)
mypy app/ --show-error-codes

# Strict mode (enforce all type annotations)
mypy app/ --strict
```

**Mypy configuration** — add to `backend/pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.12"
strict = false
ignore_missing_imports = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Set true once all functions are annotated
exclude = [
    "tests/",
    ".venv/",
]
```

### 9.5 — Pre-commit Hooks (Recommended)

Run quality checks automatically before every `git commit`:

```bash
# Install pre-commit
uv pip install pre-commit

# Create .pre-commit-config.yaml in the project root
```

Create `nexus/.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-merge-conflict
      - id: debug-statements
```

```bash
# Install the hooks
pre-commit install

# Run manually against all files (first-time setup)
pre-commit run --all-files

# Run against staged files only
pre-commit run
```

### 9.6 — Full Quality Check (CI-style)

Run this before every pull request:

```bash
cd backend

# 1. Lint check
ruff check app/

# 2. Format check
ruff format app/ --check

# 3. Type check
mypy app/ --ignore-missing-imports

# 4. Tests with coverage
pytest tests/ --cov=app --cov-report=term-missing -v
```

Or as a single one-liner (bash/zsh):
```bash
ruff check app/ && ruff format app/ --check && mypy app/ --ignore-missing-imports && pytest tests/ -v
```

PowerShell equivalent:
```powershell
ruff check app/; ruff format app/ --check; mypy app/ --ignore-missing-imports; pytest tests/ -v
```

---

## 10. Running Tests

```bash
cd backend

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_auth.py -v

# Run a specific test function
pytest tests/test_auth.py::test_google_login -v

# Run tests matching a keyword
pytest tests/ -k "auth" -v

# Run and stop at first failure
pytest tests/ -x

# Run tests in parallel (install pytest-xdist first)
uv pip install pytest-xdist
pytest tests/ -n auto
```

### Test Environment

Tests use a separate in-memory MongoDB (via `mongomock-motor` or `beanie` test utilities). Set up a `backend/.env.test` for test-specific overrides:

```ini
APP_ENV=development
MONGODB_URL=mongodb://localhost:27017/nexus_test
REDIS_URL=redis://localhost:6379/15   # DB 15 = test isolation
```

---

## 11. Staging Deployment — Railway

Nexus uses [Railway](https://railway.app/) for staging and production deployments.

### 11.1 — Initial Railway Setup

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link
```

### 11.2 — Create Staging Project

1. [railway.app/new](https://railway.app/new) → **Deploy from GitHub Repo**
2. Select `nexus` repository → Set **Root Directory** to `backend/`
3. **Add a MongoDB service** (or connect to Atlas via env vars)
4. **Add a Redis service** (or use Upstash via env vars)

### 11.3 — Set Staging Environment Variables

```bash
# Set each variable via CLI
railway variables set APP_ENV=staging
railway variables set MONGODB_URL="mongodb+srv://..."
railway variables set REDIS_URL="rediss://..."
railway variables set JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
railway variables set ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
railway variables set GOOGLE_CLIENT_ID="..."
railway variables set GOOGLE_CLIENT_SECRET="..."
railway variables set GOOGLE_REDIRECT_URI="https://api-staging.nexus.in/api/auth/google/callback"
railway variables set INSTAGRAM_APP_ID="..."
railway variables set INSTAGRAM_APP_SECRET="..."
railway variables set INSTAGRAM_REDIRECT_URI="https://api-staging.nexus.in/api/auth/instagram/callback"
railway variables set FRONTEND_URL="https://nexus-staging.vercel.app"
railway variables set SENTRY_DSN="..."
railway variables set CELERY_BROKER_URL="rediss://..."
railway variables set CELERY_RESULT_BACKEND="rediss://..."
```

Or set them in **Railway Dashboard → Service → Variables** tab.

### 11.4 — Deploy

```bash
# Push to staging (Railway auto-deploys on push to main/staging branch)
git push origin staging

# Or trigger manual deploy
railway up
```

### 11.5 — Monitor

```bash
# View real-time logs
railway logs

# Open the deployed service URL
railway open
```

---

## 12. Production Deployment — Railway

### 12.1 — Create Production Project

Identical to staging setup (Section 11) but with a **separate Railway project** and:
- MongoDB Atlas **M10+** cluster (dedicated, replica set enabled)
- Upstash Redis with **TLS** enabled
- Sentry project for production
- All `*_REDIRECT_URI` values pointing to `api.nexus.in`

### 12.2 — Environment Differences

| Setting | Staging | Production |
|---------|---------|-----------|
| `APP_ENV` | `staging` | `production` |
| `DEBUG` | `false` | `false` |
| `MONGODB_DB_NAME` | `nexus_staging` | `nexus_production` |
| `RATE_LIMIT_PER_MINUTE` | `60` | `60` |
| Sentry `traces_sample_rate` | `1.0` | `0.1` |
| Swagger UI | Disabled | Disabled |
| Log level | `INFO` | `INFO` (file: `ERROR`) |

### 12.3 — Production Deploy

```bash
# Production deploys from the main branch
git push origin main
```

> **Never** manually `railway up` into production. All production deployments must go through the GitHub merge flow with CI checks passing.

---

## 13. Common Commands Reference

```bash
# ── Environment ───────────────────────────────────────────────
uv venv --python 3.12                    # Create venv
source .venv/bin/activate                # Activate (macOS/Linux)
.venv\Scripts\Activate.ps1              # Activate (Windows)
uv pip install -r requirements.txt      # Install all deps
uv pip sync requirements.txt            # Sync exactly (removes extras)
uv pip install <package>                # Add a new package

# ── Run Locally ───────────────────────────────────────────────
uvicorn app.main:app --reload --port 8000   # API server
celery -A app.tasks.celery_app worker       # Celery worker
celery -A app.tasks.celery_app beat         # Celery scheduler

# ── Docker ────────────────────────────────────────────────────
docker-compose up --build                # Start all services
docker-compose down -v                   # Stop + delete volumes
docker-compose logs -f api               # Follow API logs
docker-compose exec api bash             # Shell in container

# ── Code Quality ──────────────────────────────────────────────
ruff check app/                          # Lint check
ruff check app/ --fix                    # Lint + auto-fix
ruff format app/                         # Format files
ruff format app/ --check                 # Format check (CI)
black app/                               # Format with black
black app/ --check                       # Format check (CI)
mypy app/ --ignore-missing-imports       # Type check

# ── Tests ─────────────────────────────────────────────────────
pytest tests/ -v                         # All tests verbose
pytest tests/ --cov=app                  # With coverage
pytest tests/ -x                         # Stop on first fail
pytest tests/ -k "auth"                  # Filter by keyword

# ── Secret Generation ─────────────────────────────────────────
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# ── Railway ───────────────────────────────────────────────────
railway login                            # Login
railway link                             # Link project
railway up                               # Manual deploy
railway logs                             # View logs
railway variables                        # List all env vars
```

---

## 14. Troubleshooting

### `uv: command not found`
```bash
# Add uv to PATH (restart your terminal after install)
# macOS/Linux:
export PATH="$HOME/.cargo/bin:$PATH"

# Or reinstall:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### `ModuleNotFoundError` when running the app

```bash
# Make sure venv is active
which python   # Should point to .venv/bin/python

# Reinstall dependencies
uv pip sync requirements.txt
```

### `pydantic_core.InitErrorDetails` / missing env vars

```bash
# Check which variables are missing
python -c "from app.config import settings; print(settings.APP_ENV)"
# If it errors, a required variable is unset

# Make sure .env exists (pydantic-settings reads .env by default)
ls -la backend/.env
# If missing: cp .env.example .env  (then fill in values)
```

### MongoDB connection refused

```bash
# Docker: check if mongo container is healthy
docker-compose ps
# Should show: nexus_mongo   Up (healthy)

# If unhealthy, check logs
docker-compose logs mongodb

# Bare metal: check MongoDB is running
# macOS:
brew services list | grep mongodb

# Linux:
sudo systemctl status mongod
```

### Redis connection refused

```bash
# Docker: check container
docker-compose ps redis

# Bare metal: check Redis
redis-cli ping   # Should return: PONG
```

### Celery tasks not running

```bash
# Verify Celery can connect
celery -A app.tasks.celery_app inspect ping

# Check worker is running
celery -A app.tasks.celery_app status

# Ensure CELERY_BROKER_URL is correct in .env
python -c "from app.config import settings; print(settings.CELERY_BROKER_URL)"
```

### `mypy` reports `Cannot find implementation` for Beanie models

```bash
# This is expected — mypy doesn't fully understand Beanie's dynamic annotations
# Add to pyproject.toml or suppress per-file:
# [tool.mypy]
# plugins = ["pydantic.mypy"]

uv pip install pydantic[mypy]
```

### Port 8000 already in use

```bash
# macOS/Linux: find and kill the process
lsof -ti:8000 | xargs kill -9

# Windows (PowerShell):
netstat -ano | findstr :8000
# Note the PID, then:
taskkill /PID <pid> /F
```

### Docker image won't rebuild with new packages

```bash
# Force rebuild without cache
docker-compose build --no-cache api
docker-compose up api
```

---

> **Questions?** Open an issue on GitHub or ping `#backend` in the team Slack.  
> **Security issues?** Email `security@nexus.in` — do not open a public GitHub issue.
