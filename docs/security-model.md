# SENTINEL Security Model

SENTINEL is an experimental defensive-security and Purple Team platform intended only for controlled environments. It is not a production SIEM and must not be used to target systems outside its dedicated lab.

## Milestone 0 controls

- Docker publishes the frontend, API, and development database only on the loopback interface (`127.0.0.1`).
- PostgreSQL has no public-interface binding and is isolated on the `sentinel_management` Docker network.
- Containers use named service discovery; no external targets or scanning features exist.
- The backend container runs as an unprivileged user.
- The frontend runtime uses an unprivileged Nginx image and adds baseline browser security headers.
- Structured logs do not emit connection strings, passwords, tokens, or other secret values.
- `.env` files are ignored by Git; `.env.example` contains development-only placeholders.

## Corporate lab boundary

- `sentinel_dmz`, `sentinel_employee`, and `sentinel_server` are internal Docker bridges separate from `sentinel_management`.
- The corporate database, SSH services, admin service, employee hosts, and collector publish no host ports.
- A read-only, unprivileged, fixed-upstream gateway is the only lab host ingress and binds the safe corporate portal to `127.0.0.1:8081`; `sentinel-web` itself publishes no port and does not join management.
- The collector joins only the management network and reads explicit named log volumes as read-only. It never mounts the Docker socket or a host root path.
- SENTINEL PostgreSQL and corporate-lab PostgreSQL use separate containers, credentials, databases, and volumes.
- Dedicated fictional credentials and data are used. No developer or real-user credentials are copied into containers.
- Normal background activity is restricted to named lab services. Explicit SSH, sudo, and direct database demonstrations are bounded benign commands.
- `tools/validate_lab_compose.py` checks these invariants from rendered Compose configuration.

The corporate lab does not contain deliberately vulnerable services, exploitation, credential cracking, malware, persistence, packet interception, or attack automation. Docker is not a hard security boundary against a user with daemon access.

## Controlled simulator boundary

- Scenario definitions are trusted repository data loaded with safe YAML and strict schemas. Duplicate IDs, unknown actions, unsupported fields, external-looking targets, arbitrary commands, and excessive limits are rejected before execution.
- `LabTargetRegistry` permits exactly the five managed Corporate Lab logical assets. Neither UI nor API accepts a target, address, hostname, URL, domain, port, credential, SQL statement, or command.
- `SafeActionRunner` maps validated action names to compiled broker paths. Lab host agents expose dedicated fixed endpoints rather than a generic command API.
- Authentication attempts, waits, steps, connection actions, action duration, and total duration have code-enforced maximums.
- `sentinel-simulator` is non-root and joins only the three internal lab bridges. It has a read-only root filesystem, all capabilities dropped, `no-new-privileges`, no host port, no management network, no host volume, no Docker socket, and no host networking.
- The backend remains management-only. The existing gateway has an unpublished listener that proxies only `/internal/simulator/` to a fixed broker upstream.
- Broker and lab action endpoints use a dedicated `SENTINEL_SIMULATION_KEY`. It is not the collector key, is never accepted as a command parameter, and `.env` remains untracked.
- The broker cannot insert events or alerts. Actual lab logs must traverse the read-only collector and authenticated telemetry boundary.
- One database-backed active slot prevents overlapping runs. Cancellation and failure preserve historical telemetry.
- Startup marks stale pending/running work failed and never automatically resumes a partially executed action sequence.
- Compose enables this feature only as a local development default. `SENTINEL_SIMULATOR_ENABLED=false` rejects execution while leaving history readable.

The normal local UI/API still lacks user authentication. Loopback binding is not authorization; do not expose the simulator through a public or shared unauthenticated ingress.

## Investigation Assistant trust boundary

- AI is optional and disabled by default. Missing or unavailable AI never degrades core health, telemetry, detection, Alerts, correlation, Incidents, the simulator, or the Attack Map.
- A provider receives only a deterministic, bounded Incident snapshot. It has no database access and cannot accept caller-supplied external context.
- Telemetry, logs, analyst questions, and prior assistant text are untrusted data. Provider system instructions explicitly prohibit following evidence content, and prompts keep instructions separate from labeled untrusted evidence.
- Recursive redaction removes recognized password, token, API-key, Authorization, cookie, secret, and credential values before provider access. Event excerpts and Q&A history are length-bounded.
- Provider output is untrusted. Pydantic validation, evidence-reference membership, authoritative ATT&CK checks, deterministic count checks, conservative-claim checks, and text sanitization run before persistence/display.
- The assistant cannot mutate Alerts, Incidents, risk, correlation, workflow state, rules, Assets, or ScenarioRuns. It has no tool or execution interface and cannot contain, block, scan, isolate, disable, reset, or run commands.
- The mock provider is local. A configured external provider is a separate privacy and retention boundary; selected redacted Incident evidence leaves SENTINEL. The UI discloses this and never displays an API key.
- Provider credentials and Authorization headers are not logged or persisted. Operational logs contain IDs, provider/model names, duration, status, and safe error categories only.
- Timeout, provider, validation, and restart failures affect only the analysis record. Failed provider calls are not automatically retried.

Redaction cannot recognize every sensitive value, and natural-language grounding cannot prove all claims. External-provider use requires operator review. See [Investigation Assistant](investigation-assistant.md).

## Development credentials

Values in `.env.example` are local development defaults, not production secrets. Change them for shared environments. Event ingestion supports an optional `X-Sentinel-Collector-Key` shared key and simulator control uses the separate `X-Sentinel-Simulation-Key`; Compose enables both for the local lab. These are lightweight local trust boundaries, not replacements for TLS, per-agent identity, key rotation, or production authorization.

## Collector trust boundary

Lab logs are treated as untrusted input. Adapters reject malformed records, redact recognized secret fields, and create the same Pydantic-validated `SecurityEventCreate` used by every ingestion caller. The collector cannot write source log volumes, cannot insert directly into PostgreSQL, and cannot bypass normal detection. Its checkpoint volume is writable and should be treated as operational state.

## Incident report trust boundary

- Reports are generated from a server-built, typed Incident snapshot; callers cannot supply factual report fields, filesystem paths, or filenames.
- HTML dynamic values are escaped and the document contains no scripts or external resources. Download responses use attachment disposition, `nosniff`, `no-store`, and a restrictive CSP.
- PDF values are emitted through ReportLab text/layout primitives and wrapped inside bounded tables; reports are generated in memory and are not retained on the server.
- AI is excluded by default. Explicit inclusion selects only the latest completed analysis and labels it separately as non-authoritative and current/outdated.
- Exported files can contain hostnames, IP addresses, usernames, alert narratives, and selected evidence. Operators must control storage, access, retention, and sharing after download.
- Reports provide no signing, chain-of-custody, completeness proof, forensic certification, or compliance certification. Absence of evidence can reflect collection gaps.

## Development reset boundary

The demo reset CLI refuses execution unless `SENTINEL_ENV=development` and an explicit confirmation flag is supplied. It deletes generated telemetry, relationships, alerts, incidents, assistant state, and ScenarioRun history while preserving assets, detection rules, and Alembic history. It is a local demonstration tool, not a production retention/deletion mechanism.
