# How to Run SENTINEL

SENTINEL is an experimental security observability and Purple Team platform intended for its bundled, isolated Docker Corporate Lab. This guide takes a new user from cloning the repository to running the flagship demonstration.

## Requirements

- Git
- Docker Desktop, or Docker Engine with Docker Compose v2
- Approximately 4 GB of free memory for the full 11-container stack
- Loopback ports `3000`, `8000`, `5432`, and `8081` available, or changed in `.env`

Docker is sufficient for normal use. Local Python and Node.js installations are needed only for host-side development and validation.

## 1. Clone the Repository

```bash
git clone https://github.com/Mayroskapnos/sentinel-security-platform.git
cd sentinel-security-platform
```

## 2. Create the Environment File

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```bash
cp .env.example .env
```

The defaults are for local development. The optional Investigation Assistant is disabled by default; leave it disabled unless you intentionally configure either the local mock or an external provider. Never commit `.env` or a real API key.

## 3. Start SENTINEL

```bash
docker compose up --build -d
```

The first build may take several minutes. Backend startup applies Alembic migrations and synchronizes the repository-defined detection rules and five canonical lab Assets. It does not silently add historical demo events.

## 4. Check Container Health

```bash
docker compose ps
```

Wait for all 11 services to report healthy. The main frontend/application container is named exactly `sentinel`; its Compose service key remains `frontend`.

## 5. Open SENTINEL

- Frontend: <http://127.0.0.1:3000>
- Backend health: <http://127.0.0.1:8000/api/v1/health>
- OpenAPI documentation: <http://127.0.0.1:8000/api/docs>
- Corporate Lab portal: <http://127.0.0.1:8081>

The health response should report SENTINEL version `1.0.0`.

## 6. Verify the System

Open **System** and confirm that the API and database are healthy, Corporate Lab collector telemetry is active, the Attack Simulator is available, and the Correlation Engine is active. The Investigation Assistant should show disabled/unavailable unless you configured it.

Open **Detection Rules** and verify the five repository-defined rules are enabled. SENTINEL v1.0 does not display a separate Detection Engine health tile; persisted rule state and observed Alerts are the authoritative validation path.

## 7. Run the Flagship Demo

1. Open **Attack Simulator**.
2. Select `SCN-005 - Multi-Stage Enterprise Security Exercise`.
3. Start the fixed Corporate Lab-only scenario.
4. Watch genuine lab telemetry move through collection, ingestion, detection, and attribution.
5. Open **Alerts** and inspect the observed detections.
6. Open the generated correlated Incident.
7. Review the deterministic **Attack Story** and evidence links.
8. Open the Incident on the **Attack Map**.
9. Optionally generate an Investigation Assistant analysis.
10. Export the Incident as an HTML or PDF report.

Expected detections can be suppressed by their existing cooldowns if the same demo ran recently. The Attack Simulator operates only against allow-listed targets in the bundled Corporate Lab and does not accept arbitrary addresses, commands, payloads, SQL, or external targets.

## 8. Optional Local AI Demo

To demonstrate the deterministic mock Investigation Assistant without an API key or external request, set these values in `.env`:

```text
SENTINEL_AI_ENABLED=true
SENTINEL_AI_PROVIDER=mock
SENTINEL_AI_MODEL=sentinel-mock-v1
SENTINEL_AI_API_KEY=
```

Recreate the backend and frontend services so the updated environment is loaded:

```bash
docker compose up -d --force-recreate backend frontend
```

The mock provider runs locally and sends no Incident evidence outside SENTINEL.

## 9. Optional OpenAI Provider

External OpenAI analysis is optional and is not required for monitoring, detection, correlation, the Attack Map, or reporting. Set the following in `.env`, using a Responses API model available to your account:

```text
SENTINEL_AI_ENABLED=true
SENTINEL_AI_PROVIDER=openai
SENTINEL_AI_MODEL=YOUR_RESPONSES_API_MODEL
SENTINEL_AI_API_KEY=YOUR_OPENAI_API_KEY
SENTINEL_AI_BASE_URL=https://api.openai.com/v1
```

Then recreate the affected services:

```bash
docker compose up -d --force-recreate backend frontend
```

Never commit the populated `.env`. A configured external provider receives selected, bounded, redacted Incident evidence and bounded Q&A content. This creates an external privacy and retention boundary; review your provider and organizational data policies before enabling it.

## 10. Stop SENTINEL

```bash
docker compose down
```

This stops and removes the containers and Compose networks while preserving named volumes and their PostgreSQL, telemetry checkpoint, and lab data. Do not add `--volumes` for normal shutdown.

## 11. Start It Again Later

```bash
docker compose up -d
```

Use `docker compose ps` to wait for all services to become healthy again.

## 12. View Logs

All services:

```bash
docker compose logs -f
```

Useful service-specific examples:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f sentinel-collector
```

Use Compose service names for commands even though the frontend container itself is named `sentinel`.

## 13. Reset the Demo

The guarded development reset clears generated SENTINEL telemetry, Alerts, Incidents, network relationships, scenario runs, analyses, and Q&A messages:

```bash
docker compose exec -T backend python -m app.cli.demo_reset --confirm-development-reset
```

This command refuses non-development environments and requires the explicit confirmation flag. It preserves canonical Assets, Detection Rules, and Alembic migration history. Treat it as destructive to generated local security/demo records.

## 14. Troubleshooting

### Port already in use

Compose reports which binding failed. The default published ports are `3000`, `8000`, `5432`, and `8081`.

Windows PowerShell can show listeners with:

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 3000,8000,5432,8081
```

Linux commonly provides:

```bash
ss -ltnp | grep -E ':(3000|8000|5432|8081)\b'
```

macOS commonly provides:

```bash
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(3000|8000|5432|8081)\b'
```

Stop the conflicting application or change `FRONTEND_PORT`, `API_PORT`, `POSTGRES_PORT`, or `LAB_WEB_PORT` in `.env`. If the frontend port changes, also update `FRONTEND_URL` and `WEBSOCKET_ALLOWED_ORIGINS`.

### Containers not healthy

```bash
docker compose ps
docker compose logs
```

For a narrower view, inspect `backend`, `postgres`, `sentinel-collector`, or the service reported unhealthy.

### Rebuild after changes

```bash
docker compose up --build -d
```

### Start from a clean development environment

> **Destructive:** the following command permanently deletes all SENTINEL platform and Corporate Lab named volumes, including local events, Alerts, Incidents, analyses, scenario history, and database state. Use it only when a complete local reset is intentional.

```bash
docker compose down --volumes --remove-orphans
docker compose up --build -d
```

## Security Notice

SENTINEL is an experimental local/lab security platform. Do not expose the development deployment directly to the public Internet. The bundled simulator is designed only for SENTINEL's isolated Corporate Lab. SENTINEL v1.0 does not provide production authentication, RBAC, TLS termination, high availability, or production-hardening guarantees.

## Quick Demo Summary

```text
Clone
  ↓
Create .env
  ↓
docker compose up --build -d
  ↓
Open SENTINEL
  ↓
Run SCN-005
  ↓
Investigate Incident
  ↓
Attack Map
  ↓
Optional AI Analysis
  ↓
Export Report
```
