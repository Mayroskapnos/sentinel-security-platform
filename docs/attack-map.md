# Network / Attack Map

## Purpose

The Attack Map is an investigation view over persisted SENTINEL telemetry. It renders the five Corporate Lab assets in stable DMZ, employee, and server zones and shows only relationships supported by actual normalized SecurityEvents. It is not a network scanner, packet capture system, or inferred attack-path engine.

## Relationship model

`NetworkConnection` stores one aggregate for a semantic identity composed of source asset, destination asset, protocol, destination port, and connection type. It retains source/destination IP and the latest observed source port, first and last timestamps, event count, last status, and compact last-event metadata. A unique SHA-256 relationship key prevents duplicate rows without relying on nullable SQL uniqueness behavior.

The ingestion path accepts connection evidence only for these normalized event types:

- authentication
- HTTP request
- network connection
- database connection
- database session

Both endpoint IPs must resolve to distinct stored assets. Unknown, partially resolved, and same-asset endpoints remain in SecurityEvent history but do not create graph edges. Privilege and database-query events can appear in the activity timeline but do not themselves prove a new connection.

## Aggregation and backfill

Each accepted event is committed before network aggregation. The aggregator updates one relationship incrementally, uses event time for first/last bounds, and does not let late telemetry replace a newer last status. A topology aggregation failure is logged and cannot roll back the accepted immutable event.

For installations with pre-Milestone 6 history:

```bash
make network-rebuild
make network-integration
```

The command reads at most 100,000 eligible events by default, computes the desired relationship set deterministically, replaces stale aggregate state, and does not modify SecurityEvents. Repeating it with unchanged input produces the same counts and timestamps. Use `python -m app.cli.rebuild_network_connections --limit N` inside the backend container to choose a smaller explicit safety bound.

## Live topology

`GET /api/v1/network/topology` returns nodes and edges in one bounded query workflow, including risk, status, open-alert context, activities, and observed ATT&CK mappings. The UI uses React Flow for pan, zoom, selection, minimap, directional edges, and a deterministic zone/hostname layout.

Edge recency is presentation state derived from persisted `last_seen`:

- active: 60 seconds or less
- recent: more than 60 seconds and at most 15 minutes
- historical: older than 15 minutes

Red/rose context requires observed alert evidence. A high risk score or historical scenario does not permanently paint an asset as actively compromised.

The server emits compact `network_connection_updated` WebSocket messages. TanStack Query debounces these messages and refetches the authoritative bulk document. Reconnect also refetches topology, so missed messages do not become permanent state.

## Scenario progression

Open `/attack-map?run=<scenario-run-uuid>` or follow the link on a Scenario Run Detail page. The scenario header reports exact total attributed SecurityEvent and distinct Alert counts. Scenario topology uses only SecurityEvents with that exact persisted `scenario_run_id`. Alert and ATT&CK context must join through `AlertEvent` evidence from those events. Targets declared in the scenario file are not rendered unless telemetry actually identifies activity on them. Selecting a timeline row focuses its evidence edge, or the relevant asset for local activity; the adjacent link opens the immutable source event.

SCN-005 therefore displays credential activity, observed service-discovery relationships, local privilege activity, and database connection evidence in timestamp order as those records arrive. A completed historical run remains available after the lab goes offline.

## Deep links and filters

- `run=<uuid>` selects exact scenario mode.
- `asset=<uuid>` selects an existing asset node.
- `alert=<uuid>` selects an edge supported by that alert's evidence, or its asset node when no relationship evidence exists.
- `window=5m|15m|1h|24h|all` controls live recency scope.

Malformed UUID parameters are ignored by the client and never sent to the API. The map also provides zone, alert-context, high-risk, and scenario-activity filters. Empty relationship windows still show known assets by zone.

## ATT&CK semantics

The overlay lists mappings only from observed Alerts whose detection rule has complete tactic, technique ID, and technique name fields. Expected scenario detections do not create badges. DET-DB-001 is intentionally absent because its telemetry proves an unexpected database connection rather than database collection.

## Limitations

- The aggregate relationship represents observed event evidence, not packet-level sessions or traffic volume.
- Activity reads are bounded to 5,000 events and disclose truncation.
- Asset resolution uses the stored primary IP plus explicitly declared lab metadata aliases; NAT, DHCP history, undeclared aliases, and unknown external nodes are not modeled.
- WebSocket delivery and the aggregation lock are process-local. Multi-instance deployment requires shared pub/sub and database-level aggregation coordination.
- Browser visual QA requires an available browser runtime; automated rendering, strict typing, and production builds do not replace human visual inspection.
- Incident correlation and attack-story reconstruction are reserved for Milestone 7.
