import type { Edge, Node } from "@xyflow/react";
import { MarkerType } from "@xyflow/react";

import type {
  NetworkConnectionUpdate,
  NetworkTopology,
  TopologyActivity,
  TopologyEdge,
  TopologyNode,
} from "../types/core";

const uuidPattern =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isUuid(value: string | null): value is string {
  return value !== null && uuidPattern.test(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return (
    Array.isArray(value) && value.every((item) => typeof item === "string")
  );
}

function isTopologyNode(value: unknown): value is TopologyNode {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.hostname === "string" &&
    typeof value.ip_address === "string" &&
    typeof value.asset_type === "string" &&
    typeof value.network_zone === "string" &&
    typeof value.status === "string" &&
    typeof value.risk_score === "number" &&
    typeof value.open_alert_count === "number" &&
    isStringArray(value.alert_ids)
  );
}

function isTopologyEdge(value: unknown): value is TopologyEdge {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.source_asset_id === "string" &&
    typeof value.destination_asset_id === "string" &&
    (typeof value.destination_port === "number" ||
      value.destination_port === null) &&
    typeof value.protocol === "string" &&
    typeof value.connection_type === "string" &&
    typeof value.last_seen === "string" &&
    typeof value.connection_count === "number" &&
    ["active", "recent", "historical"].includes(String(value.activity_state)) &&
    isStringArray(value.alert_ids)
  );
}

export function parseNetworkTopology(value: unknown): NetworkTopology {
  if (
    !isRecord(value) ||
    typeof value.generated_at !== "string" ||
    !["5m", "15m", "1h", "24h", "all"].includes(String(value.window)) ||
    !Array.isArray(value.nodes) ||
    !value.nodes.every(isTopologyNode) ||
    !Array.isArray(value.edges) ||
    !value.edges.every(isTopologyEdge) ||
    !Array.isArray(value.alerts) ||
    !Array.isArray(value.activities) ||
    !Array.isArray(value.observed_techniques) ||
    !isRecord(value.summary)
  ) {
    throw new Error("The topology API returned an invalid response.");
  }
  return value as unknown as NetworkTopology;
}

export function mergeConnectionUpdates(
  updates: readonly NetworkConnectionUpdate[],
  incoming: NetworkConnectionUpdate,
): NetworkConnectionUpdate[] {
  return [incoming, ...updates.filter((item) => item.id !== incoming.id)].sort(
    (left, right) =>
      Date.parse(right.last_seen) - Date.parse(left.last_seen) ||
      right.id.localeCompare(left.id),
  );
}

export type TopologyView =
  "all" | "alerts" | "high-risk" | "scenario" | "incident";

export function topologyLiveLabel(labOffline: boolean) {
  return labOffline ? "Historical · lab offline" : "Live updates";
}

export function initialTopologyView(
  scenarioRunId?: string,
  incidentId?: string,
): TopologyView {
  if (incidentId) return "incident";
  return scenarioRunId ? "scenario" : "all";
}

export function activityFocus(
  topology: NetworkTopology,
  activity: TopologyActivity,
): { edgeId: string | null; nodeId: string | null } {
  const edge = topology.edges.find((item) =>
    item.event_ids.includes(activity.id),
  );
  return edge
    ? { edgeId: edge.id, nodeId: null }
    : {
        edgeId: null,
        nodeId: activity.destination_asset_id ?? activity.source_asset_id,
      };
}

export interface AssetFlowData extends Record<string, unknown> {
  asset: TopologyNode;
  focused: boolean;
}

export interface ZoneFlowData extends Record<string, unknown> {
  label: string;
}

export interface ConnectionFlowData extends Record<string, unknown> {
  connection: TopologyEdge;
  focused: boolean;
}

export type AssetFlowNode = Node<AssetFlowData, "asset">;
export type ZoneFlowNode = Node<ZoneFlowData, "group">;
export type TopologyFlowNode = AssetFlowNode | ZoneFlowNode;
export type TopologyFlowEdge = Edge<ConnectionFlowData>;

export function topologyToFlowElements(
  topology: NetworkTopology,
  visibleZones: ReadonlySet<string>,
  view: TopologyView,
  focusedAssetId?: string,
  focusedAlertId?: string,
): { nodes: TopologyFlowNode[]; edges: TopologyFlowEdge[] } {
  const alertEdgeNodeIds = new Set(
    topology.edges
      .filter((edge) => edge.alert_ids.length > 0)
      .flatMap((edge) => [edge.source_asset_id, edge.destination_asset_id]),
  );
  const visibleAssets = topology.nodes.filter((asset) => {
    if (!visibleZones.has(asset.network_zone)) return false;
    if (view === "alerts") {
      return asset.open_alert_count > 0 || alertEdgeNodeIds.has(asset.id);
    }
    if (view === "high-risk") return asset.risk_score >= 60;
    return true;
  });
  const visibleIds = new Set(visibleAssets.map((asset) => asset.id));
  const zones = [
    ...new Set(visibleAssets.map((asset) => asset.network_zone)),
  ].sort((left, right) => {
    const preferred = ["dmz", "employee", "server"];
    const leftIndex = preferred.indexOf(left);
    const rightIndex = preferred.indexOf(right);
    if (leftIndex !== -1 || rightIndex !== -1) {
      return (
        (leftIndex === -1 ? 99 : leftIndex) -
        (rightIndex === -1 ? 99 : rightIndex)
      );
    }
    return left.localeCompare(right);
  });
  const nodes: TopologyFlowNode[] = [];
  zones.forEach((zone, zoneIndex) => {
    const members = visibleAssets
      .filter((asset) => asset.network_zone === zone)
      .sort((left, right) => left.hostname.localeCompare(right.hostname));
    const rows = Math.max(1, Math.ceil(members.length / 2));
    nodes.push({
      id: `zone:${zone}`,
      type: "group",
      position: { x: zoneIndex * 370, y: 20 },
      selectable: false,
      draggable: false,
      data: { label: `${zone.toUpperCase()} ZONE` },
      style: {
        width: 340,
        height: 82 + rows * 118,
        background: "rgba(11, 17, 26, 0.55)",
        border: "1px dashed #2c394a",
        borderRadius: 14,
        color: "#64748b",
        fontSize: 10,
        letterSpacing: "0.12em",
        padding: 12,
      },
    });
    members.forEach((asset, index) => {
      nodes.push({
        id: asset.id,
        type: "asset",
        parentId: `zone:${zone}`,
        extent: "parent",
        position: {
          x: 18 + (index % 2) * 154,
          y: 50 + Math.floor(index / 2) * 112,
        },
        data: {
          asset,
          focused:
            focusedAssetId === asset.id ||
            (focusedAlertId ? asset.alert_ids.includes(focusedAlertId) : false),
        },
      });
    });
  });

  const edges = topology.edges
    .filter(
      (edge) =>
        visibleIds.has(edge.source_asset_id) &&
        visibleIds.has(edge.destination_asset_id),
    )
    .map<TopologyFlowEdge>((connection) => {
      const focused = focusedAlertId
        ? connection.alert_ids.includes(focusedAlertId)
        : false;
      const color = connection.alert_ids.length
        ? "#fb7185"
        : connection.activity_state === "active"
          ? "#39c6a3"
          : connection.activity_state === "recent"
            ? "#38bdf8"
            : "#526173";
      return {
        id: connection.id,
        source: connection.source_asset_id,
        target: connection.destination_asset_id,
        type: "smoothstep",
        animated: connection.activity_state === "active",
        label: `${connection.connection_type}${connection.destination_port ? `:${connection.destination_port}` : ""}`,
        labelStyle: { fill: focused ? "#f8fafc" : "#94a3b8", fontSize: 9 },
        labelBgStyle: { fill: "#0b111a", fillOpacity: 0.92 },
        markerEnd: { type: MarkerType.ArrowClosed, color },
        style: {
          stroke: color,
          strokeWidth: focused || connection.alert_ids.length ? 2.5 : 1.5,
        },
        data: { connection, focused },
      };
    });
  return { nodes, edges };
}
