# SENTINEL Architecture

This document describes the implemented Milestone 2 architecture. Detection, correlation, attack simulation, and lab services are not operational components.

## Runtime topology

```mermaid
flowchart LR
    Producer[Synthetic telemetry producer] -->|POST /api/v1/telemetry/events| API[FastAPI routes]
    API --> Normalizer[Event normalizer]
    Normalizer --> Service[Security event service]
    Service --> Repository[SQL repositories]
    Repository -->|async SQLAlchemy| DB[(PostgreSQL 16)]
    Service -->|committed event| WS[WebSocket manager]
    WS -->|/api/v1/ws/events| Proxy[Nginx]
    Proxy --> Browser[React dashboard]
    Browser -->|authoritative REST queries| Proxy
    Proxy -->|HTTP| API
    Migration[Alembic] --> DB
    Seeder[Demo seed CLI] --> DB

    subgraph Docker[SENTINEL management network]
        Proxy
        API
        Service
        Repository
        Normalizer
        WS
        DB
        Migration
        Seeder
    end
```

## REST query flow

```mermaid
sequenceDiagram
    participant UI as React + TanStack Query
    participant Route as FastAPI route
    participant Service as Domain service
    participant Repo as Repository
    participant DB as PostgreSQL
    UI->>Route: GET /api/v1/events?severity=medium&page=1
    Route->>Service: Validated filter model
    Service->>Repo: Bounded query request
    Repo->>DB: COUNT + filtered LIMIT/OFFSET query
    DB-->>Repo: Rows and total
    Repo-->>Service: ORM entities
    Service-->>Route: Page[SecurityEventResponse]
    Route-->>UI: Typed JSON response
```

Routes handle transport concerns, services enforce application behavior, and repositories own SQL construction.

## Live telemetry flow

```mermaid
sequenceDiagram
    participant Producer as Telemetry producer
    participant Route as Telemetry route
    participant Service as SecurityEventService
    participant DB as PostgreSQL
    participant WS as WebSocketManager
    participant UI as React + TanStack Query
    Producer->>Route: POST validated normalized telemetry
    Route->>Service: canonical SecurityEventCreate
    Service->>Service: normalize and resolve asset
    Service->>DB: event + monotonic asset last_seen
    DB-->>Service: commit with persistent UUID
    Service-->>WS: typed security_event envelope
    WS-->>UI: committed SecurityEventResponse
    Service-->>Route: 201 Created
```

Broadcast happens only after a successful commit. A socket failure is isolated after persistence and never rolls back the event. With no connected clients, ingestion continues normally.

## Data model

```mermaid
erDiagram
    ASSET ||--o{ SECURITY_EVENT : "resolves activity for"
    ASSET {
        uuid id PK
        string hostname UK
        string ip_address UK
        string asset_type
        string status
        float risk_score
        jsonb metadata
        timestamptz first_seen
        timestamptz last_seen
    }
    SECURITY_EVENT {
        uuid id PK
        timestamptz timestamp
        string event_type
        string source
        string severity
        uuid asset_id FK
        jsonb raw_event
        jsonb normalized_data
    }
```

Security events may remain unresolved. Deleting an asset sets its event foreign keys to null rather than deleting historical evidence.

## Normalization and asset resolution

Real collectors are deliberately absent. `EventNormalizer` validates the canonical schema, normalizes categorical strings and hostnames, and converts timestamps to UTC. The synthetic producer exercises this contract without pretending to be a collector. Future source adapters should transform their source-specific input into `SecurityEventCreate` instead of manipulating ORM entities.

Asset resolution is deterministic:

1. Explicit valid asset ID
2. Exact normalized hostname
3. A single match across relevant destination and source IP addresses

Conflicting IP matches remain unresolved. Unknown telemetry never auto-creates assets. When an asset resolves, `last_seen` advances in the same transaction only when the incoming event is newer. Risk scores are unchanged.

## Query and cache behavior

- Assets and events use bounded page sizes with a maximum of 100 rows.
- Filtering, ordering, counts, and pagination occur in SQL.
- Events are ordered by timestamp descending with ID as a stable tiebreaker.
- Dashboard summary and activity data use dedicated database aggregation queries.
- TanStack Query remains the authoritative browser cache for REST data.
- The application maintains one typed WebSocket connection.
- Compatible newest-page event lists update directly and deduplicate by persistent ID.
- Historical pages and time ranges show a new-event notice instead of changing pagination.
- Dashboard and asset detail invalidations are debounced.
- A successful socket reconnection invalidates REST queries to recover missed events from PostgreSQL.

## Persistence lifecycle

The backend runs `alembic upgrade head` before Uvicorn starts. Alembic is the schema mechanism; application startup never invokes `Base.metadata.create_all()`. The demo seed uses deterministic UUIDs.

The telemetry transaction contains both the event insert and any monotonic asset `last_seen` update. The committed ORM object is serialized before WebSocket delivery, so clients receive the real UUID and can immediately retrieve the event through REST.

## Proxy and isolation

PostgreSQL, FastAPI, and Nginx share only the management network and publish ports exclusively on loopback. Nginx upgrades only the WebSocket route and preserves the existing HTTP proxy. FastAPI checks browser origins against an explicit development allow-list.

The connection manager is intentionally process-local because Compose runs one backend instance. Multi-instance deployments require shared pub/sub for cross-instance delivery. Milestone 2 does not add Redis, Kafka, RabbitMQ, or any other broker.
