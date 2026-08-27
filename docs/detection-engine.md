# Detection Engine

Milestone 3 adds deterministic, explainable alerting to SENTINEL. Rules are data, never executable code: the loader does not use `eval`, arbitrary SQL, shell commands, or unsafe YAML constructors.

## Lifecycle

1. A supported POST path validates and normalizes a `SecurityEvent`.
2. The event and any monotonic asset `last_seen` change commit.
3. SENTINEL broadcasts `security_event` with the persistent event ID.
4. The engine selects enabled database rules for the event type.
5. Exact match, grouping, context, and bounded event-time windows are evaluated.
6. A new alert or suppressed update commits with relational evidence.
7. SENTINEL broadcasts `alert_created` or `alert_updated` with the persistent alert ID.

Detection errors are isolated after event persistence. One broken rule is logged with its rule and event IDs and does not stop other candidate rules. REST reads and browser reconnects never invoke detection.

## Rule files and synchronization

Bundled definitions live in `backend/app/detection_rules/*.yml`. `RuleLoader` discovers `.yml` and `.yaml` files, parses with `yaml.safe_load`, rejects non-object documents, validates a constrained Pydantic schema, and rejects duplicate external IDs. The Docker entrypoint runs:

```bash
alembic upgrade head
python -m app.cli.sync_rules
```

Local development must run the same rule sync after migrations. The sync creates missing records and updates repository-controlled content such as matching and ATT&CK metadata. It deliberately preserves the existing database `enabled` value so container restarts do not undo an analyst's choice.

A malformed bundled file is rejected with its filename and validation details. Startup logs the rejection and keeps the last valid database rule state available rather than taking the API down; clean installations remain healthy but have no rule content until the definition is corrected and synchronization succeeds.

A rule has a stable external ID, display metadata, type, severity, exact match fields, grouping, suppression, and optional ATT&CK/context data. Supported types are:

- `threshold`: at least a configured count, optionally distinct values, in a bounded window.
- `sequence`: a configured number of prerequisite matches followed by the current matching event.
- `single_event`: one exact match, optionally constrained by source/destination asset type or zone.

The schema permits only known event/group/context fields. Unknown keys and invalid types fail synchronization with a file-specific error.

## Bundled detections

| Rule | Type | Condition | Severity | ATT&CK |
| --- | --- | --- | --- | --- |
| `DET-SSH-001` | Threshold | 10 failed SSH logins per source/destination in 60 seconds | High | Credential Access / T1110 |
| `DET-SSH-002` | Sequence | 5 failed SSH logins followed by success per source/destination/user in 300 seconds | High | Defense Evasion / T1078 |
| `DET-NET-001` | Distinct threshold | 10 destination ports per source in 60 seconds | Medium | Discovery / T1046 |
| `DET-PRIV-001` | Single event | Successful representative `sudo_command` telemetry | High | Privilege Escalation / T1548.003 |
| `DET-DB-001` | Contextual single event | Workstation-side database-client connection event from a workstation source to a database asset | Medium | Not mapped |

These detections identify security-relevant activity for analyst review. They do not claim malicious intent, perform scanning, or take response action.

`DET-DB-001` intentionally asserts no ATT&CK technique. It evaluates the workstation-side `database_client` record with normalized `database_connection` type and workstation/database asset context. The corresponding native PostgreSQL record remains stored telemetry but does not race the explicitly attributable client evidence into an Alert. The rule does not evaluate connection status, queries, returned data, exports, or other proof of collection.

## Windows, grouping, and late events

Threshold counts execute in SQL with exact match and group predicates. Distinct port counting uses database `COUNT(DISTINCT ...)`; qualifying evidence is retrieved only after the count reaches the threshold and is capped at 500 events per evaluation. The window is:

```text
[incoming event timestamp - timeframe, incoming event timestamp]
```

This supports normal event-time evaluation and late data that correlates with earlier event timestamps. Milestone 3 does not implement stream replay: a late event does not reopen already-ingested records whose timestamps are later than that late event.

## Suppression and evidence

The deduplication key consists of external rule ID plus configured group field values. If an active alert with that key exists inside `suppression_seconds`, the engine updates it instead of creating another alert. It attaches previously unlinked qualifying events, advances the last-event timestamp, records the suppressed-match count, and recalculates priority. Resolved and false-positive alerts do not absorb new detections. After cooldown, a fresh qualifying window may create a new alert.

`alert_events` is a composite-key association table with foreign keys to alerts and SecurityEvents. Historical SecurityEvents are never rewritten for presentation. Alert evidence metadata explains the criteria, observed count, configured threshold/sequence, grouping, timeframe, and suppression count. Detail responses return compact evidence events without duplicating large raw payload bodies.

## Workflow and rule state

Supported alert transitions are:

```text
new -> investigating | resolved | false_positive
investigating -> resolved | false_positive
resolved | false_positive -> investigating
```

Rule PATCH accepts only strict `enabled: boolean`. Evaluation queries current database state on each event, so disabling affects future events immediately and preserves historical alerts. Re-enabling does not replay old events.

## Risk scoring

Risk is an experimental prioritization score, not a probability or proof of compromise.

Individual alert priority uses:

```text
severity base + asset criticality modifier + min(10, evidence count - 1)
```

Severity bases are informational 5, low 15, medium 35, high 60, and critical 85. Criticality modifiers are low 0, medium 3, high 7, and critical 10. Scores are capped at 100.

The first alert recalculation records the asset's existing score as `baseline_risk_score`. Active alert weights are informational 1, low 5, medium 10, high 20, and critical 35. Asset score is:

```text
min(100, baseline + sum(active alert weights))
```

Only `new` and `investigating` alerts contribute. Resolution and false-positive classification recalculate back toward baseline, so risk does not ratchet upward permanently.

## Demo

Run the seeded stack and then:

```bash
make detection-demo
```

The producer sends exactly ten synthetic failed-SSH observations using the telemetry API. It performs no SSH operation. Use `--demo-source-ip` for a different grouping value when demonstrating again during the five-minute suppression period.

## Limitations

- The evaluation lock and WebSocket manager are process-local. Multi-instance deployments need distributed suppression coordination and pub/sub.
- No historical replay, arbitrary rule expression language, alert correlation, incidents, automatic containment, or notifications are implemented.
- The telemetry boundary is unauthenticated development infrastructure and must remain loopback-bound until collector authentication and TLS exist.
- Evidence retrieval has a defensive cap of 500 events per evaluation; the database count remains authoritative.
