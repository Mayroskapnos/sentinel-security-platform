# SENTINEL Portfolio Notes

## Portfolio descriptions

### 1-line version

SENTINEL is a full-stack, evidence-first security observability and Purple Team platform with a safe Docker lab, deterministic detections, incident correlation, optional grounded AI, and printable incident reporting.

### 2-3 sentence version

SENTINEL follows genuine bundled-lab service logs from collection through normalized PostgreSQL storage, deterministic detection, evidence-backed alerts, incident correlation, topology, and analyst reporting. Its fixed-target simulator validates the full pipeline without accepting arbitrary commands or targets, while an optional AI assistant remains separated from authoritative security state.

### CV bullet version

- Built an 11-container security-observability platform with FastAPI, React/TypeScript, PostgreSQL, Alembic, WebSockets, and an isolated multi-zone Docker lab.
- Designed deterministic YAML-driven detections, suppression, relational alert evidence, explainable multi-alert Incident correlation, and evidence-only ATT&CK semantics.
- Implemented allow-listed Purple Team scenarios that exercise actual SSH, sudo, HTTP, and PostgreSQL logs without arbitrary target or command input.
- Added an optional bounded/redacted AI investigation layer with grounding validation, citations, staleness, persistence, and failure isolation.
- Delivered self-contained HTML and printable PDF Incident reports generated from authoritative database state with injection-resistant rendering and explicit limitations.

### LinkedIn/project description version

SENTINEL is my portfolio-grade exploration of how SIEM, XDR, network-monitoring, and incident-response systems fit together. A reproducible Docker corporate lab produces genuine application and operating-system logs; SENTINEL collects, normalizes, detects, correlates, visualizes, and exports the resulting evidence. The design emphasizes conservative claims, transparent scoring, safe simulation boundaries, persistence, and graceful degradation over opaque automation.

## Engineering Challenges

### Evidence identity across asynchronous stages

Lab actions, source logs, collector delivery, API ingestion, detection, alert attribution, and correlation occur at different times. Persistent ScenarioRun IDs, relational AlertEvent evidence, canonical Asset identity, and REST recovery prevent the UI from confusing intent with observation.

### Honest correlation

Correlation uses a bounded active window plus explicit scenario, asset, source, username, relationship, time, and progression signals. Scores and reasons are stored. Time alone cannot merge alerts, tied candidates remain separate, and confidence is described as an experimental deterministic score rather than a probability.

### Safe simulation

Declarative scenario definitions are strict data. The API accepts only a repository-defined scenario ID; fixed actions map to exact lab broker paths. The broker has no Docker socket, host mount, management-network access, generic execution route, or public port.

### AI without authority drift

The provider sees only a bounded redacted context and has no database/tool access. Output passes schema, citation, count, ATT&CK, and conservative-language checks before persistence. Core monitoring, reporting, and health remain independent of provider availability.

### Reports without a second truth model

Both report formats share one typed, server-built Incident snapshot. The renderer escapes untrusted values, labels network relationships accurately, and never lets AI replace deterministic evidence.

## Security Design Decisions

- Loopback-only host publication and internal lab networks.
- Unprivileged containers, bounded logs, no Docker socket, no host root mounts.
- Optional local shared keys for collector and simulator as distinct trust boundaries.
- Strict request sizes, enum validation, bounded pagination, and safe YAML loading.
- PostgreSQL constraints and Alembic-managed schema rather than runtime `create_all`.
- Immutable SecurityEvents with relational alert evidence.
- ATT&CK mappings asserted only when observed telemetry supports the technique.
- Downloaded HTML reports have no script or external resources and use restrictive headers.

## What This Project Demonstrates

- end-to-end system design across data ingestion, stateful processing, APIs, live delivery, and UX;
- defensive-security domain modeling and semantic restraint;
- secure-by-default local infrastructure and explicit trust boundaries;
- resilient async workflows with persistent recovery state;
- testing across units, services, API contracts, configuration, migrations, and real containers;
- product communication through documentation, demo workflow, release metadata, and analyst artifacts.

## Technical Interview Talk Track

1. Start with the evidence path and explain why the database, not WebSockets or AI, is authoritative.
2. Show how one normalized event can update topology, trigger a rule, create/update an Alert, and contribute to an Incident after commits.
3. Explain why expected simulator detections remain neutral while a run is active and why suppression is not bypassed.
4. Contrast ScenarioRun intent with Incident inference and demonstrate the exact evidence joins.
5. Discuss ATT&CK semantic accuracy using DET-DB-001 as the example of intentionally leaving a rule unmapped.
6. Explain the AI trust boundary, then show that reports work identically with AI disabled.
7. Close with current single-instance/authentication/retention limits and the changes required for production.

## Architectural Tradeoffs

- A process-local WebSocket manager is simple and reliable for one backend replica; multi-instance operation needs shared pub/sub.
- In-process detection serialization protects one process; horizontal scale requires stronger database/distributed suppression coordination.
- Synchronous report rendering keeps deployment simple; large enterprise cases would benefit from queued exports and object storage.
- Docker internal networks are excellent reproducibility controls, but not a boundary against a daemon administrator.
- Lightweight shared keys keep the local lab understandable; real deployment needs user identity, service identity, TLS, authorization, and rotation.

## Future Work

Authentication/RBAC, TLS ingress, durable queues, retention controls, multi-instance coordination, rule-authoring workflows, signed report provenance, broader telemetry adapters, accessibility testing with assistive technology, and deployment hardening are intentionally outside v1.0.
