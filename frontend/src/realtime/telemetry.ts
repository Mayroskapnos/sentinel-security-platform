import type {
  Alert,
  AlertFilters,
  AlertStatus,
  EventFilters,
  EventSeverity,
  NetworkConnectionUpdate,
  Page,
  SecurityEvent,
} from "../types/core";

export type TelemetryConnectionState =
  "connecting" | "connected" | "reconnecting" | "disconnected" | "error";

export interface SecurityEventMessage {
  version: "1";
  type: "security_event";
  timestamp: string;
  data: SecurityEvent;
}

export interface TelemetryStatusMessage {
  version: "1";
  type: "telemetry_status";
  timestamp: string;
  data: {
    status: "connected";
    connected_clients: number;
  };
}

export interface AlertCreatedMessage {
  version: "1";
  type: "alert_created";
  timestamp: string;
  data: Alert;
}

export interface AlertUpdatedMessage {
  version: "1";
  type: "alert_updated";
  timestamp: string;
  data: Alert;
}

export interface NetworkConnectionUpdatedMessage {
  version: "1";
  type: "network_connection_updated";
  timestamp: string;
  data: NetworkConnectionUpdate;
}

export interface SimulationMessage {
  version: "1";
  type:
    | "simulation_started"
    | "simulation_step"
    | "simulation_finished"
    | "simulation_failed"
    | "simulation_cancelled";
  timestamp: string;
  data: {
    run_id: string;
    scenario_id: string;
    status: string;
    current_step: number;
    total_steps: number;
    label: string | null;
    message: string | null;
  };
}

export type TelemetryMessage =
  | SecurityEventMessage
  | TelemetryStatusMessage
  | AlertCreatedMessage
  | AlertUpdatedMessage
  | NetworkConnectionUpdatedMessage
  | SimulationMessage;

const severities = new Set<EventSeverity>([
  "informational",
  "low",
  "medium",
  "high",
  "critical",
]);
const alertStatuses = new Set<AlertStatus>([
  "new",
  "investigating",
  "resolved",
  "false_positive",
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return typeof value === "string" || value === null;
}

function isNullableNumber(value: unknown): value is number | null {
  return typeof value === "number" || value === null;
}

function isSeverity(value: unknown): value is EventSeverity {
  return typeof value === "string" && severities.has(value as EventSeverity);
}

function isAssetReference(value: unknown): boolean {
  return (
    value === null ||
    (isRecord(value) &&
      typeof value.id === "string" &&
      typeof value.hostname === "string" &&
      typeof value.display_name === "string")
  );
}

function isSecurityEvent(value: unknown): value is SecurityEvent {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.timestamp === "string" &&
    typeof value.event_type === "string" &&
    typeof value.source === "string" &&
    isNullableString(value.source_ip) &&
    isNullableString(value.destination_ip) &&
    isNullableNumber(value.source_port) &&
    isNullableNumber(value.destination_port) &&
    isNullableString(value.hostname) &&
    isNullableString(value.username) &&
    isNullableString(value.process_name) &&
    typeof value.action === "string" &&
    typeof value.status === "string" &&
    isSeverity(value.severity) &&
    isRecord(value.raw_event) &&
    isRecord(value.normalized_data) &&
    isNullableString(value.asset_id) &&
    isNullableString(value.scenario_run_id) &&
    isNullableString(value.scenario_id) &&
    isAssetReference(value.asset) &&
    typeof value.created_at === "string"
  );
}

function isAlert(value: unknown): value is Alert {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.timestamp === "string" &&
    typeof value.title === "string" &&
    typeof value.description === "string" &&
    isSeverity(value.severity) &&
    typeof value.status === "string" &&
    alertStatuses.has(value.status as AlertStatus) &&
    typeof value.detection_rule_id === "string" &&
    isRecord(value.detection_rule) &&
    typeof value.detection_rule.id === "string" &&
    typeof value.detection_rule.rule_id === "string" &&
    typeof value.detection_rule.name === "string" &&
    isNullableString(value.asset_id) &&
    isAssetReference(value.asset) &&
    isNullableString(value.source_ip) &&
    isNullableString(value.destination_ip) &&
    isNullableString(value.username) &&
    typeof value.risk_score === "number" &&
    isNullableString(value.mitre_tactic) &&
    isNullableString(value.mitre_technique_id) &&
    isNullableString(value.mitre_technique_name) &&
    isRecord(value.evidence) &&
    isRecord(value.metadata_json) &&
    typeof value.evidence_count === "number" &&
    typeof value.first_event_at === "string" &&
    typeof value.last_event_at === "string" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string"
  );
}

function isNetworkConnectionUpdate(
  value: unknown,
): value is NetworkConnectionUpdate {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.source_asset_id === "string" &&
    typeof value.destination_asset_id === "string" &&
    isNullableNumber(value.destination_port) &&
    typeof value.protocol === "string" &&
    typeof value.connection_type === "string" &&
    typeof value.last_seen === "string" &&
    typeof value.connection_count === "number" &&
    typeof value.last_status === "string"
  );
}

export function parseTelemetryMessage(raw: string): TelemetryMessage | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw) as unknown;
  } catch {
    return null;
  }

  if (
    !isRecord(parsed) ||
    parsed.version !== "1" ||
    typeof parsed.timestamp !== "string" ||
    !isRecord(parsed.data)
  ) {
    return null;
  }

  if (parsed.type === "security_event" && isSecurityEvent(parsed.data)) {
    return parsed as unknown as SecurityEventMessage;
  }
  if (
    parsed.type === "telemetry_status" &&
    parsed.data.status === "connected" &&
    typeof parsed.data.connected_clients === "number"
  ) {
    return parsed as unknown as TelemetryStatusMessage;
  }
  if (parsed.type === "alert_created" && isAlert(parsed.data)) {
    return parsed as unknown as AlertCreatedMessage;
  }
  if (parsed.type === "alert_updated" && isAlert(parsed.data)) {
    return parsed as unknown as AlertUpdatedMessage;
  }
  if (
    parsed.type === "network_connection_updated" &&
    isNetworkConnectionUpdate(parsed.data)
  ) {
    return parsed as unknown as NetworkConnectionUpdatedMessage;
  }
  if (
    [
      "simulation_started",
      "simulation_step",
      "simulation_finished",
      "simulation_failed",
      "simulation_cancelled",
    ].includes(String(parsed.type)) &&
    typeof parsed.data.run_id === "string" &&
    typeof parsed.data.scenario_id === "string" &&
    typeof parsed.data.status === "string" &&
    typeof parsed.data.current_step === "number" &&
    typeof parsed.data.total_steps === "number" &&
    isNullableString(parsed.data.label) &&
    isNullableString(parsed.data.message)
  ) {
    return parsed as unknown as SimulationMessage;
  }
  return null;
}

export function eventMatchesFilters(
  event: SecurityEvent,
  filters: EventFilters,
): boolean {
  const contains = (value: string | null, expected: string | undefined) =>
    !expected || value?.toLowerCase().includes(expected.toLowerCase()) === true;

  if (!contains(event.hostname, filters.hostname)) return false;
  if (!contains(event.username, filters.username)) return false;
  if (filters.asset_id && event.asset_id !== filters.asset_id) return false;
  if (filters.event_type && event.event_type !== filters.event_type)
    return false;
  if (filters.source && event.source !== filters.source) return false;
  if (filters.severity && event.severity !== filters.severity) return false;
  if (filters.source_ip && event.source_ip !== filters.source_ip) return false;
  if (
    filters.destination_ip &&
    event.destination_ip !== filters.destination_ip
  ) {
    return false;
  }
  if (filters.status && event.status !== filters.status) return false;

  const timestamp = Date.parse(event.timestamp);
  if (filters.start_time && timestamp < Date.parse(filters.start_time)) {
    return false;
  }
  if (filters.end_time && timestamp > Date.parse(filters.end_time))
    return false;
  return true;
}

export function canInsertLiveEvent(filters: EventFilters): boolean {
  return (filters.page ?? 1) === 1 && !filters.start_time && !filters.end_time;
}

export function mergeEventPage(
  page: Page<SecurityEvent>,
  event: SecurityEvent,
): Page<SecurityEvent> {
  if (page.items.some((item) => item.id === event.id)) return page;

  const items = [event, ...page.items]
    .sort((left, right) => {
      const timeDifference =
        Date.parse(right.timestamp) - Date.parse(left.timestamp);
      return timeDifference || right.id.localeCompare(left.id);
    })
    .slice(0, page.page_size);
  const total = page.total + 1;
  return {
    ...page,
    items,
    total,
    pages: Math.ceil(total / page.page_size),
  };
}

export function alertMatchesFilters(
  alert: Alert,
  filters: AlertFilters,
): boolean {
  const contains = (value: string | null, expected: string | undefined) =>
    !expected || value?.toLowerCase().includes(expected.toLowerCase()) === true;
  if (filters.severity && alert.severity !== filters.severity) return false;
  if (filters.status && alert.status !== filters.status) return false;
  if (filters.active_only && !["new", "investigating"].includes(alert.status))
    return false;
  if (filters.rule_id && alert.detection_rule.rule_id !== filters.rule_id)
    return false;
  if (filters.asset_id && alert.asset_id !== filters.asset_id) return false;
  if (filters.source_ip && alert.source_ip !== filters.source_ip) return false;
  if (filters.destination_ip && alert.destination_ip !== filters.destination_ip)
    return false;
  if (!contains(alert.username, filters.username)) return false;
  const timestamp = Date.parse(alert.timestamp);
  if (filters.start_time && timestamp < Date.parse(filters.start_time))
    return false;
  if (filters.end_time && timestamp > Date.parse(filters.end_time))
    return false;
  return true;
}

export function canInsertLiveAlert(filters: AlertFilters): boolean {
  return (filters.page ?? 1) === 1 && !filters.start_time && !filters.end_time;
}

export function mergeAlertPage(page: Page<Alert>, alert: Alert): Page<Alert> {
  const alreadyPresent = page.items.some((item) => item.id === alert.id);
  const items = [alert, ...page.items.filter((item) => item.id !== alert.id)]
    .sort((left, right) => {
      const timeDifference =
        Date.parse(right.timestamp) - Date.parse(left.timestamp);
      return timeDifference || right.id.localeCompare(left.id);
    })
    .slice(0, page.page_size);
  const total = page.total + (alreadyPresent ? 0 : 1);
  return { ...page, items, total, pages: Math.ceil(total / page.page_size) };
}

export function removeAlertFromPage(
  page: Page<Alert>,
  alertId: string,
): Page<Alert> {
  if (!page.items.some((item) => item.id === alertId)) return page;
  const total = Math.max(0, page.total - 1);
  return {
    ...page,
    items: page.items.filter((item) => item.id !== alertId),
    total,
    pages: Math.ceil(total / page.page_size),
  };
}

export function reconnectDelay(
  attempt: number,
  jitter = Math.random(),
): number {
  const baseDelay = Math.min(1_000 * 2 ** Math.max(0, attempt), 30_000);
  return Math.round(baseDelay * (0.8 + Math.min(1, Math.max(0, jitter)) * 0.4));
}

export function telemetryWebSocketUrl(): string {
  const configured = import.meta.env.VITE_WS_URL;
  if (configured) return configured;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/api/v1/ws/events`;
}
