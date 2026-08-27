# Portfolio Demo

This path tells the product story using real bundled-lab service activity and authoritative persisted evidence. Allow roughly 8-12 minutes, plus any five-minute detection suppression cooldown.

## Prepare

```bash
make demo-ready
```

Open the Overview, Simulator, Incidents, Attack Map, and System pages in separate tabs. Confirm the System page reports healthy core services and fresh collector telemetry.

For a clean development history, first run:

```bash
make demo-reset
make demo-ready
```

`demo-reset` is intentionally destructive to generated development telemetry, alerts, incidents, analyses, messages, relationships, and scenario runs. It refuses any environment other than `development` and requires the confirmation embedded in the Make target. It preserves canonical assets, detection rules, and Alembic history.

## Flagship SCN-005 flow

1. Open **Attack Simulator** and select `SCN-005 - Multi-Stage Intrusion Chain`.
2. Confirm the fixed Corporate Lab-only run.
3. On Run Detail, explain that unresolved expected detections remain neutral while the run is pending/running.
4. Show the actual chain: lab action -> source log -> collector -> normalized event -> detection -> alert -> correlation.
5. After terminal status, follow the correlated Incident link.
6. On Incident Detail, show affected assets, alert counts, authoritative ATT&CK mappings, deterministic confidence, evidence links, and the chronological story.
7. Open **View Incident on Attack Map** and inspect observed relationships only.
8. Download the PDF or HTML report. Keep AI excluded for the deterministic version.
9. Optionally generate mock AI analysis, explain its non-authoritative boundary, then explicitly include it in a second report.
10. Restart the stack and show that the ScenarioRun, evidence, Incident, analysis, and regenerated report remain available.

Expected SCN-005 results depend on current suppression state. DET-DB-001 intentionally has no ATT&CK technique because its telemetry proves a database connection, not queries, collection, or exfiltration. The report derives counts from the current Incident; no acceptance value is hardcoded.

## Mock AI demonstration

Set the following in `.env`, then recreate the backend:

```text
SENTINEL_AI_ENABLED=true
SENTINEL_AI_PROVIDER=mock
SENTINEL_AI_MODEL=sentinel-mock-v1
```

```bash
docker compose up --build -d backend frontend
```

The mock runs locally and sends no evidence to an external provider. On Incident Detail, generate analysis and ask a bounded evidence question. Point out citations, uncertainties, provider label, and staleness state.

## Negative demonstrations

- An unknown scenario ID is rejected.
- A second concurrent scenario is rejected.
- There is no API for custom targets or commands.
- AI disabled/unavailable does not degrade core health or reporting.
- A report for an Incident UUID outside the requested scope returns not found.
- Downloaded reports are snapshots and do not update automatically.

## Safety statement

Simulation capabilities are designed specifically for the isolated bundled lab. They use compiled actions and fictional credentials, perform no exploitation, and cannot target arbitrary systems. Docker isolation is not a security boundary against a user with daemon access.
