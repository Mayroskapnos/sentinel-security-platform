# Investigation Assistant

## Purpose

The optional Investigation Assistant explains and prioritizes evidence from an existing SENTINEL Incident. It does not detect attacks, correlate Alerts, assign authoritative ATT&CK techniques, change risk, modify workflow state, or execute response actions. The deterministic security engine remains the source of truth.

## Architecture

An analyst explicitly requests an analysis for an Incident UUID. The backend builds a versioned, bounded evidence snapshot, persists a pending `InvestigationAnalysis`, and runs the configured provider in a single-process background task. Provider output passes Pydantic structural validation and deterministic grounding validation before it can be persisted as completed. REST is authoritative; `analysis_started`, `analysis_completed`, and `analysis_failed` WebSocket messages only trigger refetches.

The background task architecture is intentionally lightweight. A restart marks pending or running analyses failed; it does not repeat a potentially paid request. Multi-instance deployments need a durable job queue and shared WebSocket pub/sub.

## Deterministic and AI responsibilities

SENTINEL owns Incident membership, Alert evidence, story stages, correlation signals, counts, Assets, risk, severity, and observed ATT&CK mappings. The assistant may summarize observations, explain stored correlation signals, report uncertainty, suggest defensive analyst investigation, and answer bounded Incident questions. It cannot create or update any security object.

## Context building

`InvestigationContextBuilder` accepts only an existing Incident ID. It selects Incident detail, Alert summaries, affected Assets, the deterministic story, authoritative observed techniques, stored correlation evidence, relevant NetworkConnections, ScenarioRun attribution, and a deterministic set of key SecurityEvents. Event selection prioritizes Alert window boundaries, successful authentication, privilege, network, and database activity. Explicit settings cap key events and network relationships; arbitrary request context and arbitrary database queries are not accepted.

The evidence-relevant canonical JSON is sorted and hashed with SHA-256. Workflow-only Incident status and global Asset posture remain visible in the snapshot but do not falsely change its evidence version. Each analysis retains its original `analysis_version`, `context_hash`, and context snapshot. API responses compare that hash with current evidence and expose `is_stale`; old records remain in history.

## Evidence grounding

Provider observations, correlation explanations, uncertainties, recommendations, key Assets, and answers cite typed stable references to Incident, Alert, SecurityEvent, Asset, NetworkConnection, or ScenarioRun records in the snapshot. Unknown references reject the result. Validation also rejects contradictory Alert/Asset counts, unsupported ATT&CK identifiers, and unqualified claims of credential theft, compromise, database queries, collection, or exfiltration.

DET-DB-001 remains intentionally ATT&CK-unmapped. Its connection evidence cannot become a claim of database querying, collection, or exfiltration.

## Prompt-injection model

System instructions and evidence are separate fields in the provider request. Logs, telemetry, filenames, commands, URLs, analyst questions, and prior assistant messages are explicitly declared untrusted data. Structured evidence is enclosed in an untrusted-evidence boundary. A log entry such as `IGNORE ALL PREVIOUS INSTRUCTIONS` remains visible as evidence text but never enters system instructions.

## Redaction

Before context or Q&A history reaches a provider, recursive redaction replaces recognized password, token, API-key, Authorization, cookie, secret, and credential fields and inline values. Raw and normalized excerpts are independently length-bounded. Redaction is defense in depth, not a guarantee that arbitrary sensitive content can always be recognized; operators must review their external-provider data policy.

## Structured outputs

Analysis output is plain structured text with bounded lengths and counts: executive summary, evidence-backed observations, deterministic-correlation explanation, key Assets, uncertainties, and prioritized defensive analyst actions. The React UI renders escaped text and links citations to SENTINEL records; it never injects provider HTML.

## Incident Q&A

Questions are limited to 500 characters and the selected Incident. Every request uses current authoritative context plus a small recent-message window; evidence overrides prior assistant text. User and assistant messages persist for auditability, but provider secrets and full vendor responses do not. Requests for unrelated information or execution receive a boundary response.

## Provider configuration

AI is disabled by default. These settings use the normal environment configuration:

```text
SENTINEL_AI_ENABLED=false
SENTINEL_AI_PROVIDER=mock|openai
SENTINEL_AI_MODEL=
SENTINEL_AI_API_KEY=
SENTINEL_AI_BASE_URL=https://api.openai.com/v1
SENTINEL_AI_TIMEOUT_SECONDS=30
SENTINEL_AI_MAX_CONTEXT_EVENTS=50
SENTINEL_AI_MAX_NETWORK_RELATIONSHIPS=50
SENTINEL_AI_QUESTION_HISTORY=10
```

`mock` is deterministic, clearly labeled, and makes no external request. `openai` uses the Responses API with Structured Outputs and provider-side storage disabled. Configuration validation is available through `python -m app.cli.validate_ai`. Never commit a real API key.

## Privacy

The mock provider keeps data inside SENTINEL. A configured external provider receives the bounded, redacted Incident snapshot and bounded Q&A content. The Incident UI displays this trust-boundary warning before generation and the System page shows provider/model metadata without credentials.

## Failure behavior

Timeouts, rejected requests, malformed output, and grounding failures mark only the analysis failed and show a safe error. The Incident remains valid, the core health result does not depend on AI availability, and no automatic retry is made. One partial unique index permits only one pending/running analysis per Incident. Lightweight per-process rate limits protect generation and Q&A endpoints.

## Limitations

- AI output is an investigation aid and requires analyst verification.
- Redaction cannot recognize every domain-specific secret.
- Grounding validation is conservative but cannot prove every natural-language claim.
- Background execution, WebSockets, and rate limits are process-local.
- External-provider quality, availability, retention outside SENTINEL, and cost remain operator responsibilities.
- No containment, remediation, simulation, scanning, or command execution exists in this feature.
