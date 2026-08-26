import { ReactFlowProvider } from "@xyflow/react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { AssetTopologyNode } from "../components/network/AttackTopology";
import {
  activityFocus,
  initialTopologyView,
  isUuid,
  parseNetworkTopology,
  topologyLiveLabel,
  topologyToFlowElements,
} from "../lib/network";
import type {
  NetworkTopology,
  TopologyEdge,
  TopologyNode,
} from "../types/core";
import { SelectionPanel } from "./AttackMapPage";

const source: TopologyNode = {
  id: "1a7a65a3-4cb0-4fa6-a2ea-1e266594ee8d",
  hostname: "employee-01",
  display_name: "Employee Workstation 01",
  ip_address: "10.10.20.10",
  asset_type: "workstation",
  operating_system: "Debian 13",
  environment: "lab",
  network_zone: "employee",
  status: "online",
  risk_score: 62,
  criticality: "medium",
  first_seen: "2026-08-25T12:00:00Z",
  last_seen: "2026-08-25T12:10:00Z",
  open_alert_count: 1,
  recent_event_count: 12,
  recent_connection_count: 1,
  alert_ids: ["4c277036-b028-4a3f-b308-e2317cf6e370"],
};
const destination: TopologyNode = {
  ...source,
  id: "52384fa9-ebc1-475e-a1d7-16c8a3a3781a",
  hostname: "admin-server",
  display_name: "Administrative Server",
  ip_address: "10.10.30.10",
  asset_type: "server",
  network_zone: "server",
  risk_score: 77,
  criticality: "critical",
};
const connection: TopologyEdge = {
  id: "3dc90e82-759a-4ef1-b60b-24c4e8dd5685",
  source_asset_id: source.id,
  destination_asset_id: destination.id,
  source_ip: source.ip_address,
  destination_ip: destination.ip_address,
  source_port: 45220,
  destination_port: 22,
  protocol: "tcp",
  connection_type: "ssh",
  first_seen: "2026-08-25T12:00:00Z",
  last_seen: "2026-08-25T12:10:00Z",
  connection_count: 12,
  recent_event_count: 12,
  last_status: "success",
  activity_state: "active",
  alert_ids: source.alert_ids,
  scenario_run_ids: [source.id],
  event_ids: [],
};
const topology: NetworkTopology = {
  generated_at: "2026-08-25T12:10:01Z",
  window: "15m",
  scenario: {
    run_id: source.id,
    scenario_id: "SCN-005",
    scenario_name: "Enterprise exercise",
    status: "completed",
    event_count: 37,
    alert_count: 5,
    started_at: "2026-08-25T12:00:00Z",
    finished_at: "2026-08-25T12:10:00Z",
  },
  nodes: [source, destination],
  edges: [connection],
  alerts: [],
  activities: [],
  observed_techniques: [],
  summary: {
    asset_count: 2,
    connection_count: 1,
    active_connection_count: 1,
    open_alert_count: 1,
    high_risk_asset_count: 2,
    activity_count: 0,
    activity_truncated: false,
  },
};

describe("Attack Map topology", () => {
  it("parses a valid bulk topology and rejects malformed responses", () => {
    expect(parseNetworkTopology(topology)).toEqual(topology);
    expect(() => parseNetworkTopology({ ...topology, edges: [{}] })).toThrow(
      "invalid response",
    );
  });

  it("converts assets into stable zone groups and observed React Flow edges", () => {
    const flow = topologyToFlowElements(
      topology,
      new Set(["employee", "server"]),
      "all",
      source.id,
      source.alert_ids[0],
    );
    expect(flow.nodes.map((node) => node.id)).toEqual([
      "zone:employee",
      source.id,
      "zone:server",
      destination.id,
    ]);
    expect(flow.edges).toHaveLength(1);
    expect(flow.edges[0].source).toBe(source.id);
    expect(flow.edges[0].animated).toBe(true);
    expect(flow.edges[0].data?.focused).toBe(true);
  });

  it("renders asset identity, alert state, and risk in a custom node", () => {
    const markup = renderToStaticMarkup(
      <ReactFlowProvider>
        <AssetTopologyNode
          data={{ asset: source, focused: true }}
          deletable={false}
          draggable={false}
          dragging={false}
          id={source.id}
          isConnectable={false}
          positionAbsoluteX={0}
          positionAbsoluteY={0}
          selected={false}
          selectable={true}
          type="asset"
          zIndex={0}
        />
      </ReactFlowProvider>,
    );
    expect(markup).toContain("employee-01");
    expect(markup).toContain("10.10.20.10");
    expect(markup).toContain("1 alerts");
    expect(markup).toContain("Risk 62");
  });

  it("renders selected node and selected edge evidence panels", () => {
    const nodeMarkup = renderToStaticMarkup(
      <MemoryRouter>
        <SelectionPanel edge={null} node={source} onClose={() => undefined} />
      </MemoryRouter>,
    );
    const edgeMarkup = renderToStaticMarkup(
      <MemoryRouter>
        <SelectionPanel
          edge={connection}
          node={null}
          onClose={() => undefined}
        />
      </MemoryRouter>,
    );
    expect(nodeMarkup).toContain("Open asset profile");
    expect(nodeMarkup).toContain("Recent events");
    expect(edgeMarkup).toContain("Observed relationship");
    expect(edgeMarkup).toContain("Lifetime observations");
    expect(edgeMarkup).toContain("View alert");
  });

  it("validates scenario-run and asset deep-link identifiers", () => {
    expect(isUuid(source.id)).toBe(true);
    expect(isUuid("SCN-005")).toBe(false);
    expect(isUuid(null)).toBe(false);
    expect(initialTopologyView(source.id)).toBe("scenario");
    expect(initialTopologyView()).toBe("all");
  });

  it("labels offline lab topology as historical and still inspectable", () => {
    expect(topologyLiveLabel(true)).toBe("Historical · lab offline");
    expect(topologyLiveLabel(false)).toBe("Live updates");
  });

  it("keeps zone-only empty views and filters high-risk nodes without inventing edges", () => {
    const empty = topologyToFlowElements(
      { ...topology, edges: [] },
      new Set(["employee", "server"]),
      "all",
    );
    expect(empty.edges).toEqual([]);
    expect(empty.nodes).toHaveLength(4);
    const highRisk = topologyToFlowElements(
      { ...topology, nodes: [{ ...source, risk_score: 20 }, destination] },
      new Set(["employee", "server"]),
      "high-risk",
    );
    expect(highRisk.nodes.map((node) => node.id)).toEqual([
      "zone:server",
      destination.id,
    ]);
    expect(highRisk.edges).toEqual([]);
  });

  it("focuses timeline connection evidence or its local activity asset", () => {
    const networkActivity = {
      id: "2606d435-97db-4f0a-b5a3-3a6ee7168230",
      timestamp: topology.generated_at,
      event_type: "authentication",
      action: "ssh_login",
      status: "success",
      source_asset_id: source.id,
      destination_asset_id: destination.id,
      source_ip: source.ip_address,
      destination_ip: destination.ip_address,
      destination_port: 22,
      scenario_run_id: topology.scenario!.run_id,
    };
    const withEvidence = {
      ...topology,
      edges: [{ ...connection, event_ids: [networkActivity.id] }],
    };
    expect(activityFocus(withEvidence, networkActivity)).toEqual({
      edgeId: connection.id,
      nodeId: null,
    });
    expect(
      activityFocus(topology, {
        ...networkActivity,
        id: "dc52f858-1355-4b7f-be87-d2f103cff862",
        event_type: "privilege",
        action: "sudo_command",
        destination_asset_id: null,
        destination_ip: null,
        destination_port: null,
      }),
    ).toEqual({ edgeId: null, nodeId: source.id });
  });
});
