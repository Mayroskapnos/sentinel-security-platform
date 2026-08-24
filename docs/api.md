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

Expected errors use a structured envelope:

```json
{
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "Requested asset does not exist."
  }
}
```

Validation failures use code `VALIDATION_ERROR` and include field-level details. IDs are UUIDs and timestamps are ISO 8601 values with timezone information.

## Health

### `GET /api/v1/health`

Checks both the API process and PostgreSQL with `SELECT 1`. Returns `503` with `status: degraded` when the database is unavailable.

## Assets

### `GET /api/v1/assets`

Filters:

- `asset_type`
- `status`
- `network_zone`
- `criticality`
- `min_risk_score` (`0`–`100`)
- `search` (hostname, display name, or IP address)
- `page` (default `1`)
- `page_size` (default `25`, maximum `100`)

### `GET /api/v1/assets/{asset_id}`

Returns one asset or `ASSET_NOT_FOUND`.

### `POST /api/v1/assets`

Creates a validated asset. Hostname and IP address are unique. Risk is constrained to `0`–`100`; IP and MAC addresses are validated.

### `PATCH /api/v1/assets/{asset_id}`

Applies only supplied mutable fields. Hostname is intentionally immutable through this milestone's API.

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
- `page` (default `1`)
- `page_size` (default `25`, maximum `100`)

Results are ordered newest first.

### `GET /api/v1/events/{event_id}`

Returns normalized fields, an optional resolved asset reference, `normalized_data`, and `raw_event` evidence.

### `POST /api/v1/events`

Ingests one normalized event. Ports are constrained to `0`–`65535`, IP fields are validated, and timestamps must be timezone-aware. When `asset_id` is omitted, SENTINEL attempts a hostname match; unresolved events remain valid.

## Dashboard

### `GET /api/v1/dashboard/summary`

Returns:

- `total_assets`
- `online_assets`
- `high_risk_assets` (risk score ≥ 61)
- `events_today` (UTC day)
- `events_last_hour`

### `GET /api/v1/dashboard/activity`

Accepts `hours` from `1` through `168` (default `72`) and returns database-aggregated:

- hourly event counts
- severity counts
- event-type counts
- most active assets

No alert or incident endpoints are implemented in Milestone 1.

