import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  getAsset,
  getAssets,
  getDashboardActivity,
  getDashboardSummary,
  getEvent,
  getEvents,
} from "../api/client";
import type { AssetFilters, EventFilters } from "../types/core";

export const queryKeys = {
  assets: {
    all: ["assets"] as const,
    lists: ["assets", "list"] as const,
    list: (filters: AssetFilters) => ["assets", "list", filters] as const,
    detail: (assetId: string) => ["assets", "detail", assetId] as const,
  },
  events: {
    all: ["events"] as const,
    lists: ["events", "list"] as const,
    list: (filters: EventFilters) => ["events", "list", filters] as const,
    detail: (eventId: string) => ["events", "detail", eventId] as const,
  },
  dashboard: {
    all: ["dashboard"] as const,
    summary: ["dashboard", "summary"] as const,
    activity: (hours: number) => ["dashboard", "activity", hours] as const,
  },
};

export function useAssets(filters: AssetFilters) {
  return useQuery({
    queryKey: queryKeys.assets.list(filters),
    queryFn: () => getAssets(filters),
    placeholderData: keepPreviousData,
  });
}

export function useAsset(assetId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.assets.detail(assetId ?? ""),
    queryFn: () => getAsset(assetId!),
    enabled: Boolean(assetId),
  });
}

export function useEvents(filters: EventFilters) {
  return useQuery({
    queryKey: queryKeys.events.list(filters),
    queryFn: () => getEvents(filters),
    placeholderData: keepPreviousData,
  });
}

export function useEvent(eventId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.events.detail(eventId ?? ""),
    queryFn: () => getEvent(eventId!),
    enabled: Boolean(eventId),
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: queryKeys.dashboard.summary,
    queryFn: getDashboardSummary,
  });
}

export function useDashboardActivity(hours = 72) {
  return useQuery({
    queryKey: queryKeys.dashboard.activity(hours),
    queryFn: () => getDashboardActivity(hours),
  });
}
