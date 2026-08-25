import { useQueryClient } from "@tanstack/react-query";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";

import { queryKeys } from "../hooks/useCoreData";
import type {
  Alert,
  AlertFilters,
  Asset,
  EventFilters,
  Page,
  SecurityEvent,
} from "../types/core";
import { TelemetryContext } from "./TelemetryContext";
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
  removeAlertFromPage,
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
  const [receivedAlerts, setReceivedAlerts] = useState<readonly Alert[]>([]);
  const [liveAlertIds, setLiveAlertIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const liveTimers = useRef(new Map<string, number>());
  const liveAlertTimers = useRef(new Map<string, number>());

  useEffect(() => {
    const timers = liveTimers.current;
    const alertTimers = liveAlertTimers.current;
    let disposed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;
    let refreshTimer: number | undefined;
    let attempt = 0;
    let connectedBefore = false;
    const pendingAssetIds = new Set<string>();

    function refreshAuthoritativeState() {
      authoritativeRefreshQueryKeys().forEach((queryKey) => {
        void queryClient.invalidateQueries({ queryKey });
      });
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

    function markAlertLive(alertId: string) {
      const existing = alertTimers.get(alertId);
      if (existing !== undefined) window.clearTimeout(existing);
      setLiveAlertIds((current) => new Set(current).add(alertId));
      const timer = window.setTimeout(() => {
        setLiveAlertIds((current) => {
          const next = new Set(current);
          next.delete(alertId);
          return next;
        });
        alertTimers.delete(alertId);
      }, 5_000);
      alertTimers.set(alertId, timer);
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

    function handleAlert(alert: Alert) {
      setReceivedAlerts((current) =>
        [alert, ...current.filter((item) => item.id !== alert.id)].slice(
          0,
          100,
        ),
      );
      markAlertLive(alert.id);
      void queryClient.invalidateQueries({
        queryKey: queryKeys.alerts.detail(alert.id),
        refetchType: "active",
      });

      queryClient
        .getQueryCache()
        .findAll({ queryKey: queryKeys.alerts.lists })
        .forEach((query) => {
          const filters = query.queryKey[2] as AlertFilters;
          queryClient.setQueryData<Page<Alert>>(query.queryKey, (current) => {
            if (!current) return current;
            const isPresent = current.items.some(
              (item) => item.id === alert.id,
            );
            if (!alertMatchesFilters(alert, filters)) {
              return removeAlertFromPage(current, alert.id);
            }
            if (isPresent || canInsertLiveAlert(filters)) {
              return mergeAlertPage(current, alert);
            }
            return current;
          });
        });
      scheduleAggregateRefresh(alert.asset_id);
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
        const refreshAfterConnect =
          shouldRefreshAuthoritativeState(connectedBefore);
        connectedBefore = true;
        attempt = 0;
        setConnectionState("connected");
        if (refreshAfterConnect) refreshAuthoritativeState();
      };
      socket.onmessage = (message) => {
        if (typeof message.data !== "string") return;
        const parsed = parseTelemetryMessage(message.data);
        if (parsed?.type === "security_event") {
          handleSecurityEvent(parsed.data);
        } else if (
          parsed?.type === "alert_created" ||
          parsed?.type === "alert_updated"
        ) {
          handleAlert(parsed.data);
        } else if (parsed?.type.startsWith("simulation_")) {
          void queryClient.invalidateQueries({
            queryKey: queryKeys.simulator.all,
          });
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
      alertTimers.forEach((timer) => window.clearTimeout(timer));
      alertTimers.clear();
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
    () => ({
      connectionState,
      receivedEvents,
      liveEventIds,
      receivedAlerts,
      liveAlertIds,
    }),
    [
      connectionState,
      receivedEvents,
      liveEventIds,
      receivedAlerts,
      liveAlertIds,
    ],
  );
  return (
    <TelemetryContext.Provider value={value}>
      {children}
    </TelemetryContext.Provider>
  );
}
