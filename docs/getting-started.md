# Getting Started

## Requirements

- Docker Desktop or Docker Engine with Docker Compose v2
- Git
- Approximately 4 GB of free memory for the full 11-container stack
- Loopback ports `3000`, `8000`, `5432`, and `8081` available, or changed in `.env`

Python 3.12+ and Node.js 22 are needed only for host-side development and validation.

## Install and start

```bash
git clone https://github.com/Mayroskapnos/sentinel-security-platform.git
cd sentinel-security-platform
cp .env.example .env
docker compose up --build -d
docker compose ps
```

PowerShell:

```powershell
git clone https://github.com/Mayroskapnos/sentinel-security-platform.git
Set-Location sentinel-security-platform
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

The backend startup applies Alembic migrations and synchronizes repository-defined detection rules and the five canonical lab assets. It does not create schema through application models or silently seed historical events.

## Verify

```bash
curl --fail http://127.0.0.1:8000/api/v1/health
docker compose ps
```

Open <http://127.0.0.1:3000>. Health should report `1.0.0`; all 11 services should become healthy. The lab may need a short period to emit and collect its first telemetry.

## First demonstration

Open **Attack Simulator**, run `SCN-001`, and watch its Run Detail page. After the run reaches a terminal state, open the observed alert and correlated Incident. Use `SCN-005` for the complete multi-stage portfolio flow after suppression cooldowns have expired. See [Demo Guide](demo.md).

## Optional historical data

```bash
docker compose exec -T backend python -m app.cli.seed
```

This adds 180 deterministic synthetic historical events. It is separate from genuine service logs produced by the bundled lab.

## Stop

```bash
docker compose down
```

Named volumes persist. Do not add `--volumes` unless deleting all local database and lab state is intentional.

## Troubleshooting

- Port collision: change `FRONTEND_PORT`, `API_PORT`, `POSTGRES_PORT`, or `LAB_WEB_PORT` in `.env`.
- Lab still warming: inspect `docker compose ps` and `docker compose logs sentinel-collector`.
- Scenario unavailable: confirm simulator is enabled, expected rules are enabled, required assets are fresh, and no other run is active.
- AI unavailable: core monitoring remains operational; verify the optional variables separately.
- Report download fails: verify the Incident still exists and inspect backend logs for a structured error.

SENTINEL is a portfolio-grade experimental platform. It has no production user authentication, RBAC, TLS termination, retention policy, or multi-instance coordination; do not expose it to the public internet.
