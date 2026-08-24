import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { queryKeys } from "../hooks/useCoreData";
import type { Asset, EventFilters, Page, SecurityEvent } from "../types/core";
import { TelemetryContext } from "./TelemetryContext";
import {
  canInsertLiveEvent,
  eventMatchesFilters,
  mergeEventPage,
  parseTelemetryMessage,
  reconnectDelay,
  type TelemetryConnectionState,
  telemetryWebSocketUrl,
} from "./telemetry";

export function TelemetryProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [connectionState, setConnectionState] =
    useState<TelemetryConnectionState>("connecting");
  const [receivedEvents, setReceivedEvents] = useState<
    readonly SecurityEvent[]
  >([]);
  const [liveEventIds, setLiveEventIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const liveTimers = useRef(new Map<string, number>());

  useEffect(() => {
    const timers = liveTimers.current;
    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let refreshTimer: number | undefined;
    let attempt = 0;
    let connectedBefore = false;
    const pendingAssetIds = new Set<string>();

    function refreshAuthoritativeState() {
      void queryClient.invalidateQueries({ queryKey: queryKeys.events.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all });
    }

    function scheduleAggregateRefresh(assetId: string | null) {
      if (assetId) pendingAssetIds.add(assetId);
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer);
      refreshTimer = window.setTimeout(() => {
        void queryClient.invalidateQueries({
          queryKey: queryKeys.dashboard.all,
          refetchType: "active",
        });
        pendingAssetIds.forEach((id) => {
          void queryClient.invalidateQueries({
            queryKey: queryKeys.assets.detail(id),
            refetchType: "active",
          });
        });
        pendingAssetIds.clear();
      }, 750);
    }

    function markLive(eventId: string) {
      const existing = timers.get(eventId);
      if (existing !== undefined) window.clearTimeout(existing);
      setLiveEventIds((current) => new Set(current).add(eventId));
      const timer = window.setTimeout(() => {
        setLiveEventIds((current) => {
          const next = new Set(current);
          next.delete(eventId);
          return next;
        });
        timers.delete(eventId);
      }, 5_000);
      timers.set(eventId, timer);
    }

    function handleSecurityEvent(event: SecurityEvent) {
      setReceivedEvents((current) => {
        if (current.some((item) => item.id === event.id)) return current;
        return [event, ...current].slice(0, 100);
      });
      markLive(event.id);
      queryClient.setQueryData(queryKeys.events.detail(event.id), event);

      queryClient
        .getQueryCache()
        .findAll({ queryKey: queryKeys.events.lists })
        .forEach((query) => {
          const filters = query.queryKey[2] as EventFilters;
          if (
            canInsertLiveEvent(filters) &&
            eventMatchesFilters(event, filters)
          ) {
            queryClient.setQueryData<Page<SecurityEvent>>(
              query.queryKey,
              (current) => (current ? mergeEventPage(current, event) : current),
            );
          }
        });

      if (event.asset_id) {
        queryClient.setQueryData<Asset>(
          queryKeys.assets.detail(event.asset_id),
          (current) => {
            if (
              !current ||
              Date.parse(current.last_seen) >= Date.parse(event.timestamp)
            ) {
              return current;
            }
            return { ...current, last_seen: event.timestamp };
          },
        );
      }
      scheduleAggregateRefresh(event.asset_id);
    }

    function scheduleReconnect() {
      if (disposed) return;
      setConnectionState("reconnecting");
      const delay = reconnectDelay(attempt);
      attempt += 1;
      reconnectTimer = window.setTimeout(connect, delay);
    }

    function connect() {
      if (disposed) return;
      setConnectionState(connectedBefore ? "reconnecting" : "connecting");
      try {
        socket = new WebSocket(telemetryWebSocketUrl());
      } catch {
        setConnectionState("error");
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        const isReconnection = connectedBefore;
        connectedBefore = true;
        attempt = 0;
        setConnectionState("connected");
        if (isReconnection) refreshAuthoritativeState();
      };
      socket.onmessage = (message) => {
        if (typeof message.data !== "string") return;
        const parsed = parseTelemetryMessage(message.data);
        if (parsed?.type === "security_event") {
          handleSecurityEvent(parsed.data);
        }
      };
      socket.onerror = () => setConnectionState("error");
      socket.onclose = () => {
        socket = null;
        if (!disposed) scheduleReconnect();
      };
    }

    connect();
    return () => {
      disposed = true;
      setConnectionState("disconnected");
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      if (refreshTimer !== undefined) window.clearTimeout(refreshTimer);
      timers.forEach((timer) => window.clearTimeout(timer));
      timers.clear();
      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;
        socket.close(1000, "SENTINEL UI closed");
      }
    };
  }, [queryClient]);

  const value = useMemo(
    () => ({ connectionState, receivedEvents, liveEventIds }),
    [connectionState, receivedEvents, liveEventIds],
  );
  return (
    <TelemetryContext.Provider value={value}>
      {children}
    </TelemetryContext.Provider>
  );
}
