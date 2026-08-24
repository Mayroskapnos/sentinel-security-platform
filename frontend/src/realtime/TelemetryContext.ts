import { createContext, useContext } from "react";

import type { SecurityEvent } from "../types/core";
import type { TelemetryConnectionState } from "./telemetry";

export interface TelemetryContextValue {
  connectionState: TelemetryConnectionState;
  receivedEvents: readonly SecurityEvent[];
  liveEventIds: ReadonlySet<string>;
}

export const TelemetryContext = createContext<TelemetryContextValue | null>(
  null,
);

export function useTelemetry(): TelemetryContextValue {
  const context = useContext(TelemetryContext);
  if (!context) {
    throw new Error("useTelemetry must be used inside TelemetryProvider");
  }
  return context;
}
