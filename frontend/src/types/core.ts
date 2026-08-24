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

export interface DashboardSummary {
  total_assets: number;
  online_assets: number;
  high_risk_assets: number;
  events_today: number;
  events_last_hour: number;
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
