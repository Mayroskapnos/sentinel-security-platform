# Controlled Attack Simulator

## Purpose

SENTINEL's Attack Simulator validates defensive controls by generating predefined suspicious activity only inside the local Corporate Lab. It is not a general offensive-security tool. Every run exercises the real path: lab action, native service log, read-only collector, Telemetry API, SecurityEvent, Detection Engine, and Alert.

## Safety model

- Scenarios are repository-owned YAML data parsed with `yaml.safe_load` and strict Pydantic models.
- Unknown fields and actions are rejected. There is no `shell`, command, payload, SQL, URL, hostname, IP, port, CIDR, plugin, or dynamic-import field.
- One canonical registry permits only `web-server`, `employee-01`, `employee-02`, `admin-server`, and `database`.
- Action-specific validation fixes each action to its reviewed originating asset.
- Hard limits permit at most 12 steps, 180 estimated seconds, 15 authentication attempts, 10 seconds per wait, 30 cumulative wait seconds, and three connection-oriented steps.
- Every broker request and complete scenario has a timeout. Authentication activity stops automatically.
- Only one run can hold the database `active_slot`; concurrent starts return `409 SCENARIO_ALREADY_RUNNING`.
- The simulator never inserts SecurityEvents or Alerts. It cannot bypass rule suppression.

## Action registry

| Action | Fixed behavior |
| --- | --- |
| `controlled_failed_authentication` | 1-15 bounded attempts from `employee-01` to the fixed admin SSH account; built-ins use 10 |
| `controlled_successful_authentication` | One fixed successful SSH login from `employee-01` to `admin-server` |
| `internal_service_discovery` | Connection attempts to exactly ten compiled service/port pairs on known lab containers |
| `controlled_privileged_activity` | Existing `sudo /usr/bin/id` operation on `admin-server` |
| `controlled_database_connection` | Fixed lab credentials, one connection, hard-coded `SELECT current_database()`, disconnect |
| `wait` | Backend delay of 1-10 seconds |

The internal broker exposes one route per action. Lab host agents likewise expose only fixed paths. No route accepts infrastructure addresses or executable text.

The lab-only SSH daemon disables OpenSSH source penalties so all code-bounded attempts are logged within the rule window; attempts remain fixed to one fictional account and cannot exceed 15. This changes no host or external SSH service.

## Target allowlist

`LabTargetRegistry` is the single source of logical target validation. YAML contains logical IDs only. Network endpoints, accounts, credentials, the harmless SQL constant, and the ten service-discovery endpoints are compiled into reviewed action code and are not client-controlled.

## Scenario format

```yaml
id: SCN-004
name: Unexpected Workstation Database Access
description: Opens one fixed lab database session from employee-01.
risk: low
estimated_seconds: 8
targets: [employee-01, database]
expected_detections: [DET-DB-001]
steps:
  - name: Controlled workstation database connection
    action: controlled_database_connection
    target: employee-01
```

Scenario definitions cannot contain executable code. CI runs `python -m app.cli.validate_scenarios` without executing a scenario.

## Built-in scenarios

| ID | Scenario | Expected rules |
| --- | --- | --- |
| SCN-001 | SSH Credential Activity | DET-SSH-001, DET-SSH-002 |
| SCN-002 | Internal Service Discovery | DET-NET-001 |
| SCN-003 | Privileged Administrative Activity | DET-PRIV-001 |
| SCN-004 | Unexpected Workstation Database Access | DET-DB-001 |
| SCN-005 | Multi-Stage Enterprise Security Exercise | all five rules |

DET-DB-001 is intentionally ATT&CK-unmapped. Its evidence establishes a workstation database connection, not information collection.

## Execution lifecycle

Before persistence, the orchestrator validates configuration, scenario shape, required online assets, active collector telemetry, enabled required rules, broker health, and absence of another active run. It creates a persistent pending `ScenarioRun`; execution then belongs to a backend task and is independent of a browser or WebSocket connection.

Steps transition through pending, running, and completed, or failed/cancelled/skipped. Typed WebSocket envelopes provide low-latency progress, while REST is authoritative after refresh, reconnect, or multi-tab observation. A bounded collection-settle interval precedes completion. No step is retried because a client reconnects.

At backend startup, any stale pending/running record is marked failed with an interruption message. It is never resumed automatically.

## Cancellation

Cancellation interrupts the current action request, marks the active step cancelled and later steps skipped, releases the one-run slot, and persists a cancelled run. Already generated SecurityEvents and Alerts are security history and are neither deleted nor rolled back. `lab-reset` remains an explicit, separate operation.

## Attribution

The backend generates `scenario_run_id` and `scenario_id`; the browser never assigns them. The internal key-authenticated action request carries the IDs. Structured host records preserve both, and SSH attribution is queued on the fixed destination agent before bounded attempts. PostgreSQL receives a strict `application_name` marker, which the collector parses. The collector places correlation values in dedicated SecurityEvent columns and normalized metadata before normal ingestion.

Run summaries count persisted events by `scenario_run_id`. Alerts are attributed through relational AlertEvent evidence, so suppressed alert updates remain observable when they attach run evidence.

## Expected detections

Expected rules are validation goals. A run reports each as observed only when an actual persisted alert has attributed evidence. Otherwise it says “Expected but not observed” and notes that suppression or collection timing may apply. Existing five-minute rule cooldowns remain authoritative. Suppression advisories are captured at start; no alert history or suppression state is cleared.

## Isolation

`sentinel-simulator` is a small non-root container on the internal DMZ, employee, and server bridges only. It has a read-only root filesystem, temporary `/tmp`, all capabilities dropped, `no-new-privileges`, no host port, no management network, no volumes, no Docker socket, and no host networking. The backend remains management-only and reaches the fixed broker path through an unpublished `8082` listener on the existing fixed-upstream gateway.

Lab action endpoints listen only inside Docker's internal networks and require `X-Sentinel-Simulation-Key`. This key is separate from `X-Sentinel-Collector-Key`. The gateway publishes only the existing loopback portal port; broker port 8082 is not host-published.

## Limitations

- The local UI/API has no user authentication and is not appropriate for public exposure.
- The simulation key is a local shared-key boundary; production would need per-service identity, TLS, authorization, and rotation.
- The task registry and WebSocket manager are process-local. Database uniqueness protects one active run, but multi-instance execution ownership is not implemented.
- Docker isolation is not a security boundary against a user who controls the Docker daemon.
- Rule suppression may make back-to-back demonstrations observe fewer new alerts.
- Incident correlation and the Attack Map are deliberately not implemented.

## Development commands

```bash
make validate-scenarios
make simulator-status
make scenario-list
make scenario-run SCENARIO=SCN-001
make scenario-history
```

PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/simulator/status
Invoke-RestMethod http://127.0.0.1:8000/api/v1/simulator/scenarios
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/simulator/run/SCN-001
Invoke-RestMethod http://127.0.0.1:8000/api/v1/simulator/runs
```

Set `SENTINEL_SIMULATOR_ENABLED=false` to reject new runs while keeping scenario metadata and run history readable.
