# Incident Reporting

SENTINEL exports analyst-readable snapshots from authoritative Incident data. Reports demonstrate the transition from telemetry to evidence, Alert, correlation, and investigation artifact; they are not compliance-certified forensic documents.

## Generate a report

On Incident Detail, choose **Download PDF** or **Download HTML**. Deterministic evidence is always included. The optional checkbox includes only the latest completed AI analysis and labels it separately as non-authoritative.

API equivalents:

```text
GET /api/v1/incidents/{incident_id}/report?format=pdf&include_ai=false
GET /api/v1/incidents/{incident_id}/report?format=html&include_ai=false
```

The server returns a safe Incident-number-derived filename, `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, and a restrictive Content Security Policy. HTML contains no JavaScript or external resources.

## Content and source of truth

The dedicated report context builder loads the same authoritative Incident service used by the API, its relational alerts/assets/evidence story, and only network relationships explicitly referenced by persisted story items. It never scrapes rendered UI and AI never creates the factual core.

Reports contain:

- release and point-in-time generation metadata;
- Incident summary, severity, lifecycle status, deterministic confidence, risk, and derived counts;
- affected assets and alert summary;
- chronological deterministic attack story and timeline;
- stored correlation signals and score weights;
- authoritative observed ATT&CK techniques only;
- evidence-backed network relationships only;
- optional latest completed AI section, with provider/model/current-or-outdated state;
- limitations, privacy, and evidence disclaimer.

DET-DB-001 remains unmapped because an unexpected workstation-to-database connection does not prove a query, collection, or exfiltration. Report language preserves that distinction.

## Snapshot semantics

Each download reflects Incident state at generation time and is not stored by SENTINEL. Later alerts, analyst status changes, or analysis regeneration do not modify an already downloaded file. Generate a new report for a new snapshot.

## Formats

PDF is a printable A4 document with repeated page furniture, wrapped table cells, and page numbering. HTML is a self-contained UTF-8 print layout. Both use the same evidence context and disclaimer.

## AI boundary

AI is opt-in per download. If no completed analysis exists, the deterministic report remains complete and no AI claims are substituted. Included output retains its external-provider privacy warning and current/outdated label. It cannot change evidence, ATT&CK mappings, counts, conclusions, or workflow state.

## Security and privacy

All dynamic text is escaped before HTML rendering. PDF content is emitted as text/layout primitives. No caller controls filesystem paths or filenames, and generation uses memory rather than retained server files.

Exports may contain hostnames, IP addresses, usernames, alert narratives, and selected evidence. Treat downloaded files as sensitive operational data. Apply access, retention, and secure-sharing controls outside SENTINEL.

## Known limitations

SENTINEL does not sign reports, provide chain-of-custody guarantees, preserve packet capture, certify completeness, or prove the absence of uncollected activity. Network relationships are evidence-derived aggregates, not packet-level sessions. Report generation is local and synchronous; exceptionally large future incidents may need an asynchronous export queue.
