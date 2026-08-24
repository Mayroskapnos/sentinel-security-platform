import { LoaderCircle, Radio, WifiOff } from "lucide-react";

import type { TelemetryConnectionState } from "../realtime/telemetry";

const labels: Record<TelemetryConnectionState, string> = {
  connecting: "Connecting",
  connected: "Live",
  reconnecting: "Reconnecting",
  disconnected: "Offline",
  error: "Connection error",
};

export function TelemetryBadge({ state }: { state: TelemetryConnectionState }) {
  const connected = state === "connected";
  const waiting = state === "connecting" || state === "reconnecting";
  const Icon = connected ? Radio : waiting ? LoaderCircle : WifiOff;
  return (
    <div
      aria-live="polite"
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs ${
        connected
          ? "border-accent/25 bg-accent/10 text-accent"
          : "border-line bg-panel text-muted"
      }`}
      title={`Live telemetry WebSocket: ${labels[state]}`}
    >
      <Icon className={`size-3.5 ${waiting ? "animate-spin" : ""}`} />
      <span className="hidden sm:inline">Telemetry</span>
      <span>{labels[state]}</span>
    </div>
  );
}
