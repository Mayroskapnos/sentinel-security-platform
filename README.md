# SENTINEL

**Security Monitoring & Attack Detection Platform**

SENTINEL is an experimental security monitoring and Purple Team platform designed for controlled environments. It currently provides persistent asset inventory, normalized security-event storage, investigation workflows, and database-backed operational dashboards.

> Current status: **Milestone 1 — SENTINEL Core**. Detection, alerts, incidents, live telemetry, MITRE ATT&CK mapping, the attack simulator, and the corporate lab are intentionally future milestones.

## What is SENTINEL?

SENTINEL is a portfolio-grade exploration of the architecture behind SIEM, EDR/XDR, incident-response, and network-monitoring products. It is not a production SIEM and contains no functionality for targeting external systems.

## Current features

- Persistent PostgreSQL Asset and SecurityEvent domain models
- SQLAlchemy 2.x async data access with constrained, indexed schemas
- Alembic-managed schema lifecycle; application startup never calls `create_all`
- Versioned assets and normalized-events APIs with validation, filters, and bounded pagination
- Database-side dashboard summary and aggregation queries
- Idempotent demo seeding with 5 lab assets and 180 coherent historical events
- Searchable Assets workspace and detailed asset profiles with recent activity
- Filterable Events investigation table and safe JSON evidence drawer
- Recharts activity, severity, event-type, and active-asset visualizations
- Explicit loading, error, and empty states through TanStack Query
- Structured JSON logging and structured API errors
- Loopback-bound Docker services running as unprivileged users

## Architecture

```mermaid
flowchart LR
    UI[React dashboard] -->|same-origin /api/v1| Proxy[Nginx]
    Proxy --> Routes[FastAPI routes]
    Routes --> Services[Application services]
    Services --> Repositories[Query repositories]
    Repositories --> DB[(PostgreSQL 16)]
    Normalizer[Event normalizer] --> Services
    Alembic[Alembic migrations] --> DB
    Seed[Deterministic demo seed] --> DB
```

The frontend never calculates security totals by downloading the event table. Lists are filtered and paginated in SQL, and dashboard aggregates are produced by dedicated database queries.

See [Architecture](docs/architecture.md), [API Reference](docs/api.md), and [Security Model](docs/security-model.md).

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Recharts |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, Uvicorn |
| Database | PostgreSQL 16 |
| Runtime | Docker, Docker Compose, Nginx |
| Quality | pytest, Ruff, ESLint, Prettier, strict TypeScript, GitHub Actions |

## Quick start

Requirements:

- Docker Desktop with Docker Compose
- Ports `3000`, `8000`, and `5432` available on localhost, or customized in `.env`

No local PostgreSQL installation is required.

```bash
docker compose up --build -d
docker compose exec -T backend python -m app.cli.seed
```

The backend applies `alembic upgrade head` before starting. Seeding is explicit and idempotent: rerunning it updates the five demo assets and does not duplicate its 180 deterministic events.

PowerShell uses the same commands:

```powershell
docker compose up --build -d
docker compose exec -T backend python -m app.cli.seed
```

Open:

- Dashboard: <http://localhost:3000>
- API health: <http://localhost:8000/api/v1/health>
- OpenAPI documentation: <http://localhost:8000/api/docs>

The Compose defaults work without an `.env` file. Copy `.env.example` to `.env` to customize local values.

## Demo data commands

```bash
# Apply outstanding migrations manually
docker compose exec -T backend alembic upgrade head

# Synchronize five assets and add missing deterministic events
docker compose exec -T backend python -m app.cli.seed

# Replace only the 180 deterministic demo events, preserving other records
docker compose exec -T backend python -m app.cli.seed --reset
```

Equivalent Make targets are `make migrate`, `make seed`, `make demo`, and `make reset`.

The demo inventory contains:

| Hostname | Type | Zone | Address |
| --- | --- | --- | --- |
| `web-server` | Web server | DMZ | `10.10.10.10` |
| `employee-01` | Workstation | Employee | `10.10.20.10` |
| `employee-02` | Workstation | Employee | `10.10.20.11` |
| `admin-server` | Server | Server | `10.10.30.10` |
| `database` | Database | Server | `10.10.30.20` |

These are database records only. Milestone 1 does not create lab containers.

## Local development

Start PostgreSQL, prepare the backend, migrate, and run the API:

```bash
docker compose up -d postgres
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+asyncpg://sentinel:sentinel_dev_only_change_me@localhost:5432/sentinel
alembic upgrade head
python -m app.cli.seed
uvicorn app.main:app --reload
```

PowerShell equivalent:

```powershell
docker compose up -d postgres
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:DATABASE_URL = 'postgresql+asyncpg://sentinel:sentinel_dev_only_change_me@localhost:5432/sentinel'
alembic upgrade head
python -m app.cli.seed
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Vite runs at <http://localhost:5173> and proxies `/api` to port `8000`.

## Quality checks

```bash
cd backend
ruff check .
ruff format --check .
pytest
alembic check

cd ../frontend
npm run lint
npm run typecheck
npm run build
npm run format:check

cd ..
docker compose config --quiet
```

Backend tests use an isolated in-memory database and never depend on manually seeded data. Migration validation is also run against PostgreSQL in CI.

## Security model

All published ports bind to `127.0.0.1`. The event API accepts normalized defensive telemetry but performs no collection, scanning, detection, or offensive action. Future simulator work will target only allow-listed SENTINEL lab containers on isolated Docker networks.

## Roadmap

1. **SENTINEL Core — complete:** persistent assets/events, normalized ingestion, APIs, investigation UI, and dashboard aggregates
2. **Live Telemetry:** ingestion producer and WebSocket updates
3. **Detection Engine:** deterministic YAML rules and alerts
4. **Corporate Docker Lab:** isolated enterprise service simulations
5. **Attack Simulator:** safe, allow-listed scenarios
6. **Network Topology:** backend-driven React Flow graph
7. **Incident Correlation:** timelines and multi-stage breach scenario
8. **MITRE ATT&CK Experience:** tactics, techniques, and attack progression

## Project motivation

The project demonstrates defensive security concepts and full-stack engineering in one reproducible environment. Its focus is explainable data flows, safe lab isolation, and maintainable implementation rather than exaggerated claims or opaque automation.

## License

MIT — see [LICENSE](LICENSE).
