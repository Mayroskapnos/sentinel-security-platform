# SENTINEL API

The API is versioned under `/api/v1`. Interactive OpenAPI documentation is available at `/api/docs` while the backend is running.

## Response conventions

Collection endpoints return bounded pages:

```json
{
  "items": [],
  "page": 1,
  "page_size": 25,
  "total": 0,
  "pages": 0
}
```

Expected errors use:

```json
{
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "Requested asset does not exist."
  }
}
```

Validation failures use `VALIDATION_ERROR` with field details. IDs are UUIDs and timestamps are timezone-aware ISO 8601 values normalized to UTC.

## Health

### `GET /api/v1/health`

Checks the API process and PostgreSQL with `SELECT 1`. Returns `503` with `status: degraded` when the database is unavailable.

## Assets

### `GET /api/v1/assets`

Filters include `asset_type`, `status`, `network_zone`, `criticality`, `min_risk_score`, `search`, `page`, and `page_size` (maximum 100).

### `GET /api/v1/assets/{asset_id}`

Returns one asset or `ASSET_NOT_FOUND`.

### `POST /api/v1/assets`

Creates a validated asset. Hostname and IP are unique; risk, IP, MAC, and timestamp fields are validated.

### `PATCH /api/v1/assets/{asset_id}`

Applies supplied mutable fields. Hostname remains immutable.

## Security events

### `GET /api/v1/events`

Filters:

- `hostname`
- `asset_id`
- `event_type`
- `severity`
- `source_ip`
- `destination_ip`
- `username`
- `status`
- `start_time`
- `end_time`
- `page` (default 1)
- `page_size` (default 25, maximum 100)

Results are ordered newest first.

### `GET /api/v1/events/{event_id}`

Returns normalized fields, optional resolved asset reference, normalized data, and raw evidence.

### `POST /api/v1/events`

Creates one stored normalized event through the canonical event service. Ports are constrained to 0-65535, IPs are validated, and timestamps must include timezone information. This remains the stored-resource API; machine producers should use the telemetry boundary.

## Live telemetry

### `POST /api/v1/telemetry/events`

Validates, normalizes, resolves, persists, and then broadcasts one machine-generated event. The response is the committed `SecurityEventResponse`, including its database UUID, with `201 Created`.

```json
{
  "timestamp": "2026-08-24T14:22:17Z",
  "event_type": "authentication",
  "source": "linux_auth",
  "source_ip": "10.10.50.2",
  "destination_ip": "10.10.20.10",
  "hostname": "employee-01",
  "username": "demo-user",
  "action": "ssh_login",
  "status": "failed",
  "severity": "low",
  "normalized_data": {
    "authentication_method": "password",
    "service": "ssh"
  },
  "raw_event": {
    "message": "Failed password for demo-user"
  }
}
```

Asset matching order is explicit `asset_id`, hostname, then a unique match across destination/source IP. Conflicting IP matches and unknown assets remain unassociated; assets are never auto-created. A resolved asset's `last_seen` only moves forward. The event and asset update commit together.

The default maximum request body is 256 KiB. Nginx enforces the body limit and FastAPI rejects an oversized declared `Content-Length`. Schema failures return `422`. A database failure produces no WebSocket message.

### `WS /api/v1/ws/events`

Provides same-origin live delivery directly from FastAPI or through Nginx. The server sends a connection status envelope first:

```json
{
  "version": "1",
  "type": "telemetry_status",
  "timestamp": "2026-08-24T14:22:17Z",
  "data": {
    "status": "connected",
    "connected_clients": 1
  }
}
```

Committed events use:

```json
{
  "version": "1",
  "type": "security_event",
  "timestamp": "2026-08-24T14:22:17Z",
  "data": {
    "id": "c4eecaf4-5b7d-4e53-8200-2df79d91a012",
    "event_type": "authentication",
    "source": "linux_auth",
    "hostname": "employee-01",
    "action": "ssh_login",
    "status": "failed",
    "severity": "low"
  }
}
```

`data` contains the complete `SecurityEventResponse`; the shortened example highlights its identifying fields. Messages are versioned, browser origins are allow-listed, and disconnected clients are removed independently. The socket does not replay missed messages; clients refetch REST data after reconnecting.

## Dashboard

### `GET /api/v1/dashboard/summary`

Returns total assets, online assets, high-risk assets, events today, and events in the last hour.

### `GET /api/v1/dashboard/activity`

Accepts `hours` from 1 through 168 (default 72) and returns hourly counts, severity counts, event-type counts, and most-active assets.

## Deployment warning

No alert, detection, or incident endpoints are implemented in Milestone 2. The local telemetry endpoint has no collector authentication and must not be exposed publicly. Production use requires authenticated collectors, TLS, durable queuing, retention controls, and cross-instance pub/sub.
