import {
  Background,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type NodeProps,
} from "@xyflow/react";
import { Box, Database, Monitor, Network, Server } from "lucide-react";
import { useMemo } from "react";

import {
  topologyToFlowElements,
  type AssetFlowNode,
  type TopologyView,
} from "../../lib/network";
import type {
  NetworkTopology,
  TopologyEdge,
  TopologyNode,
} from "../../types/core";

function AssetIcon({ assetType }: { assetType: TopologyNode["asset_type"] }) {
  if (assetType === "workstation")
    return <Monitor className="size-4" strokeWidth={1.8} />;
  if (assetType === "database")
    return <Database className="size-4" strokeWidth={1.8} />;
  if (assetType === "network_device")
    return <Network className="size-4" strokeWidth={1.8} />;
  if (["server", "web_server"].includes(assetType))
    return <Server className="size-4" strokeWidth={1.8} />;
  return <Box className="size-4" strokeWidth={1.8} />;
}

function riskColor(score: number) {
  if (score >= 80) return "#fb7185";
  if (score >= 60) return "#fb923c";
  if (score >= 35) return "#fbbf24";
  return "#39c6a3";
}

export function AssetTopologyNode({ data }: NodeProps<AssetFlowNode>) {
  const { asset, focused } = data;
  return (
    <div
      className={`w-[136px] rounded-xl border bg-[#111a27] p-3 shadow-lg transition-colors ${
        focused
          ? "border-accent ring-2 ring-accent/20"
          : asset.open_alert_count
            ? "border-rose-400/55"
            : "border-[#2a394c]"
      }`}
      title={`${asset.display_name} · ${asset.ip_address}`}
    >
      <Handle
        className="!size-2 !border-[#101722] !bg-slate-500"
        position={Position.Left}
        type="target"
      />
      <div className="flex items-start justify-between gap-2">
        <span className="grid size-7 place-items-center rounded-lg bg-white/[0.04] text-accent">
          <AssetIcon assetType={asset.asset_type} />
        </span>
        <span
          className="mt-1 size-2 rounded-full"
          style={{
            backgroundColor: asset.status === "online" ? "#39c6a3" : "#64748b",
          }}
          title={asset.status}
        />
      </div>
      <p className="mt-2 truncate text-[11px] font-semibold text-slate-100">
        {asset.hostname}
      </p>
      <p className="mt-1 font-mono text-[9px] text-slate-500">
        {asset.ip_address}
      </p>
      <div className="mt-2 flex items-center justify-between text-[9px] text-slate-500">
        <span>{asset.open_alert_count} alerts</span>
        <span style={{ color: riskColor(asset.risk_score) }}>
          Risk {Math.round(asset.risk_score)}
        </span>
      </div>
      <Handle
        className="!size-2 !border-[#101722] !bg-slate-500"
        position={Position.Right}
        type="source"
      />
    </div>
  );
}

export function AttackTopology({
  topology,
  visibleZones,
  view,
  focusedAssetId,
  focusedAlertId,
  onSelectAsset,
  onSelectEdge,
}: {
  topology: NetworkTopology;
  visibleZones: ReadonlySet<string>;
  view: TopologyView;
  focusedAssetId?: string;
  focusedAlertId?: string;
  onSelectAsset: (asset: TopologyNode) => void;
  onSelectEdge: (edge: TopologyEdge) => void;
}) {
  const elements = useMemo(
    () =>
      topologyToFlowElements(
        topology,
        visibleZones,
        view,
        focusedAssetId,
        focusedAlertId,
      ),
    [topology, visibleZones, view, focusedAssetId, focusedAlertId],
  );
  const nodeTypes = useMemo(() => ({ asset: AssetTopologyNode }), []);

  return (
    <div
      className="h-[620px] min-h-[480px] w-full"
      data-testid="attack-topology"
    >
      <ReactFlow
        colorMode="dark"
        edges={elements.edges}
        fitView
        fitViewOptions={{ padding: 0.16, maxZoom: 1.2 }}
        minZoom={0.35}
        nodes={elements.nodes}
        nodesConnectable={false}
        nodeTypes={nodeTypes}
        onEdgeClick={(_, edge) => {
          if (edge.data?.connection) onSelectEdge(edge.data.connection);
        }}
        onNodeClick={(_, node) => {
          if (node.type === "asset" && "asset" in node.data) {
            onSelectAsset(node.data.asset as TopologyNode);
          }
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#233044" gap={24} size={1} />
        <Controls position="bottom-left" showInteractive={false} />
        <MiniMap
          maskColor="rgba(9, 13, 20, 0.7)"
          nodeColor={(node) => (node.type === "group" ? "#182233" : "#39c6a3")}
          pannable
          position="bottom-right"
          zoomable
        />
      </ReactFlow>
    </div>
  );
}
