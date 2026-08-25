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
  event_type?: string;
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
