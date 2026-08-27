# v1.0 Release Checklist

Use this checklist before creating a `v1.0.0` tag. Codex does not publish, tag, or commit the release.

## Repository

- [ ] Review the complete diff and confirm no unrelated user work was changed.
- [ ] Confirm `git status` contains no secrets, reports, caches, logs, build output, or runtime data.
- [ ] Confirm package, API, health, Compose, README, changelog, and release-note versions are `1.0.0`.
- [ ] Confirm MIT `LICENSE` is present.

## Automated validation

- [ ] Run `make release-check` from an environment with backend dev dependencies and frontend dependencies installed.
- [ ] Run exact CI-context Ruff commands from `backend/`.
- [ ] Run scenario, correlation, and AI validators.
- [ ] Run all backend and frontend tests.
- [ ] Run Alembic upgrade/check against current and fresh PostgreSQL databases.
- [ ] Run Compose rendering and lab isolation validation.
- [ ] Review `npm audit --audit-level=high` and Python `pip check` results.

## Runtime

- [ ] Rebuild and start all 11 containers from documented commands.
- [ ] Confirm all services healthy and health reports `1.0.0`.
- [ ] Validate SCN-001 and SCN-005 on fresh disposable data.
- [ ] Confirm terminal ScenarioRun counts and Incident attribution use persisted evidence.
- [ ] Confirm restart persistence.
- [ ] Confirm AI-disabled core behavior and local mock analysis/Q&A behavior.

## Reports

- [ ] Export HTML and PDF for a canonical SCN-005 Incident.
- [ ] Confirm counts, assets, alerts, story, ATT&CK, relationships, and disclaimer match the Incident.
- [ ] Confirm DET-DB-001 does not claim queries, collection, exfiltration, or T1213.
- [ ] Confirm HTML escaping, safe filename, attachment headers, no-store, nosniff, and CSP.
- [ ] Render PDF pages and visually inspect wrapping, page furniture, tables, and AI separation.

## Manual visual QA

- [ ] Overview at desktop and mobile widths, including every time range.
- [ ] Incident queue/detail/report controls and 404/error recovery.
- [ ] Attack Map filters, legend, empty relationships, detail panel, and mobile guidance.
- [ ] Simulator guide, active run, pending/observed/terminal expected-detection states.
- [ ] System release metadata and optional assistant unavailable state.
- [ ] Keyboard focus, table scrolling, empty states, and loading/error states.
- [ ] Capture real screenshots listed in `docs/images/README.md`.

## Release preparation

- [ ] Read `docs/release-notes-v1.0.0.md` against the final diff.
- [ ] Replace or remove any environment-specific performance measurements.
- [ ] Commit Milestone 9 only after review.
- [ ] Create and push `v1.0.0` only with explicit maintainer approval.
