# SENTINEL

**Security Monitoring & Attack Detection Platform**

SENTINEL is an experimental security monitoring and Purple Team platform designed for controlled environments. The project is being built incrementally toward collecting lab telemetry, applying deterministic detections, correlating incidents, mapping behavior to MITRE ATT&CK, and visualizing activity in real time.

> Current status: **Milestone 0 — Project Bootstrap**. The React control plane, FastAPI service, PostgreSQL connectivity, container runtime, and CI foundation are implemented. Security telemetry and detection features intentionally begin in later milestones.

## What is SENTINEL?

SENTINEL is a portfolio-grade exploration of the architecture behind SIEM, EDR/XDR, incident-response, network-monitoring, and Purple Team platforms. It is not represented as a production SIEM and does not contain tooling for targeting external systems.

## Implemented foundation

- Responsive React 19 and TypeScript dashboard shell
- Vite, Tailwind CSS, React Router, TanStack Query, and Lucide icons
- Versioned FastAPI endpoint at `/api/v1/health`
- Real asynchronous PostgreSQL connectivity check through SQLAlchemy
- Healthy, loading, and degraded states in the browser
- Structured JSON backend logging and structured validation errors
- Docker Compose startup with health-aware service ordering
- Loopback-only published ports and unprivileged application containers
- Ruff, pytest, ESLint, strict TypeScript, Prettier, and GitHub Actions

## Architecture

```mermaid
flowchart LR
    UI[React dashboard] -->|/api/v1| Nginx[Nginx reverse proxy]
    Nginx --> API[FastAPI]
    API -->|async SQLAlchemy| DB[(PostgreSQL)]
```

The frontend makes environment-neutral, same-origin requests. In Docker, Nginx forwards `/api` to FastAPI; in local Vite development, the Vite proxy forwards the same path. The health endpoint runs a real `SELECT 1` query before reporting PostgreSQL as connected.

See [Architecture](docs/architecture.md) and [Security Model](docs/security-model.md) for details.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router |
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Uvicorn |
| Database | PostgreSQL 16 |
| Runtime | Docker, Docker Compose, Nginx |
| Quality | pytest, Ruff, ESLint, Prettier, strict TypeScript, GitHub Actions |

## Quick start

Requirements:

- Docker Desktop with Docker Compose
- Ports `3000`, `8000`, and `5432` available on localhost, or customized in `.env`

No local PostgreSQL installation is required.

```bash
docker compose up --build
```

The Compose file has safe development defaults, so creating `.env` is optional. To customize them:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Open:

- Dashboard: <http://localhost:3000>
- API health: <http://localhost:8000/api/v1/health>
- OpenAPI documentation: <http://localhost:8000/api/docs>

Stop the stack with `docker compose down`. To also remove the local database volume, use `docker compose down --volumes`; this permanently deletes SENTINEL's development database data.

## Development without a full container rebuild

Start PostgreSQL:

```bash
docker compose up -d postgres
```

Create a Python environment and start the backend. Use a host database URL because the Compose service name `postgres` resolves only inside Docker:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
DATABASE_URL=postgresql+asyncpg://sentinel:sentinel_dev_only_change_me@localhost:5432/sentinel uvicorn app.main:app --reload
```

PowerShell equivalent:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:DATABASE_URL = 'postgresql+asyncpg://sentinel:sentinel_dev_only_change_me@localhost:5432/sentinel'
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server is available at <http://localhost:5173> and proxies API calls to port `8000`.

## Quality checks

```bash
cd backend
ruff check .
ruff format --check .
pytest

cd ../frontend
npm run lint
npm run typecheck
npm run build

cd ..
docker compose config --quiet
```

Common Make targets are available on systems with `make`: `make up`, `make down`, `make logs`, `make test`, `make lint`, `make build`, and `make config`. The direct commands above are the supported Windows equivalents.

## Security model

All published container ports bind to `127.0.0.1`. The future attack simulator will target only dedicated SENTINEL lab containers on isolated Docker networks. SENTINEL will not provide arbitrary public scanning, credential theft, malware, persistence, evasion, or external attack functionality.

## Roadmap

1. **SENTINEL Core:** database models, Alembic, assets/events APIs, normalization, and seeded data
2. **Live Telemetry:** ingestion, simulated producer, and WebSockets
3. **Detection Engine:** deterministic YAML rules and alerts
4. **Corporate Docker Lab:** isolated enterprise service simulations
5. **Attack Simulator:** safe, allow-listed scenario execution
6. **Network Topology:** backend-driven React Flow graph
7. **Incident Correlation:** timelines and multi-stage breach scenario
8. **MITRE ATT&CK Experience:** tactics, techniques, and attack progression

## Project motivation

The project demonstrates defensive security concepts and full-stack engineering in one reproducible environment. Its focus is explainable detections, observable data flows, safe lab isolation, and maintainable implementation rather than exaggerated claims or opaque automation.

## License

MIT — see [LICENSE](LICENSE).
