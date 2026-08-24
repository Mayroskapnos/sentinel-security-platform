# SENTINEL

**Security Monitoring & Attack Detection Platform**

SENTINEL is an experimental security monitoring and Purple Team platform for controlled environments. It provides persistent asset inventory, normalized security-event storage, live telemetry delivery, investigation workflows, and database-backed operational dashboards.

> Current status: **Milestone 2 - Live Telemetry**. Detection, alerts, incidents, MITRE ATT&CK mapping, attack simulation, and the corporate lab are future milestones.

## What is SENTINEL?

SENTINEL is a portfolio-grade exploration of the architecture behind SIEM, EDR/XDR, incident-response, and network-monitoring products. It is not a production SIEM and contains no functionality for targeting external systems.

## Current features

- Persistent PostgreSQL Asset and SecurityEvent domain models
- SQLAlchemy 2.x async data access with constrained, indexed schemas
- Alembic-managed schema lifecycle; application startup never calls `create_all`
- Versioned asset and event APIs with validation, filtering, and bounded pagination
- Dedicated telemetry ingestion with deterministic asset resolution and monotonic `last_seen`
- Typed WebSocket delivery after PostgreSQL commit, with browser-origin checks and per-client failure isolation
- Automatic frontend reconnection, missed-event REST recovery, ID deduplication, and live row cues
- Debounced dashboard and asset-detail updates through TanStack Query
- Safe bounded synthetic producer with single, stream, and burst modes
- Database-side dashboard summary and aggregation queries
- Idempotent demo seeding with five lab assets and 180 coherent historical events
- Searchable Assets, Asset Details, Events investigation, and safe JSON evidence views
- Structured JSON logging and structured API errors
- Loopback-bound Docker services running as unprivileged users

## Architecture

```mermaid
flowchart LR
    Producer[Synthetic producer] -->|POST telemetry| API[FastAPI]
    API --> Normalizer[Event normalizer]
    Normalizer --> Service[Security event service]
    Service --> DB[(PostgreSQL 16)]
    Service -->|after commit| WS[WebSocket manager]
    WS --> Proxy[Nginx]
    Proxy --> UI[React dashboard]
    UI -->|authoritative REST queries| Proxy
    Alembic[Alembic migrations] --> DB
    Seed[Deterministic demo seed] --> DB
```

PostgreSQL remains the source of truth. WebSockets provide low-latency delivery; REST refetches repair any gap after reconnection. See [Architecture](docs/architecture.md), [Telemetry](docs/telemetry.md), [API Reference](docs/api.md), and [Security Model](docs/security-model.md).

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Recharts |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, Uvicorn |
| Database | PostgreSQL 16 |
| Runtime | Docker, Docker Compose, Nginx |
| Quality | pytest, Ruff, Vitest, ESLint, Prettier, strict TypeScript, GitHub Actions |

## Quick start

Requirements:

- Docker Desktop with Docker Compose
- Ports `3000`, `8000`, and `5432` available on localhost, or customized in `.env`

```bash
docker compose up --build -d
docker compose exec -T backend python -m app.cli.seed
```

The backend applies `alembic upgrade head` before starting. Seeding is explicit and idempotent. The same commands work in PowerShell.

Open:

- Dashboard: <http://localhost:3000>
- Events: <http://localhost:3000/events>
- API health: <http://localhost:8000/api/v1/health>
- OpenAPI: <http://localhost:8000/api/docs>

The Compose defaults work without an `.env` file. Copy `.env.example` to `.env` to customize local values.

## Live telemetry

The development producer exercises the complete live path:

```text
Synthetic Producer -> Telemetry API -> Normalization -> PostgreSQL -> WebSocket -> React
```

With the stack seeded and `/events` open, run:

```bash
make telemetry
```

Windows alternative:

```powershell
python tools/telemetry_producer.py --mode stream --count 25 --interval 2
```

Other bounded modes:

```bash
python tools/telemetry_producer.py --mode single
python tools/telemetry_producer.py --mode burst --count 100
```

The producer targets the seeded hosts and emits synthetic development telemetry only. It does not collect endpoint data or simulate attacks. `Ctrl+C` stops a stream cleanly.

## Demo data

```bash
docker compose exec -T backend alembic upgrade head
docker compose exec -T backend python -m app.cli.seed
docker compose exec -T backend python -m app.cli.seed --reset
```

Equivalent Make targets are `make migrate`, `make seed`, `make demo`, and `make reset`.

| Hostname | Type | Zone | Address |
| --- | --- | --- | --- |
| `web-server` | Web server | DMZ | `10.10.10.10` |
| `employee-01` | Workstation | Employee | `10.10.20.10` |
| `employee-02` | Workstation | Employee | `10.10.20.11` |
| `admin-server` | Server | Server | `10.10.30.10` |
| `database` | Database | Server | `10.10.30.20` |

These are database records only. Milestone 2 does not create lab containers.

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

PowerShell activation and environment setup:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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

Vite runs at <http://localhost:5173> and proxies both HTTP and WebSocket `/api` traffic to port `8000`.

## Quality checks

```bash
cd backend
ruff check .
ruff format --check .
pytest
alembic check

cd ../frontend
npm ci
npm run lint
npm run typecheck
npm test
npm run format:check
npm run build
npm audit

cd ..
docker compose config --quiet
```

Backend tests use an isolated in-memory database. Migration validation runs against PostgreSQL in CI.

## Security model

Published services bind to `127.0.0.1`. The telemetry API accepts normalized defensive data but performs no collection, scanning, detection, or offensive action. WebSocket browser origins are allow-listed for local development. A real deployment must add collector authentication, TLS, and production ingress controls before exposing ingestion.

## Roadmap

1. **SENTINEL Core - complete:** persistent assets/events, normalized storage APIs, investigation UI, and dashboard aggregates
2. **Live Telemetry - complete:** dedicated ingestion, asset resolution, WebSocket delivery, live query updates, and synthetic producer
3. **Detection Engine:** deterministic rules and alerts
4. **Corporate Docker Lab:** isolated enterprise service simulations
5. **Attack Simulator:** safe, allow-listed scenarios
6. **Network Topology:** backend-driven graph
7. **Incident Correlation:** timelines and multi-stage breach scenario
8. **MITRE ATT&CK Experience:** tactics, techniques, and attack progression

## Project motivation

The project demonstrates defensive security concepts and full-stack engineering in one reproducible environment. Its focus is explainable data flows, safe lab isolation, and maintainable implementation rather than exaggerated claims or opaque automation.

## License

MIT - see [LICENSE](LICENSE).
