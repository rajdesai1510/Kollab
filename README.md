# Kollab

## **Idea**: The idea was to create a creator marketplace and to expand it to a fully fledged creator-brand platform with advanced analytics and connection algorithm. Currently on hold, if you have any idea or wanna contribute it, connect with me on LINKEDIN.

> **A city-aware creator-brand matchmaking platform for Indian micro-influencers.**
> Verified creator profiles. Structured deal flow. No more cold DMs.

[![CI](https://github.com/your-org/nexus/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/nexus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [What is Nexus?](#what-is-nexus)
- [How It Works](#how-it-works)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Pages & Routes](#pages--routes)
- [Environment Setup](#environment-setup)
- [Local Development](#local-development)
- [Three-Environment Model](#three-environment-model)
- [Branch Strategy](#branch-strategy)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Contributing](#contributing)

---

## What is Nexus?

Nexus solves a structural gap in India's ₹5,500 crore influencer market. On one side, micro-influencers (10K–200K followers) struggle to find brand deals — no pipeline, no rate cards, no visibility. On the other side, local D2C brands and businesses waste budget on random cold DMs and unverified creators.

**Nexus is the bridge.** Think of it as LinkedIn for micro-influencers and local brands — a discovery and connection platform where:

- **Creators** build a verified profile auto-filled from Instagram, set their niche and city, and receive inbound deal requests from brands.
- **Brands** search verified creators by city, niche, follower tier, and engagement rate — and connect with the right ones in two clicks.
- **Deals** get structured and safe — no more ghosting, no more cold DMs.

---

## How It Works

### For Creators
1. Sign up with Google → Connect your Instagram account
2. Platform auto-fills your stats: followers, engagement rate, niche, city
3. Set your rate range and collaboration preferences
4. Go live — brands in your city can now find you
5. Receive connection requests → Accept → Chat inside the platform
6. Browse brand campaign briefs and express interest in relevant ones

### For Brands
1. Sign up with Google → Complete your brand profile
2. Post campaign briefs (what you need, your budget, target city and niche)
3. Discover verified creators filtered by city, niche, follower count, engagement rate
4. Send connection requests to creators you want to work with
5. After acceptance → Chat inside the platform → Move to deal details

---

## Features

### Creator Features
| Feature | Description |
|---|---|
| Google Sign-up | One-click sign-up via Google OAuth |
| Instagram Connect | OAuth integration — auto-pulls followers, engagement rate, bio, category |
| Verified Profile | Auto-synced IG stats, authenticity badge, engagement rate displayed |
| Niche & City Tags | Geolocation-assisted city detection, multiple niche tags |
| Rate Card | Optional "Starting from ₹X" visible to brands |
| Collaboration Types | Set preference: Product seeding / Paid post / Long-term ambassador |
| Open to Collabs Toggle | Turn discoverability ON/OFF |
| Campaign Board | Browse and express interest in brand campaign briefs |
| Connection Management | Accept / Decline brand connection requests |
| In-platform Chat | Real-time WebSocket chat — unlocks after mutual connection |
| Creator Dashboard | Profile views, connection stats, active dealings |
| Notification Centre | In-app + email alerts for requests, messages, campaign interest |

### Brand Features
| Feature | Description |
|---|---|
| Google Sign-up | One-click sign-up via Google OAuth |
| Brand Profile | Business name, logo, category, city, website |
| Campaign Brief Builder | Post what you need, budget range, target city/niche, timeline |
| Creator Discovery | Filter by city, niche, follower tier (nano/micro/mid), engagement rate %, collab type |
| Geolocation Search | "Creators in Bangalore" or "Creators near me" |
| Full Profile View | See IG stats, rate, past collaborations count, niche tags |
| Connection Requests | Send requests to shortlisted creators |
| Interested Creators | View creators who expressed interest in your campaign brief |
| In-platform Chat | After connection accepted — real-time WebSocket chat |
| Brand Dashboard | Active campaigns, connection count, inbound interests |

### Admin Features
| Feature | Description |
|---|---|
| User Management | View, verify, suspend creator and brand accounts |
| Campaign Moderation | Review and remove inappropriate briefs |
| Platform Analytics | Total users, connections made, city-wise activity |

---

## Tech Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.12 | Core language |
| **FastAPI** | 0.111+ | Async API framework, auto OpenAPI docs |
| **Beanie (Motor)** | 1.26+ | Async MongoDB ODM |
| **MongoDB Atlas** | — | Primary database (M0 free tier) |
| **Redis (Upstash)** | — | Sessions, cache, rate limiting, Celery broker |
| **Celery** | 5.4+ | Background jobs (Instagram stat sync, email) |
| **JWT (python-jose)** | — | Stateless auth tokens |
| **Loguru** | — | Structured logging |
| **Pydantic v2** | — | Request/response validation |
| **Pytest + HTTPX** | — | Async API testing |
| **Sentry SDK** | — | Error tracking (staging + production) |

### Frontend
| Technology | Version | Purpose |
|---|---|---|
| **Next.js** | 14 (App Router) | React framework, RSC, edge-ready |
| **Tailwind CSS** | 3.x | Utility-first styling |
| **Framer Motion** | — | Micro-animations, page transitions |
| **Zustand** | — | UI state management |
| **React Query (TanStack)** | — | Server state, caching, mutations |
| **Recharts** | — | Engagement stats charts |
| **Lucide React** | — | Icon set |
| **Inter** (Google Fonts) | — | Typography |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Docker + Docker Compose** | Local development environment parity |
| **Railway** | Backend hosting (dev + staging + production containers) |
| **Vercel** | Frontend hosting (native Next.js, edge CDN, preview PRs) |
| **GitHub Actions** | CI/CD pipeline |
| **Cloudflare R2** | File storage (profile photos, media) |
| **Resend** | Transactional email (connection alerts, welcome emails) |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│               CLIENT (Next.js on Vercel)          │
│  Creator App │ Brand App │ Admin Panel            │
│  (role-based routing in single Next.js app)       │
└─────────────────────┬────────────────────────────┘
                      │ HTTPS / WebSocket
┌─────────────────────▼────────────────────────────┐
│             FASTAPI MONOLITH (on Railway)         │
│                                                   │
│  /api/auth  /api/creators  /api/brands            │
│  /api/campaigns  /api/connections                 │
│  /api/messages  /api/notifications  /api/admin    │
│                                                   │
│  JWT Middleware │ CORS │ Rate Limiting            │
└──────┬──────────────┬──────────────┬─────────────┘
       │              │              │
   ┌───▼───┐    ┌─────▼────┐  ┌─────▼─────┐
   │MongoDB│    │  Redis   │  │  Celery   │
   │ Atlas │    │(Upstash) │  │  Workers  │
   └───────┘    └──────────┘  └─────┬─────┘
                                    │
                        ┌───────────▼──────────┐
                        │   External Services  │
                        │  Instagram Graph API │
                        │  Google OAuth        │
                        │  Resend Email        │
                        │  Cloudflare R2       │
                        └──────────────────────┘
```

---

## Pages & Routes

### Public Routes
| Route | Description |
|---|---|
| `/` | Landing page — hero, how it works, featured creators, CTA |
| `/discover` | Creator discovery (limited view without login) |
| `/campaigns` | Campaign board (limited view without login) |
| `/creators/[id]` | Public creator profile with IG stats |
| `/brands/[id]` | Public brand profile |

### Auth Routes
| Route | Description |
|---|---|
| `/login` | Google OAuth sign-in |
| `/onboarding` | Role selection (Creator / Brand) |
| `/onboarding/creator` | Connect Instagram, set niche, city, rate |
| `/onboarding/brand` | Business profile setup |

### Protected Routes (Authenticated)
| Route | Who | Description |
|---|---|---|
| `/dashboard` | Both | Role-based overview dashboard |
| `/discover` | Brand | Full creator search with all filters |
| `/campaigns` | Creator | Full campaign board |
| `/campaigns/new` | Brand | Post a new campaign brief |
| `/campaigns/[id]` | Both | Campaign detail + interested creators |
| `/connections` | Both | Pending requests + active connections |
| `/messages` | Both | All chat threads list |
| `/messages/[id]` | Both | Real-time WebSocket chat room |
| `/settings` | Both | Profile edit, Instagram reconnect |
| `/admin` | Admin | Admin panel |
| `/admin/users` | Admin | User management table |
| `/admin/campaigns` | Admin | Campaign moderation |
| `/admin/analytics` | Admin | Platform-wide stats |

---

## Environment Setup

### Prerequisites
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Node.js 20+
- Python 3.12+
- Git

### Required Accounts (for full functionality)
| Service | Purpose | Free Tier |
|---|---|---|
| [MongoDB Atlas](https://cloud.mongodb.com) | Primary database | M0 (512MB) — free forever |
| [Upstash Redis](https://upstash.com) | Cache + Celery broker | 10K commands/day free |
| [Google Cloud Console](https://console.cloud.google.com) | Google OAuth | Free |
| [Facebook Developers](https://developers.facebook.com) | Instagram OAuth | Free |
| [Cloudflare R2](https://cloudflare.com/r2) | File storage | 10GB free forever |
| [Resend](https://resend.com) | Email | 3000 emails/month free |
| [Sentry](https://sentry.io) | Error tracking | 5K errors/month free |

---

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/your-org/nexus.git
cd nexus
git checkout develop
```

### 2. Configure environment variables

```bash
# Backend
cp backend/.env.example backend/.env.development
# Edit backend/.env.development with your values

# Frontend
cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local with your values
```

### 3. Start with Docker Compose

```bash
# Start all services (FastAPI + MongoDB + Redis + Celery)
docker-compose up --build

# Or in detached mode
docker-compose up -d --build
```

### 4. Verify services are running

| Service | URL |
|---|---|
| FastAPI backend | http://localhost:8000 |
| API documentation (Swagger) | http://localhost:8000/docs |
| API documentation (ReDoc) | http://localhost:8000/redoc |
| Frontend (Next.js) | http://localhost:3000 |
| MongoDB (via Compass) | mongodb://localhost:27017 |
| Redis | redis://localhost:6379 |

### 5. Run tests

```bash
# Backend tests
cd backend
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=term-missing

# Frontend type checks
cd frontend
npm run type-check
```

---

## Three-Environment Model

| Environment | Branch | Backend | Frontend | Database | Notes |
|---|---|---|---|---|---|
| **Development** | `develop` | `localhost:8000` (Docker) | `localhost:3000` | Local MongoDB | Real API keys not required — mocks provided |
| **Staging** | `staging` | Railway (staging project) | Vercel (preview) | MongoDB Atlas M0 (dev cluster) | Auto-deploys on merge to `staging` |
| **Production** | `main` | Railway (prod project) | Vercel (production) | MongoDB Atlas M10+ | PR with 1 approval required |

### How Environment Switching Works

The entire application behaviour is controlled by a **single `APP_ENV` variable** in the `.env` file:

```env
# Switch between: development | staging | production
APP_ENV=development
```

This affects:
- Debug mode and log verbosity
- CORS allowed origins
- MongoDB cluster URL
- Redis connection
- Sentry DSN (disabled in development)
- Instagram/Google OAuth redirect URIs
- Email sending (mocked in development)

---

## Branch Strategy

```
main          ← Production (protected, PR + 1 review required)
  ↑
staging       ← Staging (auto-deploys on push)
  ↑
develop       ← Integration branch (all features merge here first)
  ↑
feature/xxx   ← Individual feature branches
hotfix/xxx    ← Urgent production fixes (merge to both main + develop)
```

### Workflow

```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/creator-discovery

# Work, commit, push
git add .
git commit -m "feat: add creator discovery search with city filter"
git push origin feature/creator-discovery

# Open PR → develop
# After CI passes + review → squash merge to develop
# develop → staging: auto-deploy via GitHub Actions
# staging → main: PR with approval → production deploy
```

---

## API Reference

Full interactive API docs available at:
- Development: http://localhost:8000/docs
- Staging: https://api-staging.nexus.in/docs

### Quick Reference

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/api/health` | Health check | None |
| `GET` | `/api/auth/google` | Google OAuth redirect | None |
| `GET` | `/api/auth/google/callback` | OAuth callback | None |
| `GET` | `/api/auth/instagram/connect` | Connect Instagram | JWT |
| `GET` | `/api/auth/me` | Current user profile | JWT |
| `POST` | `/api/auth/logout` | Logout | JWT |
| `GET` | `/api/creators/search` | Discover creators (filters) | Optional JWT |
| `GET` | `/api/creators/{id}` | Creator public profile | None |
| `PUT` | `/api/creators/profile` | Update creator profile | JWT (creator) |
| `POST` | `/api/creators/sync-instagram` | Refresh IG stats | JWT (creator) |
| `PATCH` | `/api/creators/toggle-collab` | Toggle open to collabs | JWT (creator) |
| `GET` | `/api/brands/{id}` | Brand public profile | None |
| `PUT` | `/api/brands/profile` | Update brand profile | JWT (brand) |
| `GET` | `/api/campaigns` | List open campaigns | Optional JWT |
| `POST` | `/api/campaigns` | Create campaign brief | JWT (brand) |
| `GET` | `/api/campaigns/{id}` | Campaign detail | None |
| `PUT` | `/api/campaigns/{id}` | Update campaign | JWT (brand, owner) |
| `DELETE` | `/api/campaigns/{id}` | Close campaign | JWT (brand, owner) |
| `POST` | `/api/campaigns/{id}/interest` | Express interest | JWT (creator) |
| `GET` | `/api/campaigns/{id}/interested` | View interested creators | JWT (brand, owner) |
| `POST` | `/api/connections/request` | Send connection request | JWT |
| `POST` | `/api/connections/{id}/accept` | Accept request | JWT |
| `POST` | `/api/connections/{id}/decline` | Decline request | JWT |
| `GET` | `/api/connections` | List connections + pending | JWT |
| `GET` | `/api/messages/{connection_id}` | Message history | JWT |
| `POST` | `/api/messages/{connection_id}` | Send message (REST fallback) | JWT |
| `WS` | `/api/ws/{connection_id}` | Real-time chat | JWT (query param) |
| `GET` | `/api/notifications` | Unread notifications | JWT |
| `POST` | `/api/notifications/read` | Mark notifications read | JWT |
| `GET` | `/api/admin/users` | All users | JWT (admin) |
| `GET` | `/api/admin/analytics` | Platform stats | JWT (admin) |

---

## Project Structure

```
nexus/
├── backend/                        # FastAPI monolith
│   ├── app/
│   │   ├── main.py                 # App factory, router registration
│   │   ├── config.py               # Pydantic settings, env-driven config
│   │   ├── database.py             # MongoDB + Redis connection init
│   │   ├── models/                 # Beanie ODM documents
│   │   │   ├── user.py
│   │   │   ├── creator_profile.py
│   │   │   ├── brand_profile.py
│   │   │   ├── campaign.py
│   │   │   ├── connection.py
│   │   │   ├── message.py
│   │   │   └── notification.py
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── creator.py
│   │   │   ├── brand.py
│   │   │   ├── campaign.py
│   │   │   ├── connection.py
│   │   │   └── message.py
│   │   ├── routers/                # FastAPI route handlers
│   │   │   ├── auth.py
│   │   │   ├── creators.py
│   │   │   ├── brands.py
│   │   │   ├── campaigns.py
│   │   │   ├── connections.py
│   │   │   ├── messages.py
│   │   │   ├── notifications.py
│   │   │   └── admin.py
│   │   ├── services/               # Business logic (called by routers)
│   │   │   ├── auth_service.py
│   │   │   ├── instagram_service.py
│   │   │   ├── creator_service.py
│   │   │   ├── connection_service.py
│   │   │   └── notification_service.py
│   │   ├── tasks/                  # Celery background tasks
│   │   │   ├── celery_app.py
│   │   │   └── instagram_sync.py
│   │   ├── middleware/
│   │   │   └── auth_middleware.py
│   │   └── utils/
│   │       ├── jwt_utils.py
│   │       ├── geo_utils.py
│   │       ├── encryption.py
│   │       └── response.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_creators.py
│   │   ├── test_campaigns.py
│   │   └── test_connections.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/                       # Next.js 14 App Router
│   ├── src/
│   │   ├── app/                    # App Router pages
│   │   ├── components/             # Reusable UI components
│   │   ├── lib/                    # API client, auth, store, websocket
│   │   └── styles/                 # Global CSS design tokens
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   └── .env.example
├── docker-compose.yml              # Local dev (all services)
├── docker-compose.staging.yml      # Staging overrides
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI: test → lint → build → deploy
├── .gitignore
└── README.md                       # ← You are here
```

---

## Contributing

1. Fork the repository
2. Create a feature branch from `develop`: `git checkout -b feature/your-feature`
3. Commit your changes with the conventional commits format:
   - `feat: add creator city filter`
   - `fix: correct engagement rate calculation`
   - `docs: update API reference`
   - `chore: bump dependencies`
4. Push to your fork and open a PR against `develop`
5. Ensure CI passes (lint + tests + Docker build)
6. Request a review

### Code Standards
- **Backend**: Ruff + Black formatting, Mypy type checking, Pytest for all new service functions
- **Frontend**: ESLint + Prettier, TypeScript strict mode
- **Commits**: Conventional Commits format
- **PRs**: Must have at least one reviewer approval before merge to `staging` or `main`

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

*Built with ❤️ for India's creator economy.*
