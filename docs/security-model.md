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

## Future lab boundary

The corporate lab and attack simulator are not implemented in Milestone 0. When added, their networks will be separate from the management network, intentionally vulnerable services will not bind public interfaces, and every scenario target will be allow-listed as a SENTINEL-owned container.

## Development credentials

Values in `.env.example` are local development defaults, not production secrets. Change them for shared environments. Authentication is not part of Milestone 0; the JWT settings are reserved for its later milestone and are not consumed yet.

