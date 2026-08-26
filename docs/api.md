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
- `scenario_run_id`
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

Controlled scenario progress uses the same version `1` envelope with `simulation_started`, `simulation_step`, `simulation_finished`, `simulation_failed`, or `simulation_cancelled`. The data contains backend-owned `run_id`, `scenario_id`, status, current/total step, label, and message. These messages never replace SecurityEvents or Alerts.

Eligible known-endpoint telemetry can additionally emit `network_connection_updated`. Its compact data contains the persisted relationship ID, source/destination asset IDs, protocol, destination port, connection type, last observation, count, and last status. The browser invalidates and refetches the authoritative topology; it does not manufacture missing node or edge fields from the message.

Committed correlation changes emit `incident_created` or `incident_updated` with a compact Incident list item. Alert delivery precedes Incident delivery for the same ingestion path. REST remains authoritative and reconnect invalidates Incident queries.

## Alerts

### `GET /api/v1/alerts`

Returns newest-first alert pages. Filters are `severity`, `status`, external `rule_id`, `asset_id`, `source_ip`, `destination_ip`, `username`, `active_only`, `start_time`, `end_time`, `page`, and `page_size` (maximum 100).

### `GET /api/v1/alerts/{alert_id}`

Returns alert context, rule and asset references, ATT&CK mapping, priority score, explainable evidence metadata, and compact supporting SecurityEvents. Raw and normalized payload bodies remain available through each event's API rather than being duplicated in the alert response.

### `PATCH /api/v1/alerts/{alert_id}`

Accepts `{"status": "investigating"}`, `resolved`, or `false_positive` subject to validated transitions. Resolved and false-positive alerts stop contributing to asset risk. Reopening uses `investigating`.

Alert responses include a compact Incident reference when membership exists, or `null` otherwise.

## Incidents

### `GET /api/v1/incidents`

Returns most-recently-active Incident pages. Server-side filters are `severity`, `status`, `asset_id`, `scenario_run_id`, `confidence_min`, `start_time`, `end_time`, `search`, `page`, and `page_size` (maximum 100). Search matches Incident number, title, and affected Asset hostname.

### `GET /api/v1/incidents/{incident_id}`

Returns one efficient Incident document with Alert references, affected Assets, chronological story steps and supporting event IDs, observed ATT&CK techniques, persisted correlation explanations, optional ScenarioRun context, and bounded derived counts. It does not duplicate raw event bodies.

### `PATCH /api/v1/incidents/{incident_id}`

Updates `status` and/or nullable `assigned_to`. Status transitions are validated across `open`, `investigating`, `contained`, `resolved`, and `false_positive`. Normal Incident deletion, arbitrary public correlation, merge, split, and Alert removal are intentionally absent.

## Detection rules

### `GET /api/v1/rules`

Returns synchronized rules with filters for `enabled`, `rule_type`, `severity`, `event_type`, `search`, and pagination.

### `GET /api/v1/rules/{rule_id}`

The path ID is the rule's database UUID. The response also carries the stable external identifier such as `DET-SSH-001`.

### `PATCH /api/v1/rules/{rule_id}`

Accepts only a strict boolean `enabled` field. Changes are read directly during future event evaluation; existing alerts are retained.

## Dashboard

### `GET /api/v1/dashboard/summary`

Returns total assets, online assets, high-risk assets, events today, events in the last hour, active open/critical/high alert counts, and real open/critical Incident counts.

### `GET /api/v1/dashboard/activity`

Accepts `hours` from 1 through 168 (default 72) and returns hourly counts, severity counts, event-type counts, and most-active assets.

## Network and Attack Map

### `GET /api/v1/network/topology`

Returns one bulk graph document containing asset nodes, observed relationship edges, alert references, actual activity rows, observed mapped ATT&CK techniques, and summary counts. `window` accepts `5m`, `15m`, `1h`, `24h`, or `all` (default `15m`). Optional UUID parameters are `scenario_run_id`, `incident_id`, `asset_id`, and `alert_id`. Scenario and Incident scope are mutually exclusive.

With `scenario_run_id`, only explicitly attributed SecurityEvents create activity or edges; unrelated events and intended-but-unobserved targets are excluded. ATT&CK rows come only from Alerts joined through relational evidence and omit unmapped rules. Activity reads are capped at 5,000 rows and report `activity_truncated` honestly.

With `incident_id`, exact AlertEvent evidence for that Incident selects activities, Assets, relationships, Alerts, and techniques. Story text never creates topology.

### `GET /api/v1/network/connections`

Returns bounded pages of durable aggregate relationships, newest observation first. Filters are `source_asset_id`, `destination_asset_id`, `protocol`, `destination_port`, `start_time`, `page`, and `page_size` (maximum 100). Counts are observations contributing to a semantic source/destination/protocol/port/type identity, not inferred sessions.

## Corporate lab

### `GET /api/v1/lab/status`

Returns Corporate Lab v0.1 status inferred from recent real-lab telemetry. It includes overall `running`, `degraded`, or `offline` state; collector activity; the five canonical assets; telemetry freshness; and supported source freshness. It does not query Docker or claim that a reporting service is secure.

## Controlled Attack Simulator

### `GET /api/v1/simulator/status`

Returns configuration availability, `disabled`, `unavailable`, `idle`, or `running` state, and the active persistent run when present.

### `GET /api/v1/simulator/scenarios`

Lists repository-defined scenario metadata: ID, name, description, low-risk designation, estimated seconds, logical lab targets, expected rule IDs, and step count.

### `GET /api/v1/simulator/scenarios/{scenario_id}`

Adds the validated declarative steps. Definitions contain no raw infrastructure addresses or executable text.

### `POST /api/v1/simulator/run/{scenario_id}`

Starts a predefined scenario and accepts no request body or target parameters. It returns `202` with the persistent pending run. Preconditions include enabled configuration, available broker, online required lab assets, active collector, enabled expected rules, and no active run. Conflicts return `409 SCENARIO_ALREADY_RUNNING`; disabled/unavailable prerequisites return structured `503` errors.

### `GET /api/v1/simulator/runs`

Returns newest-first persistent history with bounded `page` and `page_size`. Each run includes step state, event/alert counts, expected-versus-observed detection rows, and attributed alert references.

### `GET /api/v1/simulator/runs/{run_id}`

Returns authoritative live or historical run detail. Counts and observations are computed server-side from `scenario_run_id` and relational alert evidence.

### `POST /api/v1/simulator/runs/{run_id}/cancel`

Cancels future execution of an active backend-owned run. No request body is accepted. Existing SecurityEvents and Alerts remain.

## Deployment warning

AI investigation assistance and active response are not implemented. The local shared keys are not production authentication. Production use requires user authorization, TLS, independently authenticated services, key rotation, durable queuing, retention controls, and cross-instance pub/sub.
