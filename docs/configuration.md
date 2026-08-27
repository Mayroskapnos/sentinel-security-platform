# Configuration

SENTINEL reads configuration from environment variables. Docker Compose loads an optional root `.env`; the backend also reads `.env` while running directly. Copy `.env.example` and keep the resulting `.env` untracked.

## Core runtime

| Variable                    | Default                  | Purpose                                            |
| --------------------------- | ------------------------ | -------------------------------------------------- |
| `APP_VERSION`               | `1.0.0`                  | Version returned by health and shown in System.    |
| `SENTINEL_BUILD_SHA`        | empty                    | Optional release commit identifier.                |
| `SENTINEL_BUILD_TIME`       | empty                    | Optional ISO 8601 build timestamp.                 |
| `SENTINEL_ENV`              | `development`            | Runtime environment; gates destructive demo reset. |
| `DATABASE_URL`              | local Compose PostgreSQL | SQLAlchemy async connection string.                |
| `FRONTEND_URL`              | `http://localhost:3000`  | Comma-separated HTTP CORS origins.                 |
| `WEBSOCKET_ALLOWED_ORIGINS` | local UI origins         | Explicit browser WebSocket origin allow-list.      |
| `LOG_LEVEL`                 | `INFO`                   | Backend structured-log threshold.                  |

## Telemetry and lab

| Variable                      | Default                  | Purpose                                        |
| ----------------------------- | ------------------------ | ---------------------------------------------- |
| `COLLECTOR_API_KEY`           | development placeholder  | Shared local collector ingestion key.          |
| `TELEMETRY_MAX_BODY_BYTES`    | `262144`                 | Maximum telemetry request body.                |
| `LAB_TELEMETRY_STALE_SECONDS` | `120`                    | Freshness threshold for lab status.            |
| `LAB_ACTIVITY_INTERVAL`       | `45`                     | Seconds between quiet background lab activity. |
| `LAB_*_PASSWORD`              | development placeholders | Fictional bundled-lab credentials only.        |

The example credentials are not suitable for shared or production environments. The local API has no user authentication or RBAC.

## Simulator

`SENTINEL_SIMULATOR_ENABLED` enables only repository-defined, allow-listed scenarios against bundled logical lab targets. `SENTINEL_SIMULATION_KEY` authenticates the fixed-action broker and must differ from the collector key. Action, scenario, and settle timeouts are bounded by application validation.

The simulator cannot accept a hostname, address, URL, port, command, SQL statement, payload, or external target from a caller.

## Investigation Assistant

AI is optional and disabled by default:

```text
SENTINEL_AI_ENABLED=false
SENTINEL_AI_PROVIDER=
SENTINEL_AI_MODEL=
SENTINEL_AI_API_KEY=
```

For a no-network demonstration, use provider `mock` and model `sentinel-mock-v1`. Provider `openai` sends a bounded, redacted Incident context to the configured external endpoint. Keep provider keys only in `.env`; never put them in Compose YAML, source, logs, or screenshots. See [Investigation Assistant](investigation-assistant.md).

## Frontend

The production frontend normally uses same-origin `/api/v1` through Nginx. `VITE_API_BASE_URL` is compiled into the bundle. During Vite development, `VITE_DEV_API_PROXY` can change the local API proxy target.

## Published ports

Compose binds the frontend, backend API, platform PostgreSQL, and lab web gateway to `127.0.0.1` only. Defaults are `3000`, `8000`, `5432`, and `8081`. Changing a port does not add authentication or make public exposure safe.
