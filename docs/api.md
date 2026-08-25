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
- `source`
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

Creates one normalized event through the shared ingestion boundary. Ports are constrained to 0-65535, IPs are validated, and timestamps must include timezone information. After commit it is broadcast and evaluated exactly once. Machine producers should normally use the telemetry boundary. When `COLLECTOR_API_KEY` is configured, this route and the telemetry POST require `X-Sentinel-Collector-Key`.

## Live telemetry

### `POST /api/v1/telemetry/events`

Validates, normalizes, resolves, persists, broadcasts, and then evaluates one machine-generated event. The response is the committed `SecurityEventResponse`, including its database UUID, with `201 Created`. A rule failure is isolated and cannot roll back that event.

Compose configures the corporate collector to send `X-Sentinel-Collector-Key`. A missing or invalid key returns `401 COLLECTOR_AUTHENTICATION_FAILED`. The check is optional in configurations where `COLLECTOR_API_KEY` is unset.

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

`data` contains the complete `SecurityEventResponse`; the shortened example highlights its identifying fields. Committed alerts use the same versioned envelope with `type: alert_created` or `type: alert_updated` and a complete `AlertResponse`. Messages are versioned, browser origins are allow-listed, and disconnected clients are removed independently. The socket does not replay missed messages; clients refetch REST data after reconnecting.

## Alerts

### `GET /api/v1/alerts`

Returns newest-first alert pages. Filters are `severity`, `status`, external `rule_id`, `asset_id`, `source_ip`, `destination_ip`, `username`, `active_only`, `start_time`, `end_time`, `page`, and `page_size` (maximum 100).

### `GET /api/v1/alerts/{alert_id}`

Returns alert context, rule and asset references, ATT&CK mapping, priority score, explainable evidence metadata, and compact supporting SecurityEvents. Raw and normalized payload bodies remain available through each event's API rather than being duplicated in the alert response.

### `PATCH /api/v1/alerts/{alert_id}`

Accepts `{"status": "investigating"}`, `resolved`, or `false_positive` subject to validated transitions. Resolved and false-positive alerts stop contributing to asset risk. Reopening uses `investigating`.

## Detection rules

### `GET /api/v1/rules`

Returns synchronized rules with filters for `enabled`, `rule_type`, `severity`, `event_type`, `search`, and pagination.

### `GET /api/v1/rules/{rule_id}`

The path ID is the rule's database UUID. The response also carries the stable external identifier such as `DET-SSH-001`.

### `PATCH /api/v1/rules/{rule_id}`

Accepts only a strict boolean `enabled` field. Changes are read directly during future event evaluation; existing alerts are retained.

## Dashboard

### `GET /api/v1/dashboard/summary`

Returns total assets, online assets, high-risk assets, events today, events in the last hour, and active open/critical/high alert counts.

### `GET /api/v1/dashboard/activity`

Accepts `hours` from 1 through 168 (default 72) and returns hourly counts, severity counts, event-type counts, and most-active assets.

## Corporate lab

### `GET /api/v1/lab/status`

Returns Corporate Lab v0.1 status inferred from recent real-lab telemetry. It includes overall `running`, `degraded`, or `offline` state; collector activity; the five canonical assets; telemetry freshness; and supported source freshness. It does not query Docker or claim that a reporting service is secure.

## Deployment warning

Incident correlation and active response are not implemented. The local shared collector key is not production authentication. Production use requires TLS, independently authenticated collectors, key rotation, durable queuing, retention controls, and cross-instance pub/sub.
