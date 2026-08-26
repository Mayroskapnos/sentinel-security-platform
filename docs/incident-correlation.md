# Incident Correlation and Attack Story Reconstruction

## Purpose

Milestone 7 groups related persisted Alerts into persistent Incidents and reconstructs a chronological, evidence-backed story. The engine is deterministic, conservative, explainable, and reproducible. It uses no AI, probability model, or intended scenario outcome.

## Incident model

`Incident` stores workflow state, severity, deterministic confidence and risk scores, activity bounds, a bounded summary, an optional ScenarioRun reference, and derived story metadata. `IncidentAlert` guarantees that an Alert belongs to at most one Incident and preserves the score and actual signals used at attachment time. `IncidentAsset` stores affected Assets derived from Alert evidence. Incident numbers use a UUID-derived `INC-XXXXXXXX` identity rather than a race-prone row count.

Normal deletion is not exposed. Alert evidence remains immutable. False-positive Alerts remain associated for audit but are excluded from effective story, technique, severity, and risk calculations.

## Correlation lifecycle

The Detection Engine commits an Alert first. Ingestion broadcasts `alert_created` or `alert_updated`, then invokes correlation. A correlation failure rolls back only correlation work, is logged, and does not roll back the Alert. A successful decision commits before `incident_created` or `incident_updated` is broadcast. REST remains authoritative and WebSocket reconnects trigger refetches.

The engine uses a process lock plus a PostgreSQL transaction advisory lock based on explicit scenario or identity context. The unique IncidentAlert constraint is the final single-membership guarantee. Horizontal deployments still require shared work coordination.

## Candidate selection

Only `open` and `investigating` Incidents whose activity overlaps a configurable 15-minute candidate window are considered. Queries are bounded to 25 recent candidates. Explicitly different ScenarioRuns conflict and cannot merge. An exact tie between top candidates creates a new Incident rather than making an arbitrary attachment.

The controlled rebuild command is non-destructive and idempotent for existing membership:

```bash
make validate-correlation
make incident-rebuild
```

It processes only currently unassociated Alerts and refuses unbounded limits.

## Correlation signals

The repository-owned configuration currently scores:

| Persisted signal | Weight |
| --- | ---: |
| Same explicit ScenarioRun | 50 |
| Shared source IP | 20 |
| Shared username | 15 |
| Shared affected Asset | 15 |
| Observed NetworkConnection between affected Assets | 10 |
| Forward detection-progression hint | 15 |
| Within 2 minutes | 15 |
| Within 5 minutes | 10 |
| Within the 15-minute candidate window | 5 |

The minimum attachment score is 50. Time alone cannot merge Alerts. Scenario identity receives strong weight because it is explicit persisted attribution, but no scenario ID has custom code and intended detections never become observations.

Progression hints are directional: SSH failures to authenticated access, authenticated access to discovery, discovery to privilege activity, and privilege activity to database connection. They contribute only when the earlier Alert precedes the new Alert. They are correlation hints, not claims that an attacker completed a tactic.

## Confidence scoring

Incident confidence is the average stored attachment score for non-founding associations. A one-Alert Incident starts at 25. Labels are low below 50, moderate from 50, and high from 80. The score is an experimental deterministic explanation score, never a probability of compromise.

## Severity and risk scoring

Incident risk is distinct from Asset risk. It starts with the highest effective Alert severity, then applies bounded modifiers for multiple active Alerts, highest affected-Asset criticality, number of affected Assets, observed privilege activity, and observed database-connection activity. The value is capped at 100 and mapped to incident severity. If all effective Alerts are resolved, the historical base contribution is halved. False-positive Alerts contribute nothing.

The formula components are persisted in Incident metadata for inspection. Incident scoring does not stack back into Asset risk, avoiding a feedback loop.

## Story reconstruction

Story steps are chronological Alert observations supported by relational AlertEvent evidence. Central templates provide conservative language for known rule IDs. Each item records the supporting Alert, event IDs, affected Asset IDs, source/destination context, and an observed NetworkConnection ID where one exists.

Only complete ATT&CK metadata already present on an observed, non-false-positive Alert is aggregated. Story stages never invent mappings. In particular, DET-DB-001 states only that an unexpected workstation-to-database connection was observed; it does not assert a query, data access, or collection technique.

## Incident lifecycle

Validated analyst transitions cover `open`, `investigating`, `contained`, `resolved`, and `false_positive`. Resolved, contained, and false-positive Incidents do not accept new automatic membership. A resolved or false-positive Incident may be reopened to `investigating`. Alert status changes recalculate the associated Incident.

## ScenarioRun and Attack Map relationships

A ScenarioRun answers what controlled test executed. An Incident answers what SENTINEL inferred from actual security evidence. The objects remain separate and link only when all effective incident evidence resolves to one persisted run.

`/attack-map?incident=<uuid>` requests Incident mode. The backend selects exact AlertEvent evidence for that Incident, resolves Assets from those records, and renders only observed relationships. It does not parse story prose or titles to create edges.

## Limitations

- Correlation configuration is repository-owned rather than analyst-editable.
- Automatic Incident merge, split, delete, and manual Alert removal are not implemented.
- Candidate and evidence reads are bounded; metadata reports evidence truncation where applicable.
- Process locks and WebSockets are single-instance facilities; PostgreSQL constraints protect membership but do not provide a distributed work queue.
- Correlation cannot establish attacker intent, compromise, data collection, or causality beyond the persisted signals it reports.
