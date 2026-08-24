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

export function useAssets(filters: AssetFilters) {
  return useQuery({
    queryKey: ["assets", filters],
    queryFn: () => getAssets(filters),
    placeholderData: keepPreviousData,
  });
}

export function useAsset(assetId: string | undefined) {
  return useQuery({
    queryKey: ["assets", assetId],
    queryFn: () => getAsset(assetId!),
    enabled: Boolean(assetId),
  });
}

export function useEvents(filters: EventFilters) {
  return useQuery({
    queryKey: ["events", filters],
    queryFn: () => getEvents(filters),
    placeholderData: keepPreviousData,
  });
}

export function useEvent(eventId: string | undefined) {
  return useQuery({
    queryKey: ["events", eventId],
    queryFn: () => getEvent(eventId!),
    enabled: Boolean(eventId),
  });
}

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
  });
}

export function useDashboardActivity(hours = 72) {
  return useQuery({
    queryKey: ["dashboard", "activity", hours],
    queryFn: () => getDashboardActivity(hours),
  });
}
