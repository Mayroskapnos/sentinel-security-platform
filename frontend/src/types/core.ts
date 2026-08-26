export type AssetType =
  | "workstation"
  | "server"
  | "web_server"
  | "database"
  | "container"
  | "network_device"
  | "unknown";

export type AssetStatus =
  "online" | "offline" | "warning" | "critical" | "unknown";

export type Criticality = "low" | "medium" | "high" | "critical";
export type EventSeverity =
  "informational" | "low" | "medium" | "high" | "critical";
export type AlertStatus =
  "new" | "investigating" | "resolved" | "false_positive";
export type RuleType = "threshold" | "sequence" | "single_event";
export type ScenarioRunStatus =
  "pending" | "running" | "completed" | "failed" | "cancelled";
export type ScenarioStepStatus =
  "pending" | "running" | "completed" | "failed" | "skipped" | "cancelled";

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface Asset {
  id: string;
  hostname: string;
  display_name: string;
  ip_address: string;
  mac_address: string | null;
  asset_type: AssetType;
  operating_system: string;
  environment: string;
  network_zone: string;
  status: AssetStatus;
  risk_score: number;
  criticality: Criticality;
  first_seen: string;
  last_seen: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AssetReference {
  id: string;
  hostname: string;
  display_name: string;
}

export interface SecurityEvent {
  id: string;
  timestamp: string;
  event_type: string;
  source: string;
  source_ip: string | null;
  destination_ip: string | null;
  source_port: number | null;
  destination_port: number | null;
  hostname: string | null;
  username: string | null;
  process_name: string | null;
  action: string;
  status: string;
  severity: EventSeverity;
  raw_event: Record<string, unknown>;
  normalized_data: Record<string, unknown>;
  asset_id: string | null;
  scenario_run_id: string | null;
  scenario_id: string | null;
  asset: AssetReference | null;
  created_at: string;
}

export interface AlertRuleReference {
  id: string;
  rule_id: string;
  name: string;
}

export interface Alert {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  severity: EventSeverity;
  status: AlertStatus;
  detection_rule_id: string;
  detection_rule: AlertRuleReference;
  asset_id: string | null;
  asset: AssetReference | null;
  source_ip: string | null;
  destination_ip: string | null;
  username: string | null;
  risk_score: number;
  mitre_tactic: string | null;
  mitre_technique_id: string | null;
  mitre_technique_name: string | null;
  evidence: Record<string, unknown>;
  metadata_json: Record<string, unknown>;
  evidence_count: number;
  first_event_at: string;
  last_event_at: string;
  created_at: string;
  updated_at: string;
}

export type EvidenceEvent = Omit<
  SecurityEvent,
  "raw_event" | "normalized_data" | "asset" | "created_at"
>;

export interface AlertDetail extends Alert {
  evidence_events: EvidenceEvent[];
}

export interface DetectionRule {
  id: string;
  rule_id: string;
  name: string;
  description: string;
  rule_type: RuleType;
  severity: EventSeverity;
  enabled: boolean;
  event_type: string | null;
  configuration: Record<string, unknown>;
  mitre_tactic: string | null;
  mitre_technique_id: string | null;
  mitre_technique_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssetFilters {
  search?: string;
  asset_type?: AssetType;
  status?: AssetStatus;
  network_zone?: string;
  criticality?: Criticality;
  min_risk_score?: number;
  page?: number;
  page_size?: number;
}

export interface EventFilters {
  hostname?: string;
  asset_id?: string;
  scenario_run_id?: string;
  event_type?: string;
  source?: string;
  severity?: EventSeverity;
  source_ip?: string;
  destination_ip?: string;
  username?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

export interface AlertFilters {
  severity?: EventSeverity;
  status?: AlertStatus;
  rule_id?: string;
  asset_id?: string;
  source_ip?: string;
  destination_ip?: string;
  username?: string;
  active_only?: boolean;
  start_time?: string;
  end_time?: string;
  page?: number;
  page_size?: number;
}

export interface DetectionRuleFilters {
  enabled?: boolean;
  rule_type?: RuleType;
  severity?: EventSeverity;
  event_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface DashboardSummary {
  total_assets: number;
  online_assets: number;
  high_risk_assets: number;
  events_today: number;
  events_last_hour: number;
  open_alerts: number;
  critical_alerts: number;
  high_alerts: number;
}

export interface CountBucket {
  name: string;
  count: number;
}

export interface TimeBucket {
  timestamp: string;
  count: number;
}

export interface ActiveAssetBucket {
  asset_id: string | null;
  hostname: string;
  count: number;
}

export interface DashboardActivity {
  window: {
    start: string;
    end: string;
    hours: number;
  };
  events_over_time: TimeBucket[];
  events_by_severity: CountBucket[];
  events_by_type: CountBucket[];
  most_active_assets: ActiveAssetBucket[];
}

export interface LabAssetStatus {
  hostname: string;
  display_name: string;
  network_zone: string;
  status: "online" | "offline";
  telemetry_status: "active" | "stale";
  last_telemetry: string | null;
}

export interface LabSourceStatus {
  source: string;
  status: "active" | "stale";
  last_telemetry: string | null;
}

export interface LabStatus {
  version: string;
  status: "running" | "degraded" | "offline";
  collector_status: "active" | "stale";
  active_assets: number;
  total_assets: number;
  assets: LabAssetStatus[];
  sources: LabSourceStatus[];
}

export interface ScenarioSummary {
  id: string;
  name: string;
  description: string;
  risk: "low";
  estimated_seconds: number;
  targets: string[];
  expected_detections: string[];
  step_count: number;
}

export interface ScenarioStepDefinition {
  name: string;
  action: string;
  target: string | null;
  count: number | null;
  seconds: number | null;
}

export interface ScenarioDetail extends ScenarioSummary {
  steps: ScenarioStepDefinition[];
}

export interface ScenarioRunStep {
  index: number;
  name: string;
  action: string;
  status: ScenarioStepStatus;
  started_at: string | null;
  finished_at: string | null;
  message: string | null;
}

export interface DetectionObservation {
  rule_id: string;
  observed: boolean;
  alert_ids: string[];
  note: string | null;
}

export interface ScenarioAlertReference {
  id: string;
  rule_id: string;
  title: string;
  severity: EventSeverity;
  timestamp: string;
}

export interface ScenarioRun {
  id: string;
  scenario_id: string;
  scenario_name: string;
  status: ScenarioRunStatus;
  started_at: string | null;
  finished_at: string | null;
  current_step: number;
  total_steps: number;
  requested_by: string;
  steps: ScenarioRunStep[];
  expected_detections: string[];
  targets: string[];
  result: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  event_count: number;
  alert_count: number;
  detections: DetectionObservation[];
  alerts: ScenarioAlertReference[];
}

export interface SimulatorStatus {
  enabled: boolean;
  available: boolean;
  state: "disabled" | "unavailable" | "idle" | "running";
  active_run: ScenarioRun | null;
  message: string;
}

export type TopologyWindow = "5m" | "15m" | "1h" | "24h" | "all";
export type ConnectionActivityState = "active" | "recent" | "historical";

export interface NetworkConnectionUpdate {
  id: string;
  source_asset_id: string;
  destination_asset_id: string;
  destination_port: number | null;
  protocol: string;
  connection_type: string;
  last_seen: string;
  connection_count: number;
  last_status: string;
}

export interface TopologyNode {
  id: string;
  hostname: string;
  display_name: string;
  ip_address: string;
  asset_type: AssetType;
  operating_system: string;
  environment: string;
  network_zone: string;
  status: AssetStatus;
  risk_score: number;
  criticality: Criticality;
  first_seen: string;
  last_seen: string;
  open_alert_count: number;
  recent_event_count: number;
  recent_connection_count: number;
  alert_ids: string[];
}

export interface TopologyEdge {
  id: string;
  source_asset_id: string;
  destination_asset_id: string;
  source_ip: string;
  destination_ip: string;
  source_port: number | null;
  destination_port: number | null;
  protocol: string;
  connection_type: string;
  first_seen: string;
  last_seen: string;
  connection_count: number;
  recent_event_count: number;
  last_status: string;
  activity_state: ConnectionActivityState;
  alert_ids: string[];
  scenario_run_ids: string[];
  event_ids: string[];
}

export interface TopologyAlert {
  id: string;
  title: string;
  severity: EventSeverity;
  status: AlertStatus;
  rule_id: string;
  timestamp: string;
}

export interface TopologyActivity {
  id: string;
  timestamp: string;
  event_type: string;
  action: string;
  status: string;
  source_asset_id: string | null;
  destination_asset_id: string | null;
  source_ip: string | null;
  destination_ip: string | null;
  destination_port: number | null;
  scenario_run_id: string | null;
}

export interface ObservedTechnique {
  technique_id: string;
  technique_name: string;
  tactic: string;
  alert_ids: string[];
}

export interface TopologyScenarioContext {
  run_id: string;
  scenario_id: string;
  scenario_name: string;
  status: ScenarioRunStatus;
  event_count: number;
  alert_count: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface NetworkTopology {
  generated_at: string;
  window: TopologyWindow;
  scenario: TopologyScenarioContext | null;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  alerts: TopologyAlert[];
  activities: TopologyActivity[];
  observed_techniques: ObservedTechnique[];
  summary: {
    asset_count: number;
    connection_count: number;
    active_connection_count: number;
    open_alert_count: number;
    high_risk_asset_count: number;
    activity_count: number;
    activity_truncated: boolean;
  };
}

export interface TopologyParameters {
  window: TopologyWindow;
  scenario_run_id?: string;
  asset_id?: string;
  alert_id?: string;
}
