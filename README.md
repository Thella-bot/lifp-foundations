# LIFP - Lesotho Inclusive Finance Platform

[![CI](https://github.com/Thella-bot/lifp-foundations/actions/workflows/ci.yml/badge.svg)](https://github.com/Thella-bot/lifp-foundations/actions/workflows/ci.yml)

A cloud-native, modular platform that bridges the credit gap for MSMEs and individual users in Lesotho through alternative credit scoring, digital identity verification, and mobile-first financial tools.

---

## Architecture

```text
Clients:
- LIFP PWA (React + Vite) on :5173
- USSD Gateway (Africa's Talking) on :8004
- Lender Dashboard (API currently on :8003, frontend coming soon)

Core Services:
- ACSE (credit scoring) on :8001
- Identity Service (e-KYC + consent) on :8002
- Lender Service on :8003
- USSD Service on :8004

Data Layer:
- PostgreSQL
- Redis
```

## Services

| Service | Port | Description |
|---|---|---|
| `acse_service` | 8001 | AI credit scoring engine (XGBoost + SHAP) |
| `identity_service` | 8002 | e-KYC bridge via MOSIP |
| `lender_service` | 8003 | Lender dashboard API |
| `ussd_service` | 8004 | USSD gateway (Africa's Talking) |
| `pwa` | 5173 | Progressive Web App (React + Vite) |

---

## Quick Start

### 1. Prerequisites

- Docker 24+ and Docker Compose v2
- Node.js 20+ (for PWA dev only)
- Git

### 2. Clone and configure

```bash
git clone https://github.com/Thella-bot/lifp-foundations.git
cd lifp-foundations

cp .env.example .env
# Edit .env - at minimum set POSTGRES_PASSWORD and SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start all services

```bash
docker compose up --build
```

This runs in order:
1. PostgreSQL + Redis (with health checks)
2. `migrate` - Alembic migrations to latest schema
3. `data_setup` - seeds 250 MSME + 250 individual synthetic users
4. All four API services
5. PWA dev server

### 4. Verify

```bash
curl http://localhost:8001/health   # {"status":"ok","service":"acse"}
curl http://localhost:8002/health   # {"status":"ok","service":"identity"}
curl http://localhost:8003/health   # {"status":"ok","service":"lender"}
curl http://localhost:8004/health   # {"status":"ok","service":"ussd"}
```

Open **http://localhost:5173** for the PWA.

### 5. API Docs

| Service | Swagger UI |
|---|---|
| ACSE | http://localhost:8001/docs |
| Identity | http://localhost:8002/docs |
| Lender | http://localhost:8003/docs |
| USSD | http://localhost:8004/docs |

---

## Development

### Run tests

```bash
# All services (from repo root)
PYTHONPATH=. SECRET_KEY=test-secret-key-32chars-padding!! \
  pytest acse_service/tests/ identity_service/tests/ \
         lender_service/tests/ ussd_service/tests/ -v

# Single service
PYTHONPATH=. SECRET_KEY=test-secret-key-32chars-padding!! \
  pytest acse_service/tests/ -v
```

### Database migrations

```bash
# Create a new migration after changing shared/models.py
docker compose run --rm migrate \
  alembic -c migrations/alembic.ini revision --autogenerate -m "your description"

# Apply migrations
docker compose run --rm migrate \
  alembic -c migrations/alembic.ini upgrade head

# Roll back one step
docker compose run --rm migrate \
  alembic -c migrations/alembic.ini downgrade -1
```

### Re-seed the database

```bash
docker compose run --rm data_setup
```

### PWA dev (without Docker)

```bash
cd pwa
npm install
npm run dev
```

---

## Project Structure

```text
lifp-foundations/
|- shared/                   # Shared ORM models, DB engine, JWT security
|  |- models.py              # Single source of truth for all tables
|  |- db.py                  # SQLAlchemy engine + session factory
|  `- security.py            # JWT verification (used by all services)
|
|- acse_service/             # Credit scoring (FastAPI + XGBoost + SHAP)
|  |- main.py
|  |- model.py               # ModelManager with SHAP wired
|  `- tests/
|
|- identity_service/         # e-KYC + consent management (FastAPI + MOSIP)
|  |- main.py
|  |- auth.py
|  `- tests/
|
|- lender_service/           # Lender dashboard API (FastAPI)
|  |- main.py
|  `- tests/
|
|- ussd_service/             # USSD gateway (Africa's Talking)
|  |- main.py
|  `- tests/
|
|- pwa/                      # Progressive Web App (React + TypeScript + Vite)
|  |- src/
|  |  |- api/client.ts       # Typed API client
|  |  |- db/localStore.ts    # IndexedDB offline store
|  |  `- pages/              # Login, Dashboard
|  `- vite.config.ts         # PWA manifest + Workbox caching
|
|- migrations/               # Alembic schema migrations
|  `- versions/
|     `- 0001_initial_schema.py
|
|- docker-compose.yml
|- .env.example
`- .github/workflows/ci.yml # Tests + Docker build + security scan + PWA build
```

---

## User Tracks

LIFP serves two distinct user types:

| Feature | MSME (Business) | Individual |
|---|---|---|
| Finance tracking | Business income/expense + inventory | Personal income/expense |
| Transaction types | Includes merchant payments | Standard + bill payments |
| Credit scoring | Business cash-flow model | Personal behavior model |
| Loan products | Business working capital | Consumer / personal loans |
| `user_type` value | `msme` | `individual` |

The `user_type` field flows through: user registration -> feature generation -> model prediction -> loan product filtering.

---

## Security Notes

- **UIN is never stored.** The national ID is SHA-256 hashed on receipt; only `internal_id` (the hash) is persisted and appears in JWTs.
- **Consent is DB-persisted.** All consent records live in PostgreSQL - not in memory.
- **CORS is locked** to `CORS_ORIGINS` env var. Never hardcoded wildcard in production.
- **No default credentials.** Missing `SECRET_KEY` or DB vars raise a `RuntimeError` at startup.
- **RS256 upgrade path** is documented in `shared/security.py` for production deployment.

---

## Roadmap

- [ ] Real MOSIP e-Signet OAuth2 integration (replace mock `/v1/auth/token`)
- [ ] MLflow experiment tracking + model registry
- [ ] Airflow DAG replacing one-shot `init_db.py` seeder
- [ ] Lender React dashboard (frontend)
- [ ] USSD phone->internal_id mapping table
- [ ] LeRIMA collateral API integration
- [ ] Push notifications (FCM/SMS) for score changes
- [ ] Fairness monitoring dashboard (fairlearn + Grafana)
