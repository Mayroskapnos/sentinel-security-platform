import { describe, expect, it } from "vitest";

import type { Alert, Page, SecurityEvent } from "../types/core";
import { queryKeys } from "../hooks/useCoreData";
import {
  authoritativeRefreshQueryKeys,
  shouldRefreshAuthoritativeState,
} from "./cacheRefresh";
import {
  alertMatchesFilters,
  canInsertLiveAlert,
  canInsertLiveEvent,
  eventMatchesFilters,
  mergeAlertPage,
  mergeEventPage,
  parseTelemetryMessage,
  reconnectDelay,
} from "./telemetry";
import { mergeConnectionUpdates } from "../lib/network";

function securityEvent(overrides: Partial<SecurityEvent> = {}): SecurityEvent {
  return {
    id: "c4eecaf4-5b7d-4e53-8200-2df79d91a012",
    timestamp: "2026-08-24T14:22:17Z",
    event_type: "authentication",
    source: "linux_auth",
    source_ip: "10.10.50.2",
    destination_ip: "10.10.20.10",
    source_port: 44000,
    destination_port: 22,
    hostname: "employee-01",
    username: "demo-user",
    process_name: "sshd",
    action: "ssh_login",
    status: "failed",
    severity: "low",
    raw_event: { message: "Synthetic development telemetry" },
    normalized_data: { service: "ssh" },
    asset_id: "837e38d2-032a-42d4-9f58-e2699153ea77",
    scenario_run_id: null,
    scenario_id: null,
    asset: {
      id: "837e38d2-032a-42d4-9f58-e2699153ea77",
      hostname: "employee-01",
      display_name: "Employee 01",
    },
    created_at: "2026-08-24T14:22:17.025Z",
    ...overrides,
  };
}

function alert(overrides: Partial<Alert> = {}): Alert {
  return {
    id: "5d5da7a4-7e3c-4b23-848e-f9c7c6dcce8c",
    timestamp: "2026-08-24T14:22:17Z",
    title: "SSH Brute Force Activity",
    description: "Repeated failed SSH authentication attempts.",
    severity: "high",
    status: "new",
    detection_rule_id: "356d9f02-ff8b-49b0-b65f-af1c08c58bc2",
    detection_rule: {
      id: "356d9f02-ff8b-49b0-b65f-af1c08c58bc2",
      rule_id: "DET-SSH-001",
      name: "SSH Brute Force Activity",
    },
    asset_id: "837e38d2-032a-42d4-9f58-e2699153ea77",
    asset: {
      id: "837e38d2-032a-42d4-9f58-e2699153ea77",
      hostname: "employee-01",
      display_name: "Employee 01",
    },
    source_ip: "10.10.50.2",
    destination_ip: "10.10.20.10",
    username: "demo-user",
    risk_score: 72,
    mitre_tactic: "Credential Access",
    mitre_technique_id: "T1110",
    mitre_technique_name: "Brute Force",
    evidence: { observed_count: 10 },
    metadata_json: { rule_type: "threshold" },
    evidence_count: 10,
    first_event_at: "2026-08-24T14:22:08Z",
    last_event_at: "2026-08-24T14:22:17Z",
    created_at: "2026-08-24T14:22:17.025Z",
    updated_at: "2026-08-24T14:22:17.025Z",
    incident: null,
    ...overrides,
  };
}

describe("telemetry message parsing", () => {
  it("accepts a typed security event envelope", () => {
    const event = securityEvent();
    const parsed = parseTelemetryMessage(
      JSON.stringify({
        version: "1",
        type: "security_event",
        timestamp: "2026-08-24T14:22:17Z",
        data: event,
      }),
    );
    expect(parsed?.type).toBe("security_event");
    if (parsed?.type !== "security_event") {
      throw new Error("Expected security_event message");
    }
    expect(parsed.data.id).toBe(event.id);
  });

  it("ignores malformed or unsupported messages", () => {
    expect(parseTelemetryMessage("not-json")).toBeNull();
    expect(
      parseTelemetryMessage(
        JSON.stringify({ version: "2", type: "security_event", data: {} }),
      ),
    ).toBeNull();
  });

  it("accepts typed simulation progress for REST refetch", () => {
    const parsed = parseTelemetryMessage(
      JSON.stringify({
        version: "1",
        type: "simulation_step",
        timestamp: "2026-08-25T12:00:00Z",
        data: {
          run_id: "1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d",
          scenario_id: "SCN-005",
          status: "running",
          current_step: 3,
          total_steps: 5,
          label: "Internal service activity",
          message: "Action started.",
        },
      }),
    );
    expect(parsed?.type).toBe("simulation_step");
  });

  it("accepts compact connection updates and deduplicates them by identity", () => {
    const update = {
      id: "3dc90e82-759a-4ef1-b60b-24c4e8dd5685",
      source_asset_id: "1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d",
      destination_asset_id: "52384fa9-ebc1-475e-a1d7-16c8a3a3781a",
      destination_port: 22,
      protocol: "tcp",
      connection_type: "ssh",
      last_seen: "2026-08-25T12:10:00Z",
      connection_count: 12,
      last_status: "success",
    };
    const parsed = parseTelemetryMessage(
      JSON.stringify({
        version: "1",
        type: "network_connection_updated",
        timestamp: update.last_seen,
        data: update,
      }),
    );
    expect(parsed?.type).toBe("network_connection_updated");
    expect(
      mergeConnectionUpdates(
        [
          {
            ...update,
            connection_count: 11,
            last_seen: "2026-08-25T12:09:00Z",
          },
        ],
        update,
      ),
    ).toEqual([update]);
  });

  it("accepts typed incident messages for authoritative refresh", () => {
    const parsed = parseTelemetryMessage(
      JSON.stringify({
        version: "1",
        type: "incident_created",
        timestamp: "2026-08-25T12:10:00Z",
        data: {
          id: "3dc90e82-759a-4ef1-b60b-24c4e8dd5685",
          incident_number: "INC-3DC90E82",
          title: "Possible Credential Compromise",
          severity: "high",
          status: "open",
          confidence_score: 85,
          risk_score: 76,
          first_activity_at: "2026-08-25T12:00:00Z",
          last_activity_at: "2026-08-25T12:10:00Z",
          created_at: "2026-08-25T12:00:01Z",
          updated_at: "2026-08-25T12:10:01Z",
          alert_count: 2,
          asset_count: 1,
          event_count: 11,
          affected_assets: ["employee-01"],
          scenario_run_id: null,
        },
      }),
    );
    expect(parsed?.type).toBe("incident_created");
  });

  it("accepts analysis completion messages for REST recovery", () => {
    const parsed = parseTelemetryMessage(
      JSON.stringify({
        version: "1",
        type: "analysis_completed",
        timestamp: "2026-08-26T10:00:02Z",
        data: {
          analysis_id: "44444444-4444-4444-4444-444444444444",
          incident_id: "11111111-1111-1111-1111-111111111111",
          status: "completed",
        },
      }),
    );
    expect(parsed?.type).toBe("analysis_completed");
    if (parsed?.type !== "analysis_completed") {
      throw new Error("Expected analysis_completed message");
    }
    expect(parsed.data.incident_id).toBe(
      "11111111-1111-1111-1111-111111111111",
    );
  });
});

describe("live event cache behavior", () => {
  it("deduplicates by persistent event ID", () => {
    const event = securityEvent();
    const page: Page<SecurityEvent> = {
      items: [event],
      page: 1,
      page_size: 20,
      total: 1,
      pages: 1,
    };
    expect(mergeEventPage(page, event)).toBe(page);
  });

  it("matches filters and protects historical pagination", () => {
    const event = securityEvent();
    expect(
      eventMatchesFilters(event, {
        hostname: "employee",
        source: "linux_auth",
        severity: "low",
        status: "failed",
      }),
    ).toBe(true);
    expect(eventMatchesFilters(event, { source: "postgresql" })).toBe(false);
    expect(eventMatchesFilters(event, { severity: "critical" })).toBe(false);
    expect(canInsertLiveEvent({ page: 1 })).toBe(true);
    expect(canInsertLiveEvent({ page: 7 })).toBe(false);
    expect(
      canInsertLiveEvent({ page: 1, end_time: "2026-08-23T00:00:00Z" }),
    ).toBe(false);
  });
});

describe("live alert cache behavior", () => {
  it("parses alert envelopes with persistent identity", () => {
    const detectionAlert = alert();
    const parsed = parseTelemetryMessage(
      JSON.stringify({
        version: "1",
        type: "alert_created",
        timestamp: detectionAlert.created_at,
        data: detectionAlert,
      }),
    );
    expect(parsed?.type).toBe("alert_created");
    if (parsed?.type !== "alert_created")
      throw new Error("Expected alert_created");
    expect(parsed.data.id).toBe(detectionAlert.id);
  });

  it("deduplicates updates by alert ID without inflating totals", () => {
    const created = alert();
    const page: Page<Alert> = {
      items: [created],
      page: 1,
      page_size: 20,
      total: 1,
      pages: 1,
    };
    const updated = alert({ status: "investigating", evidence_count: 11 });
    const merged = mergeAlertPage(page, updated);
    expect(merged.total).toBe(1);
    expect(merged.items).toHaveLength(1);
    expect(merged.items[0].status).toBe("investigating");
    expect(merged.items[0].evidence_count).toBe(11);
  });

  it("respects alert filters and historical pagination", () => {
    const detectionAlert = alert();
    expect(
      alertMatchesFilters(detectionAlert, {
        severity: "high",
        status: "new",
        rule_id: "DET-SSH-001",
      }),
    ).toBe(true);
    expect(alertMatchesFilters(detectionAlert, { status: "resolved" })).toBe(
      false,
    );
    expect(canInsertLiveAlert({ page: 1 })).toBe(true);
    expect(canInsertLiveAlert({ page: 2 })).toBe(false);
    expect(
      canInsertLiveAlert({ page: 1, start_time: "2026-08-01T00:00:00Z" }),
    ).toBe(false);
  });
});

describe("reconnect backoff", () => {
  it("grows exponentially and remains capped with deterministic jitter", () => {
    expect(reconnectDelay(0, 0.5)).toBe(1_000);
    expect(reconnectDelay(1, 0.5)).toBe(2_000);
    expect(reconnectDelay(2, 0.5)).toBe(4_000);
    expect(reconnectDelay(20, 0.5)).toBe(30_000);
  });

  it("refetches authoritative simulator state only after a reconnect", () => {
    expect(shouldRefreshAuthoritativeState(false)).toBe(false);
    expect(shouldRefreshAuthoritativeState(true)).toBe(true);
    expect(authoritativeRefreshQueryKeys()).toContain(queryKeys.simulator.all);
    expect(authoritativeRefreshQueryKeys()).toContain(queryKeys.network.all);
  });
});
