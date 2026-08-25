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

## Development credentials

Values in `.env.example` are local development defaults, not production secrets. Change them for shared environments. Event ingestion supports an optional `X-Sentinel-Collector-Key` shared key and Compose enables it for the lab. It is a lightweight local trust boundary, not a replacement for TLS, per-agent identity, key rotation, or production authorization. JWT settings remain reserved and unused.

## Collector trust boundary

Lab logs are treated as untrusted input. Adapters reject malformed records, redact recognized secret fields, and create the same Pydantic-validated `SecurityEventCreate` used by every ingestion caller. The collector cannot write source log volumes, cannot insert directly into PostgreSQL, and cannot bypass normal detection. Its checkpoint volume is writable and should be treated as operational state.
