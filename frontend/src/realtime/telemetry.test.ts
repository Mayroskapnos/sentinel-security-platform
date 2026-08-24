import { describe, expect, it } from "vitest";

import type { Page, SecurityEvent } from "../types/core";
import {
  canInsertLiveEvent,
  eventMatchesFilters,
  mergeEventPage,
  parseTelemetryMessage,
  reconnectDelay,
} from "./telemetry";

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
    asset: {
      id: "837e38d2-032a-42d4-9f58-e2699153ea77",
      hostname: "employee-01",
      display_name: "Employee 01",
    },
    created_at: "2026-08-24T14:22:17.025Z",
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
        severity: "low",
        status: "failed",
      }),
    ).toBe(true);
    expect(eventMatchesFilters(event, { severity: "critical" })).toBe(false);
    expect(canInsertLiveEvent({ page: 1 })).toBe(true);
    expect(canInsertLiveEvent({ page: 7 })).toBe(false);
    expect(
      canInsertLiveEvent({ page: 1, end_time: "2026-08-23T00:00:00Z" }),
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
});
