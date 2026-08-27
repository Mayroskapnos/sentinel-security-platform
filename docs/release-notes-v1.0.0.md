# SENTINEL v1.0.0

SENTINEL v1.0.0 is the first portfolio release candidate of the experimental security monitoring and Purple Team platform.

## Highlights

- Reproducible 11-container platform and fictional multi-zone Corporate Lab.
- Evidence-first pipeline from genuine service logs to normalized events, detections, alerts, incidents, topology, and reports.
- Polished analyst dashboard, persistent investigation workflows, controlled flagship demo, and release documentation.

## Security Monitoring

PostgreSQL-backed canonical assets and immutable normalized SecurityEvents support bounded APIs, live WebSocket hints, reconnect recovery, health status, filtering, pagination, and operational dashboard aggregates.

## Detection & Alerting

Five validated YAML rules implement threshold, sequence, and contextual single-event detection with suppression and relational evidence. ATT&CK metadata is conservative; the database-connection rule intentionally asserts no technique because it does not prove data access or collection.

## Corporate Lab

Isolated web, SSH/host, admin, PostgreSQL, gateway, and read-only collector services produce genuine logs using fictional identities. Internal networks, loopback publication, non-root services, separate platform/lab databases, and a no-Docker-socket design bound the local demonstration.

## Attack Simulation

Five fixed, repository-defined scenarios validate the pipeline. There are no custom targets, arbitrary commands, exploits, scanning, or external attack features. ScenarioRun history, cancellation, exact telemetry attribution, and neutral active-run observation states remain persistent.

## Attack Map

The backend supplies canonical nodes, observed aggregate relationships, exact ScenarioRun/Incident evidence overlays, activity, alerts, and authoritative ATT&CK. The UI adds deterministic layout, filters, legend, selection details, deep links, and live REST recovery.

## Incident Correlation

Explainable multi-signal correlation produces persistent Incidents, affected assets, stored scores/reasons, chronological evidence stories, workflow state, and an Incident-scoped topology without treating time alone as proof.

## Investigation Assistant

Optional mock/OpenAI provider adapters generate bounded, redacted, schema-validated summaries and Incident-scoped Q&A. Citations, uncertainty, staleness, and persistence are visible. AI is analysis-only, disabled by default, and isolated from core health and authority.

## Reporting

Incident Detail exports self-contained HTML and printable PDF snapshots from authoritative server-side context. Reports include evidence-derived counts, alerts, assets, story, correlation, ATT&CK, network relationships, disclaimers, and an explicitly opt-in non-authoritative AI section.

## Testing

CI runs exact-context Ruff lint/format, scenario/correlation/AI configuration validators, pytest, Alembic upgrade/check, ESLint, strict TypeScript, Vitest, Prettier, production build, npm audit, Compose rendering, and lab-isolation validation. Final measured counts and performance values belong in the release validation report, not hardcoded product claims.

## Known Limitations

This is not a production SIEM or forensic/compliance system. It lacks user authentication, RBAC, TLS termination, retention policy, distributed coordination, durable event queues, packet capture, endpoint agents, and signed report provenance. WebSocket and detection coordination are single-backend-process designs. Docker isolation is not protection from a daemon administrator. External AI provider use is a separate privacy boundary.

## Getting Started

Follow [Getting Started](getting-started.md), then use the [Portfolio Demo](demo.md). Do not expose the local application to the public internet.
