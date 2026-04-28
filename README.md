# HNG Stage Three - Insighta Labs+

## Overview
The **Insighta Labs+** is a FastAPI-based service that enriches names with demographic insights. By integrating with external APIs (**Genderize.io**, **Agify.io**, and **Nationalize.io**), it provides estimated gender, age, and nationality for a given name. Results are persisted in a PostgreSQL database for historical tracking and efficient retrieval.

This project was developed as part of the HNG Stage One backend task.

---

## Table of Contents

- [System Architecture](#system-architecture)
- [Authentication Flow](#authentication-flow)
- [CLI Usage](#cli-usage)
- [Token Handling Approach](#token-handling-approach)
- [Role Enforcement Logic](#role-enforcement-logic)
- [Natural Language Parsing Approach](#natural-language-parsing-approach)
- [Tech Stack](#tech-stack)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [External Integrations](#external-integrations)
- [License](#license)

---

## System Architecture

The application follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                              │
│               (Browser / CLI / HTTP Client)                 │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     Middleware Stack                        │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │  Logging      │ │  Rate Limit  │ │  API Versioning     │ │
│  │  Middleware   │ │  Middleware   │ │  (X-API-Version)    │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    API Router Layer                         │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │  /auth/*             │  │  /api/profiles/*         │    │
│  │  (auth.py)           │  │  (profiles.py)           │    │
│  └──────────┬───────────┘  └────────────┬─────────────┘    │
│             │                           │                  │
│  ┌──────────▼───────────────────────────▼─────────────┐    │
│  │           Dependency Injection Layer                │    │
│  │  ┌───────────────┐    ┌──────────────────────┐     │    │
│  │  │ get_current_   │    │ Rolechecker (RBAC)   │     │    │
│  │  │ user (deps.py) │    │ (rbac.py)            │     │    │
│  │  └───────────────┘    └──────────────────────┘     │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Service Layer                            │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │  Auth Service         │  │  Profile Service          │    │
│  │  - GitHub OAuth       │  │  - CRUD operations        │    │
│  │  - Token creation     │  │  - External API calls     │    │
│  │  - Token refresh      │  │  - Natural language query │    │
│  │  - Logout / revoke    │  │  - CSV export             │    │
│  └──────────────────────┘  └──────────────────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Data Layer                               │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │  SQLAlchemy ORM       │  │  External APIs           │    │
│  │  Models:              │  │  - Genderize.io          │    │
│  │  - User               │  │  - Agify.io              │    │
│  │  - Profile (UUID v7)  │  │  - Nationalize.io        │    │
│  │  - RefreshToken       │  │  - GitHub OAuth           │    │
│  └──────────┬───────────┘  └──────────────────────────┘    │
│             │                                              │
│  ┌──────────▼───────────┐                                  │
│  │  PostgreSQL Database  │                                  │
│  └──────────────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
app/
├── main.py                  # App entrypoint, middleware registration, exception handlers
├── core/
│   └── config.py            # Pydantic Settings (env vars)
├── db/
│   └── session.py           # SQLAlchemy engine, session factory, Base
├── models/
│   ├── users.py             # User model with ROLE enum (ADMIN / ANALYST)
│   ├── auth.py              # RefreshToken model
│   └── profiles.py          # Profile model (UUID v7 primary key)
├── schemas/
│   └── profiles.py          # Pydantic request/response models, filter params
├── api/
│   ├── v1/
│   │   ├── auth.py          # Auth routes (GitHub OAuth, refresh, logout)
│   │   └── profiles.py      # Profile CRUD, search, export routes
│   └── dependencies/
│       ├── deps.py          # get_current_user (JWT verification)
│       └── rbac.py          # Rolechecker (role-based access control)
├── services/
│   ├── auth.py              # Auth business logic (JWT, refresh tokens, GitHub OAuth)
│   └── profiles.py          # Profile business logic (CRUD, NLP query, CSV export)
├── middleware/
│   ├── logging.py           # Request/response logging with timing
│   ├── rate_limits.py       # IP-based rate limiting (10 auth / 60 general per minute)
│   └── versioning.py        # X-API-Version header enforcement
├── alembic/                 # Database migration scripts
├── seed.py                  # Database seeding from seed_profiles.json
└── seed_profiles.json       # Initial profile data
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| **UUID v7** primary keys for profiles | Time-ordered UUIDs provide natural chronological ordering and are globally unique |
| **Layered architecture** (Router → Dependency → Service → Model) | Clean separation of concerns; services are testable independently of HTTP layer |
| **Middleware stack** (Logging → Rate Limit → Versioning) | Cross-cutting concerns handled before reaching route handlers |
| **Pydantic Settings** for configuration | Type-safe config with automatic `.env` loading and validation at startup |

---

## Authentication Flow

The API uses **GitHub OAuth 2.0** as the authentication provider with support for **PKCE** (Proof Key for Code Exchange) for CLI clients.

### Flow Diagram

```
┌──────────┐                ┌──────────┐              ┌──────────┐
│  Client  │                │  API     │              │  GitHub  │
└────┬─────┘                └────┬─────┘              └────┬─────┘
     │  1. GET /auth/github      │                         │
     │  (+ state, code_challenge │                         │
     │   for CLI/PKCE)           │                         │
     │ ─────────────────────────>│                         │
     │                           │  2. 302 Redirect        │
     │ <─────────────────────────│  → GitHub authorize URL │
     │                           │                         │
     │  3. User authorizes app on GitHub                   │
     │ ───────────────────────────────────────────────────>│
     │                           │                         │
     │                           │  4. GitHub redirects    │
     │                           │  with ?code=...         │
     │ <──────────────────────────────────────────────────│
     │                           │                         │
     │  5. GET /auth/github/     │                         │
     │     callback?code=...     │                         │
     │ ─────────────────────────>│                         │
     │                           │  6. Exchange code for   │
     │                           │  GitHub access token    │
     │                           │ ───────────────────────>│
     │                           │                         │
     │                           │  7. Fetch user profile  │
     │                           │ ───────────────────────>│
     │                           │  8. GitHub user data    │
     │                           │ <───────────────────────│
     │                           │                         │
     │  9. { access_token,       │                         │
     │       refresh_token }     │                         │
     │ <─────────────────────────│                         │
     └───────────────────────────┘                         │
```

### Step-by-Step

1. **Initiate login** — Client calls `GET /auth/github`. For CLI clients, optional `state` and `code_challenge` (S256) parameters enable PKCE.
2. **Redirect** — The API builds a GitHub OAuth authorize URL and returns a `302 Redirect`.
3. **User authorizes** — The user logs in/authorizes the app on GitHub.
4. **Callback** — GitHub redirects back to the callback URL with an authorization `code`.
5. **Token exchange** — `GET /auth/github/callback` receives the code. The API service exchanges it with GitHub for a GitHub access token.
6. **User resolution** — The API fetches the user's GitHub profile (`/user` endpoint). If the user doesn't exist locally, a new `User` record is created with the default role `analyst`. If they already exist, `last_login_at` is updated.
7. **Token issuance** — The API creates a **JWT access token** and a **refresh token**, returning both to the client.

---

## CLI Usage

The API supports CLI-based authentication using the **PKCE** (Proof Key for Code Exchange) extension of OAuth 2.0, ensuring secure token exchange without exposing client secrets.

### CLI Authentication with PKCE

```bash
# 1. Generate a PKCE code verifier and challenge (S256) on the client side
#    The code_verifier is a random string; the code_challenge is its SHA-256 hash, base64url-encoded.

# 2. Initiate GitHub login with PKCE parameters
curl -L "http://localhost:8000/auth/github?state=<random_state>&code_challenge=<your_code_challenge>"
#    → Opens GitHub authorization page (302 redirect)

# 3. After authorization, GitHub redirects to the callback with ?code=...
#    Complete the flow by passing the code_verifier:
curl "http://localhost:8000/auth/github/callback?code=<github_code>&state=<random_state>&code_verifier=<your_code_verifier>"
#    → Returns { "access_token": "...", "refresh_token": "..." }
```

### Using the Access Token

All `/api/*` endpoints require two things:
1. A valid **JWT Bearer token** in the `Authorization` header.
2. An **`X-API-Version: 1`** header.

```bash
# List profiles
curl -H "Authorization: Bearer <access_token>" \
     -H "X-API-Version: 1" \
     http://localhost:8000/api/profiles

# Create a profile (requires admin role)
curl -X POST \
     -H "Authorization: Bearer <access_token>" \
     -H "X-API-Version: 1" \
     -H "Content-Type: application/json" \
     -d '{"name": "Alex"}' \
     http://localhost:8000/api/profiles

# Search profiles with natural language
curl -H "Authorization: Bearer <access_token>" \
     -H "X-API-Version: 1" \
     "http://localhost:8000/api/profiles/search?q=female+adults+from+Nigeria"

# Refresh tokens
curl -X POST "http://localhost:8000/auth/refresh?refresh_token=<refresh_token>"

# Logout (revoke refresh token)
curl -X POST "http://localhost:8000/auth/logout?refresh_token=<refresh_token>"
```

---

## Token Handling Approach

The system uses a **dual-token strategy** with short-lived JWTs and long-lived refresh tokens.

### Access Tokens (JWT)

| Property | Value |
|---|---|
| **Format** | JSON Web Token (JWT) |
| **Algorithm** | HS256 |
| **Lifetime** | Configurable via `ACCESS_TOKEN_TIME` env var (minutes) |
| **Claims** | `sub` (user ID), `role` (user role), `type` ("access"), `exp` (expiry) |
| **Storage** | Client-side only; never persisted on the server |

**Creation** (`create_access_token`):
- Encodes user ID and role into the JWT payload.
- Sets `type: "access"` to distinguish from other token types.
- Sets an expiration timestamp based on `ACCESS_TOKEN_TIME`.
- Signs with `SECRET_KEY` using HS256.

**Verification** (`verify_token`):
- Decodes the JWT using the server's `SECRET_KEY`.
- Validates the `type` claim is `"access"`.
- Raises `401 Unauthorized` on invalid or expired tokens.

### Refresh Tokens

| Property | Value |
|---|---|
| **Format** | Cryptographically random URL-safe string (`secrets.token_urlsafe(32)`) |
| **Lifetime** | Configurable via `REFRESH_TOKEN_TIME` env var (minutes) |
| **Storage** | Persisted in the `refresh_tokens` database table |
| **Revocation** | `is_revoked` flag on the database record |

**Refresh flow** (`POST /auth/refresh`):
1. Look up the token in the database.
2. Verify it has not been revoked and has not expired.
3. **Rotate**: revoke the old refresh token, issue a new access + refresh token pair.
4. Return the new token pair to the client.

**Logout flow** (`POST /auth/logout`):
1. Look up the refresh token in the database.
2. Set `is_revoked = True` and commit.
3. The associated access token will naturally expire.

### Token Lifecycle Diagram

```
Login ──► [Access Token (short-lived)] ──► Expired?
              │                                │
              │                          YES   │
              │                     ┌──────────▼──────────┐
              │                     │  POST /auth/refresh  │
              │                     │  (send refresh_token)│
              │                     └──────────┬──────────┘
              │                                │
              │                     ┌──────────▼──────────┐
              │                     │ Old refresh revoked   │
              │                     │ New access + refresh  │
              │                     │ tokens issued         │
              │                     └─────────────────────┘
              │
              └──► POST /auth/logout ──► Refresh token revoked
```

---

## Role Enforcement Logic

The system implements **Role-Based Access Control (RBAC)** through a dependency-injection pattern using FastAPI's `Depends()`.

### Roles

| Role | Value | Description |
|---|---|---|
| **ADMIN** | `"admin"` | Full access — can create profiles, delete profiles, and perform all read operations |
| **ANALYST** | `"analyst"` | Read-only access — can list, search, view, and export profiles |

New users created via GitHub OAuth are assigned the **`analyst`** role by default.

### Enforcement Mechanism

The `Rolechecker` class in `app/api/dependencies/rbac.py` acts as a callable FastAPI dependency:

```python
class Rolechecker:
    def __init__(self, required_role: ROLE):
        self.required_role = required_role

    def __call__(self, current_user: User = Depends(get_current_user)):
        if current_user.role != self.required_role:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )
        return current_user
```

### How It Works

1. **Authentication first** — `Rolechecker` depends on `get_current_user`, which extracts and verifies the JWT from the `Authorization: Bearer <token>` header. This ensures the user is authenticated before any role check occurs.
2. **Role comparison** — The authenticated user's role (from the database record) is compared against the required role.
3. **Access denied** — If the role doesn't match, a `403 Forbidden` response is returned with `"Insufficient permissions"`.
4. **Access granted** — If the role matches, the authenticated `User` object is injected into the route handler.

### Per-Endpoint Enforcement

| Endpoint | Required Role | Dependency |
|---|---|---|
| `POST /api/profiles` | `ADMIN` | `Depends(Rolechecker(ROLE.ADMIN))` |
| `DELETE /api/profiles/{id}` | `ADMIN` | `Depends(Rolechecker(ROLE.ADMIN))` |
| `GET /api/profiles` | Any authenticated | `Depends(get_current_user)` |
| `GET /api/profiles/{id}` | Any authenticated | `Depends(get_current_user)` |
| `GET /api/profiles/search` | Any authenticated | `Depends(get_current_user)` |
| `GET /api/profiles/export` | Public | None |

---

## Natural Language Parsing Approach

The `GET /api/profiles/search?q=<query>` endpoint accepts plain-English queries and translates them into structured database filters using the `natural_query` method in `ProfileService`.

### Parsing Strategy

The parser uses a **keyword-matching** approach with regex pattern extraction. It scans the lowercased query string for known tokens and maps them to filter parameters:

#### Gender Detection

| Keywords | Filter Applied |
|---|---|
| `"male"`, `"males"` | `gender = "male"` |
| `"female"`, `"females"` | `gender = "female"` |

#### Age Group Detection

| Keywords | Filter Applied |
|---|---|
| `"child"`, `"children"` | `age_group = "child"` |
| `"teenager"`, `"teenagers"` | `age_group = "teenager"` |
| `"adult"`, `"adults"` | `age_group = "adult"` |
| `"senior"` | `age_group = "senior"` |
| `"young"` | `min_age = 16`, `max_age = 24` |

#### Age Range Extraction (Regex)

| Pattern | Example | Filter Applied |
|---|---|---|
| `above <number>` | `"above 30"` | `min_age = 30` |
| `below <number>` | `"below 18"` | `max_age = 18` |

#### Country Detection (Dynamic)

Country names are resolved dynamically using the **`pycountry`** library. The parser iterates over all entries in `pycountry.countries` and checks if any country's full name appears in the query. If found, it maps to the ISO 3166-1 alpha-2 code:

```python
for country in pycountry.countries:
    if country.name.lower() in q:
        filters["country_id"] = country.alpha_2
        break
```

This approach supports **all 249 countries** without maintaining a hardcoded mapping.

### Example Queries

| Natural Language Query | Parsed Filters |
|---|---|
| `"Show me all females from Nigeria"` | `gender=female`, `country_id=NG` |
| `"Male adults above 30"` | `gender=male`, `age_group=adult`, `min_age=30` |
| `"Teenagers from Japan"` | `age_group=teenager`, `country_id=JP` |
| `"Young males below 20"` | `gender=male`, `min_age=16`, `max_age=20` |
| `"Senior females"` | `gender=female`, `age_group=senior` |

### Error Handling

- If the query string is empty or whitespace-only → `400: "Missing search query"`
- If no tokens can be matched from the query → `400: "Unable to interpret query"`

---

## Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/)
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **External API Interaction**: [HTTPX](https://www.python-httpx.org/)
- **Validation**: [Pydantic](https://docs.pydantic.dev/)
- **Auth**: JWT (HS256) + GitHub OAuth 2.0 with PKCE
- **Country Resolution**: [pycountry](https://pypi.org/project/pycountry/)

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/edenis00/stageone.git
cd stageone
```

### 2. Set up a Virtual Environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root directory (refer to `.env.sample`):
```env
DATABASE_URL="postgresql://username:password@localhost:5432/hng_stageone"

GENDERIZE_URL=https://api.genderize.io
AGIFY_URL=https://api.agify.io
NATIONALIZE_URL=https://api.nationalize.io

SECRET_KEY=your-secret-key
ALGORITHM="HS256"
ACCESS_TOKEN_TIME=3
REFRESH_TOKEN_TIME=5

GITHUB_CLIENT_ID="your-github-client-id"
GITHUB_REDIRECT_URI="your-github-redirect-uri"
GITHUB_CLIENT_SECRET="your-github-client-secret"
```

### 5. Database Migrations
```bash
alembic upgrade head
```

---

## Running the Application

Start the development server:
```bash
uvicorn app.main:app --reload
```
The API will be accessible at `http://localhost:8000`.

Interactive documentation:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/auth/github` | Public | Initiate GitHub OAuth login (supports PKCE) |
| `GET` | `/auth/github/callback` | Public | GitHub OAuth callback — exchanges code for tokens |
| `POST` | `/auth/refresh` | Public | Rotate refresh token, get new access + refresh tokens |
| `POST` | `/auth/logout` | Public | Revoke a refresh token |
| `POST` | `/api/profiles` | Admin | Create a profile (or return existing) |
| `GET` | `/api/profiles` | Authenticated | List all profiles with advanced filters |
| `GET` | `/api/profiles/search` | Authenticated | Natural language profile search |
| `GET` | `/api/profiles/{id}` | Authenticated | Get a specific profile by ID |
| `DELETE` | `/api/profiles/{id}` | Admin | Delete a profile by ID |
| `GET` | `/api/profiles/export` | Public | Export profiles as CSV |

### Rate Limits

| Scope | Limit |
|---|---|
| Auth endpoints (`/auth/*`) | 10 requests / minute / IP |
| General endpoints | 60 requests / minute / IP |

---

## External Integrations

- **[Genderize.io](https://genderize.io/)** — Predicts gender based on a name
- **[Agify.io](https://agify.io/)** — Estimates age based on a name
- **[Nationalize.io](https://nationalize.io/)** — Predicts nationality based on a name
- **[GitHub OAuth](https://docs.github.com/en/apps/oauth-apps)** — User authentication provider

---

## License
MIT
