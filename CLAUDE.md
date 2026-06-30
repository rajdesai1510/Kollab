# Nexus — CLAUDE.md

> **Agent Orientation Document**
> This file is the authoritative guide for any AI agent working on this codebase.
> Read it fully before making any changes. Follow every convention documented here.

---

## 1. Project Overview

**Nexus** is a creator-brand matchmaking platform for the Indian micro-influencer market.
Think LinkedIn meets Fiverr - Instagram-only, India-focused. It is a **connection platform**, not an agency.

| Audience | Description |
|----------|-------------|
| Creators | Micro-influencers (10K-200K Instagram followers) |
| Brands   | Local Indian D2C brands seeking authentic promotion |

**Core flow:**
1. Creator/Brand signs up via **Google OAuth**
2. Creator connects **Instagram** (token stored encrypted)
3. Brand discovers creators via **filtered search** (city, niche, tier, engagement rate)
4. Brand sends **connection request** -> Creator accepts -> **in-platform chat** unlocks
5. Brands can also post **campaign briefs** -> Creators express interest

**Monetization:** 100% free at launch. Subscription tiers (Pro/Growth) are architecturally planned but feature-flagged off - do NOT activate them until the traction milestone.

---

## 2. Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend Framework | FastAPI | 0.111.1 |
| Python | CPython | 3.12 |
| ORM / ODM | Beanie (Motor + MongoDB) | 1.26.0 / 3.4.0 |
| Database | MongoDB Atlas | 7.0 (local Docker) |
| Cache / Queue Broker | Redis | 5.0.6 (Upstash in prod) |
| Background Tasks | Celery | 5.4.0 |
| Config | pydantic-settings | 2.3.4 |
| Auth | python-jose (JWT) + authlib (OAuth) | 3.3.0 / 1.3.1 |
| Encryption | cryptography (Fernet) | 42.0.8 |
| HTTP Client | httpx | 0.27.0 |
| Email | Resend | 2.2.0 |
| File Storage | Cloudflare R2 (boto3) | - |
| Error Tracking | Sentry | 2.6.0 |
| Logging | Loguru | 0.7.2 |
| Linter | Ruff | 0.4.10 |
| Formatter | Black | 24.4.2 |
| Type Checker | MyPy | 1.10.0 |
| Testing | pytest + pytest-asyncio | 8.2.2 / 0.23.7 |
| Frontend | Next.js 14 (App Router) | **NOT STARTED** |
| Infra | Docker Compose (local) / Railway (backend) / Vercel (frontend) |
| CI/CD | GitHub Actions (3 environments: develop -> staging -> main) |

---

## 3. Repository Structure

```
d:\startup\
+-- .github/
|   +-- workflows/
|       +-- ci.yml               <- GitHub Actions: lint, test, build, deploy
+-- backend/
|   +-- app/
|   |   +-- config.py            <- Settings class (pydantic-settings, env-driven)
|   |   +-- database.py          <- OLD file -- superseded by core/database.py (keep for now)
|   |   +-- main.py              <- FastAPI app factory + lifespan
|   |   +-- core/
|   |   |   +-- database.py      <- DatabaseManager class (MongoDB + Redis lifecycle)
|   |   |   +-- logger.py        <- CollabLogger class (Loguru wrapper)
|   |   |   +-- jwt_manager.py   <- JWTManager class (access + refresh tokens)
|   |   |   +-- encryption.py    <- EncryptionManager class (Fernet AES-128)
|   |   +-- models/              <- Beanie Document models (MongoDB collections)
|   |   |   +-- user.py          <- User + UserRole enum
|   |   |   +-- creator_profile.py <- CreatorProfile + NicheCategory, FollowerTier, etc.
|   |   |   +-- brand_profile.py <- BrandProfile
|   |   |   +-- campaign.py      <- Campaign + CampaignStatus, DeliverableType
|   |   |   +-- connection.py    <- Connection + ConnectionStatus
|   |   |   +-- message.py       <- Message + MessageType
|   |   |   +-- notification.py  <- Notification + NotificationType
|   |   +-- services/            <- Class-based business logic (NO direct DB calls in routers)
|   |   |   +-- auth_service.py        <- AuthService
|   |   |   +-- creator_service.py     <- CreatorService
|   |   |   +-- connection_service.py  <- ConnectionService (state machine)
|   |   |   +-- notification_service.py <- NotificationService
|   |   |   +-- instagram_service.py   <- InstagramService (stat sync)
|   |   +-- middleware/
|   |   |   +-- auth_middleware.py <- BearerTokenExtractor, get_current_user, get_optional_user, require_role
|   |   +-- routers/             <- FastAPI route handlers (thin -- delegate to services)
|   |   |   +-- auth.py
|   |   |   +-- creators.py
|   |   |   +-- brands.py
|   |   |   +-- campaigns.py
|   |   |   +-- connections.py
|   |   |   +-- messages.py      <- also contains ConnectionManager (WebSocket)
|   |   |   +-- notifications.py
|   |   |   +-- admin.py
|   |   +-- schemas/             <- Pydantic request/response models
|   |   |   +-- auth.py
|   |   |   +-- creator.py
|   |   |   +-- shared.py        <- campaign, connection, message schemas
|   |   +-- tasks/               <- Celery background tasks
|   |       +-- instagram_sync.py <- TODO: not yet implemented
|   +-- Dockerfile               <- Multi-stage: base, development, production
|   +-- requirements.txt
|   +-- .env.example             <- Template for all required env vars
+-- frontend/                    <- NOT STARTED -- Next.js 14 App Router
+-- docker-compose.yml           <- Local dev: api, worker, beat, mongodb, redis, frontend
+-- .gitignore
+-- README.md
```

---

## 4. The Golden Rule: Everything Is Class-Based

> **This is the single most important architectural rule. Never violate it.**

All logic in this codebase lives inside Python classes. This applies to:

| Layer | Class Name | Singleton Export |
|-------|-----------|-----------------|
| Core utilities | DatabaseManager, CollabLogger, JWTManager, EncryptionManager | db_manager, logger, jwt_manager, encryption_manager |
| Services | AuthService, CreatorService, ConnectionService, NotificationService, InstagramService | instantiated per-router as _auth_service = AuthService() |
| Routers | Pending refactor -- see Section 8 | auth_router = AuthRouter() |
| WebSocket manager | ConnectionManager | ws_manager = ConnectionManager() |
| Auth middleware | BearerTokenExtractor | _required_bearer, _optional_bearer |

**The only exceptions to class-based code:**
- FastAPI dependency functions (get_current_user, get_optional_user, require_role) -- must be plain async def for FastAPI Depends() to work
- Pydantic schema classes (BaseModel subclasses) -- data containers, not behavior classes
- @lru_cache-decorated get_settings() factory function

**When adding new code:** create a class, put logic in methods, export a module-level singleton.

---

## 5. Three Environments

APP_ENV controls all environment-specific behavior:

| Value | Where | Behavior |
|-------|-------|---------|
| development | Local Docker Compose | DEBUG logs (colored), Swagger UI at /docs, lenient CORS, Sentry off |
| staging | Railway staging project | JSON logs, no Swagger, Sentry on, preview Vercel deployments |
| production | Railway production | JSON logs + file rotation, Sentry on (0.1 sample rate), strict CORS |

Config is driven by app/config.py -> Settings class -> pydantic-settings.
Always use: from app.config import settings
Never read os.environ directly.

---

## 6. Authentication and Security Architecture

### Google OAuth (primary login)
`
Browser -> GET /api/auth/google -> redirect to Google consent
Google -> GET /api/auth/google/callback?code=... -> exchange code -> upsert User -> issue JWT pair
`

### Instagram OAuth (secondary -- connect stats)
`
Authenticated user -> GET /api/auth/instagram/connect -> redirect to Instagram consent
Instagram -> GET /api/auth/instagram/callback?code=... -> exchange -> encrypt token -> store in DB
-> trigger Celery task: sync Instagram stats immediately
`

### JWT Strategy
- **Access token:** 60 min TTL, sent as Authorization: Bearer <token>
- **Refresh token:** 30 days TTL, used only on POST /api/auth/refresh
- Both tokens carry: sub (user_id), role, type, iat, exp
- JWTManager class handles all cryptographic operations via python-jose
- Token verification: jwt_manager.verify_token(token, expected_type="access")

### Instagram Token Encryption
- Algorithm: **Fernet (AES-128-CBC + HMAC-SHA256)**
- Key: ENCRYPTION_KEY env var -- generate with: Fernet.generate_key().decode()
- Storage: user.instagram_access_token_encrypted field in MongoDB
- Operations: encryption_manager.encrypt(plaintext) / encryption_manager.decrypt(ciphertext)

### Auth Middleware Usage in Routers
`python
# Require authenticated user
from app.middleware.auth_middleware import get_current_user
async def my_endpoint(current_user: User = Depends(get_current_user)):

# Optional auth (public endpoint, different response when logged in)
from app.middleware.auth_middleware import get_optional_user
async def my_endpoint(viewer: Optional[User] = Depends(get_optional_user)):

# Require specific role
from app.middleware.auth_middleware import require_role
async def my_endpoint(current_user: User = Depends(require_role(UserRole.BRAND))):
`

---

## 7. Data Models

All models are **Beanie Documents** (MongoDB ODM). Registered in DatabaseManager.connect_mongo().

### User (users collection)
Key fields: email, name, avatar_url, role (UserRole enum), google_id, instagram_user_id, instagram_access_token_encrypted, is_active, onboarding_complete

### CreatorProfile (creator_profiles collection)
Key fields: user_id, display_name, city, state, niches (List[NicheCategory]), languages, collab_types, rate_min, rate_max, instagram_followers, instagram_engagement_rate, follower_tier, open_to_collabs, is_featured
Enums: NicheCategory, CollabType, FollowerTier (NANO/MICRO/MID/MACRO), Language

### BrandProfile (brand_profiles collection)
Key fields: user_id, company_name, industry, website, description, city

### Campaign (campaigns collection)
Key fields: brand_id, brand_user_id, title, description, deliverable_type (DeliverableType enum), budget_min/max, target_niches, target_city, pan_india, status (CampaignStatus: OPEN/PAUSED/CLOSED), interested_creator_ids, interested_count

### Connection (connections collection)
Key fields: requester_id (brand user_id), requester_profile_id, recipient_id (creator user_id), recipient_profile_id, status (ConnectionStatus: PENDING/ACCEPTED/DECLINED), campaign_id, accepted_at, declined_at

**State machine:** PENDING -> ACCEPTED (chat unlocks) or PENDING -> DECLINED.
Only the **recipient (creator)** can accept or decline. Duplicate check enforced by ConnectionService.

### Message (messages collection)
Key fields: connection_id, sender_id, content, message_type (TEXT), is_read, sent_at

### Notification (notifications collection)
Key fields: user_id, type (NotificationType enum), title, body, metadata (dict), is_read

---

## 8. Router Architecture -- PENDING REFACTOR

> WARNING: The last approved user request (not yet implemented) is to refactor all routers to class-based.

### Required Pattern
Every router module must be refactored to this pattern:

`python
class AuthRouter:
    def __init__(self):
        self.router = APIRouter()
        self.auth_service = AuthService()
        self._register_routes()

    def _register_routes(self):
        self.router.add_api_route(
            "/google", self.google_redirect, methods=["GET"],
            summary="Redirect to Google OAuth"
        )
        self.router.add_api_route(
            "/google/callback", self.google_callback, methods=["GET"],
            summary="Google OAuth callback", response_model=AuthResponse
        )
        # ... all other routes

    async def google_redirect(self) -> RedirectResponse:
        return RedirectResponse(url=settings.google_auth_url)

    async def google_callback(
        self,
        code: str = Query(...),
        response: Response = None,
    ) -> AuthResponse:
        ...

# Module export
auth_router = AuthRouter()
`

In main.py: app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])

### Routers to Refactor (8 total)
- auth.py -> AuthRouter (Google OAuth, Instagram OAuth, /me, /onboarding, /refresh, /logout)
- creators.py -> CreatorRouter (search, get profile, update, toggle collab, sync instagram)
- brands.py -> BrandRouter
- campaigns.py -> CampaignRouter (CRUD + interest flow)
- connections.py -> ConnectionRouter (request, accept, decline, list)
- messages.py -> MessageRouter (history REST, send REST, WebSocket)
- notifications.py -> NotificationRouter
- admin.py -> AdminRouter (users, campaigns, analytics)

**Current state:** All 8 routers use module-level router = APIRouter() and plain function handlers. The refactor is the next step to implement.

---

## 9. WebSocket Chat Architecture

Lives in routers/messages.py. Class: ConnectionManager.

`
ws_manager.active_connections = {
    connection_id: {user_id: WebSocket}
}
`

**Authentication:** JWT passed as query param ?token=... (headers not supported by WebSocket spec in browsers).

**Smart notification logic:** When a message is sent, a push notification is only sent to the recipient if they are NOT currently in the room:
`python
if recipient_id not in ws_manager.active_connections.get(connection_id, {}):
    await notify...
`

**Scaling note:** ConnectionManager is in-memory, single-instance. For horizontal scaling, replace with Redis Pub/Sub. Do not implement Redis Pub/Sub until explicitly required.

**Connection flow:**
1. Client connects: ws://api/api/messages/ws/{connection_id}?token=<jwt>
2. Server validates JWT, verifies user is party to an ACCEPTED connection
3. Server calls ws_manager.connect(connection_id, user_id, websocket)
4. Client sends: {"content": "Hello!"}
5. Server persists to DB, broadcasts to room, conditionally notifies recipient

---

## 10. Services -- Key Behaviours

### AuthService
- google_login(code) -> exchanges code -> upserts User -> returns (User, TokenPair)
- connect_instagram(user, code) -> stores encrypted token -> triggers Celery sync task
- set_user_role(user, role) -> one-time role assignment during onboarding
- Shares a single httpx.AsyncClient across calls (TCP connection reuse)
- Cleanup: await auth_service.close() on shutdown

### CreatorService
- search(filters, skip, limit) -> filtered discovery query, sorted by engagement rate desc
- increment_profile_views(profile_id) -> fire-and-forget MongoDB  update
- Hard cap: limit = min(limit, 50) -- never return more than 50 results per page

### ConnectionService
- send_request(...) -> checks for PENDING/ACCEPTED duplicate -> creates Connection -> notifies creator
- accept_request(connection_id, accepting_user_id) -> validates recipient -> sets ACCEPTED -> notifies brand
- decline_request(connection_id, declining_user_id) -> validates recipient -> sets DECLINED
- get_connection_for_chat(connection_id, user_id) -> validates ACCEPTED status + membership -> used before chat access

### NotificationService
- notify_connection_request(...) -> creates in-app Notification + optional email via Resend
- notify_connection_accepted(...) -> same pattern
- notify_new_message(...) -> same pattern
- Email is gated by settings.email_enabled (requires RESEND_API_KEY)

### InstagramService
- Fetches stats from Instagram Graph API using the stored encrypted access token
- Calculates engagement_rate = (avg_likes + avg_comments) / followers * 100
- Updates CreatorProfile with all Instagram fields
- Sets follower_tier based on computed_follower_tier property thresholds

---

## 11. Background Tasks (Celery)

**Broker:** Redis DB 1 (CELERY_BROKER_URL)
**Result backend:** Redis DB 2 (CELERY_RESULT_BACKEND)

### Instagram Sync Task -- tasks/instagram_sync.py (NOT YET IMPLEMENTED)

This task is called in two places:
1. AuthService.connect_instagram() -- immediate sync on first connect
2. CreatorRouter.sync_instagram() -- manual trigger endpoint

Expected implementation pattern:
`python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "nexus",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

@celery_app.task(name="instagram_sync.trigger_instagram_sync")
def trigger_instagram_sync(user_id: str, profile_id: str = None):
    """Sync Instagram stats for a creator. Called via .delay()."""
    import asyncio
    from app.services.instagram_service import InstagramService
    service = InstagramService()
    asyncio.run(service.sync_creator_stats(user_id=user_id, profile_id=profile_id))
`

The task must be importable as:
`python
from app.tasks.instagram_sync import trigger_instagram_sync
trigger_instagram_sync.delay(str(user.id))
`

Docker Compose spins up worker and beat services that run this automatically.

---

## 12. main.py -- Wiring Issue

main.py currently imports from the **old** app.database module (module-level functions):
`python
from app.database import (
    connect_to_mongodb, connect_to_redis,
    disconnect_from_mongodb, disconnect_from_redis,
)
`

It **should** use the class-based DatabaseManager from app.core.database:
`python
from app.core.database import db_manager

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await db_manager.connect()
    yield
    await db_manager.disconnect()
`

This migration is part of the pending work. The old app/database.py can be kept temporarily as a compatibility shim.

---

## 13. API Route Reference

All routes are prefixed with /api. No versioning prefix in URLs (versioning via branch/deployment).

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| Auth | /api/auth | GET /google, /google/callback, /instagram/connect, /instagram/callback, /me; POST /onboarding/role, /refresh, /logout |
| Creators | /api/creators | GET /search, /{profile_id}; PUT /profile; PATCH /toggle-collab; POST /sync-instagram |
| Brands | /api/brands | Brand profile CRUD |
| Campaigns | /api/campaigns | GET /, /{id}, /{id}/interested; POST /, /{id}/interest; PUT /{id}; DELETE /{id} |
| Connections | /api/connections | POST /request, /{id}/accept, /{id}/decline; GET / |
| Messages | /api/messages | GET /{connection_id}; POST /{connection_id}; WebSocket /ws/{connection_id} |
| Notifications | /api/notifications | GET + PATCH (mark read) |
| Admin | /api/admin | GET/PATCH/DELETE users + campaigns; GET /analytics |
| Health | /api/health | GET (always public, used by Railway) |

Swagger UI available at /docs in development/staging only (hidden in production).

---

## 14. Environment Variables

See backend/.env.example for the full annotated list.

### Required for all environments
`
APP_ENV                      # development | staging | production
MONGODB_URL                  # MongoDB connection string
MONGODB_DB_NAME              # nexus_dev | _staging | _production
REDIS_URL                    # Redis URL (rediss:// with TLS for Upstash)
CELERY_BROKER_URL            # Redis URL for Celery broker (DB 1)
CELERY_RESULT_BACKEND        # Redis URL for Celery results (DB 2)
JWT_SECRET_KEY               # Min 32 chars
ENCRYPTION_KEY               # Fernet key
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI          # http://localhost:8000/api/auth/google/callback
INSTAGRAM_APP_ID
INSTAGRAM_APP_SECRET
INSTAGRAM_REDIRECT_URI       # http://localhost:8000/api/auth/instagram/callback
FRONTEND_URL                 # http://localhost:3000
`

### Generate secrets
`ash
python -c "import secrets; print(secrets.token_urlsafe(64))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
`

### Optional (feature-gated)
`
RESEND_API_KEY               # Email sending -- empty = emails logged only
SENTRY_DSN                   # Error tracking -- empty = Sentry disabled
R2_ACCOUNT_ID                # Cloudflare R2 -- empty = no file uploads
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
`

---

## 15. Local Development

### Start everything
`ash
cp backend/.env.example backend/.env.development   # Fill in your values
docker-compose up --build
`

Services:
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- MongoDB: localhost:27017
- Redis: localhost:6379

### Running tests
`ash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
`

### Code quality (run before committing)
`ash
cd backend
ruff check app/
black --check app/
mypy app/ --ignore-missing-imports
`

---

## 16. CI/CD Pipeline

GitHub Actions: .github/workflows/ci.yml

| Job | Trigger | What it does |
|-----|---------|-------------|
| backend-test | all pushes/PRs | Ruff + Black + MyPy + Pytest (>=70% coverage) |
| frontend-test | all pushes/PRs | ESLint + TypeScript check + Next.js build |
| docker-build | after tests pass | Verifies production Docker images build |
| deploy-staging | push to staging branch | Railway (backend) + Vercel (frontend) |
| deploy-production | push to main branch | Railway (backend) + Vercel (frontend) --prod |

**Branch flow:** develop -> (PR) -> staging -> (PR) -> main

**Required GitHub Secrets:**
- RAILWAY_TOKEN_STAGING, RAILWAY_TOKEN_PRODUCTION
- VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID

---

## 17. What Is Done vs. Pending

### Complete (Backend)
- Docker Compose infrastructure (MongoDB, Redis, Celery worker + beat, API)
- GitHub Actions CI/CD pipeline
- All 7 Beanie data models with indexes
- DatabaseManager -- MongoDB + Redis lifecycle management
- CollabLogger -- environment-aware Loguru wrapper
- JWTManager -- access + refresh token issuance and verification
- EncryptionManager -- Fernet encryption for Instagram tokens
- AuthService -- Google OAuth + Instagram OAuth + user upsert
- CreatorService -- profile CRUD + discovery search
- ConnectionService -- full PENDING->ACCEPTED/DECLINED state machine
- NotificationService -- in-app + Resend email notifications
- InstagramService -- stat sync + engagement rate calculation
- BearerTokenExtractor + get_current_user + get_optional_user + require_role
- All Pydantic schemas (auth, creator, shared: campaign/connection/message)
- All 8 routers (auth, creators, brands, campaigns, connections, messages, notifications, admin)
- ConnectionManager class for WebSocket rooms (in messages.py)

### Not Yet Implemented (priority order)
1. **tasks/instagram_sync.py** -- Celery task file (wraps InstagramService.sync_creator_stats)
2. **main.py migration** -- switch from app.database (old) to app.core.database.db_manager
3. **Router refactor** -- convert all 8 routers to the class-based XxxRouter pattern (Section 8)
4. **Frontend** -- entire Next.js 14 App Router frontend (d:\startup\frontend\)
5. **Test suite** -- no tests exist yet; CI requires 70% coverage

### Architecturally Planned but Deferred
- Subscription tiers (Pro/Growth) -- feature-flagged, not activated
- Redis token blocklist for logout invalidation (currently stateless)
- Multi-instance WebSocket via Redis Pub/Sub (currently in-memory)
- Celery Beat scheduled tasks (48h Instagram stat refresh)

---

## 18. Coding Conventions

### Python (Backend)
- **Class-based everything** -- see Section 4
- **Type annotations** on all method signatures (enforced by MyPy)
- **Docstrings** on all public methods -- describe Args, Returns, Raises
- **No logic in routers** -- route handlers validate input, call service methods, return responses
- **Import services lazily when needed** to break circular imports (e.g., Celery task imports inside method body)
- **Exception hierarchy** -- define domain-specific exceptions per service (e.g., ConnectionNotFoundError)
- **Module-level singletons** -- always export as snake_case_name = ClassName()
- **Never read os.environ directly** -- always use from app.config import settings
- **Never use print()** -- always use from app.core.logger import logger
- **Pagination pattern:** limit + 1 trick -- fetch one extra, check has_more = len(results) > limit, then slice results[:limit]

### File naming
- Models: snake_case.py with a single PascalCase Document class
- Services: xxx_service.py with an XxxService class + domain exceptions at top
- Routers: xxx.py (pending migration to class pattern) -- after migration, export xxx_router
- Schemas: group related schemas in same file; split when file exceeds ~300 lines

### Async patterns
- All database operations are async/await via Motor + Beanie
- All HTTP calls are async via httpx.AsyncClient
- Never use synchronous DB or HTTP calls in route handlers -- they block the event loop
- Celery tasks are synchronous -- use asyncio.run() inside the task to call async service methods

---

## 19. Frontend Architecture (Planned -- Not Started)

When implementing the frontend, use this stack:

| Component | Technology |
|-----------|-----------|
| Framework | Next.js 14 (App Router) |
| Styling | Tailwind CSS |
| Animation | Framer Motion |
| State | Zustand |
| Server state | React Query (TanStack Query) |
| Auth | JWT in localStorage (access) + httpOnly cookie (refresh) |
| API base URL | NEXT_PUBLIC_API_URL env var |

**Key pages to build:**
1. Landing page (creator discovery preview + CTA)
2. Auth: Google sign-in redirect
3. Onboarding: role selection -> Creator profile setup or Brand profile setup
4. Creator dashboard: profile, Instagram connect, collab toggle
5. Brand dashboard: search creators, campaign CRUD
6. Discovery: creator search with filters
7. Connection inbox: pending/accepted connections
8. Chat: WebSocket-based real-time messages per connection
9. Campaign board: browse briefs, express interest
10. Admin dashboard: user management, analytics

---

## 20. Known Issues / Technical Debt

| Issue | File | Severity |
|-------|------|---------|
| main.py uses old app.database imports, not core/database.py | app/main.py | Medium -- works but inconsistent |
| app/database.py (old file) still exists | app/database.py | Low -- kept as shim, delete after migration |
| Routers are function-based, not class-based | app/routers/*.py | Medium -- pending approved refactor |
| tasks/instagram_sync.py is referenced but not implemented | app/tasks/ | High -- trigger_instagram_sync.delay() will crash |
| InstagramStats in creator_profile.py inherits dict instead of BaseModel | app/models/creator_profile.py | Low -- design quirk, not breaking |
| main.py does not configure CollabLogger via logger.configure(...) | app/main.py | Low -- Loguru falls back to default config |
| No test files exist yet | backend/tests/ | High -- CI enforces 70% coverage threshold |

---

## 21. Security Rules

1. **Never log secrets** -- no JWT values, OAuth codes, access tokens, or encryption keys in logs
2. **Never commit .env files** -- .gitignore covers *.env, .env.*, .env.development, etc.
3. **Instagram tokens are always stored encrypted** -- use encryption_manager.encrypt() before saving to DB
4. **Swagger is disabled in production** -- enforced via docs_url=None when settings.is_production
5. **Admin routes enforce role check** -- use Depends(require_role(UserRole.ADMIN)) on every admin endpoint
6. **CORS is strict in production** -- only settings.FRONTEND_URL is whitelisted
7. **Non-root user in production Docker** -- appuser is created and used in the production Dockerfile stage

---

*Last updated by project analysis: Nexus v0.1.0 -- backend complete, frontend pending.*
