import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getAlert,
  getAlerts,
  getAsset,
  getAssets,
  getDashboardActivity,
  getDashboardSummary,
  getEvent,
  getEvents,
  getLabStatus,
  getNetworkTopology,
  getScenario,
  getScenarioRun,
  getScenarioRuns,
  getScenarios,
  getSimulatorStatus,
  getRule,
  getRules,
  updateAlert,
  updateRule,
  cancelScenarioRun,
  runScenario,
} from "../api/client";
import type {
  AlertFilters,
  AlertStatus,
  AssetFilters,
  DetectionRuleFilters,
  EventFilters,
  TopologyParameters,
} from "../types/core";

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
  alerts: {
    all: ["alerts"] as const,
    lists: ["alerts", "list"] as const,
    list: (filters: AlertFilters) => ["alerts", "list", filters] as const,
    detail: (alertId: string) => ["alerts", "detail", alertId] as const,
  },
  rules: {
    all: ["rules"] as const,
    lists: ["rules", "list"] as const,
    list: (filters: DetectionRuleFilters) =>
      ["rules", "list", filters] as const,
    detail: (ruleId: string) => ["rules", "detail", ruleId] as const,
  },
  dashboard: {
    all: ["dashboard"] as const,
    summary: ["dashboard", "summary"] as const,
    activity: (hours: number) => ["dashboard", "activity", hours] as const,
  },
  lab: {
    status: ["lab", "status"] as const,
  },
  simulator: {
    all: ["simulator"] as const,
    status: ["simulator", "status"] as const,
    scenarios: ["simulator", "scenarios"] as const,
    scenario: (scenarioId: string) =>
      ["simulator", "scenarios", scenarioId] as const,
    runs: ["simulator", "runs"] as const,
    run: (runId: string) => ["simulator", "runs", runId] as const,
  },
  network: {
    all: ["network"] as const,
    topology: (parameters: TopologyParameters) =>
      ["network", "topology", parameters] as const,
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

export function useAlerts(filters: AlertFilters) {
  return useQuery({
    queryKey: queryKeys.alerts.list(filters),
    queryFn: () => getAlerts(filters),
    placeholderData: keepPreviousData,
  });
}

export function useAlert(alertId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.alerts.detail(alertId ?? ""),
    queryFn: () => getAlert(alertId!),
    enabled: Boolean(alertId),
  });
}

export function useUpdateAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      alertId,
      status,
    }: {
      alertId: string;
      status: AlertStatus;
    }) => updateAlert(alertId, status),
    onSuccess: (alert) => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.alerts.detail(alert.id),
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.alerts.lists });
      void queryClient.invalidateQueries({ queryKey: queryKeys.assets.all });
      void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.all });
    },
  });
}

export function useRules(filters: DetectionRuleFilters) {
  return useQuery({
    queryKey: queryKeys.rules.list(filters),
    queryFn: () => getRules(filters),
    placeholderData: keepPreviousData,
  });
}

export function useRule(ruleId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.rules.detail(ruleId ?? ""),
    queryFn: () => getRule(ruleId!),
    enabled: Boolean(ruleId),
  });
}

export function useUpdateRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ ruleId, enabled }: { ruleId: string; enabled: boolean }) =>
      updateRule(ruleId, enabled),
    onSuccess: (rule) => {
      queryClient.setQueryData(queryKeys.rules.detail(rule.id), rule);
      void queryClient.invalidateQueries({ queryKey: queryKeys.rules.lists });
    },
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

export function useLabStatus() {
  return useQuery({
    queryKey: queryKeys.lab.status,
    queryFn: getLabStatus,
    refetchInterval: 15_000,
  });
}

export function useNetworkTopology(parameters: TopologyParameters) {
  return useQuery({
    queryKey: queryKeys.network.topology(parameters),
    queryFn: () => getNetworkTopology(parameters),
  });
}

export function useSimulatorStatus() {
  return useQuery({
    queryKey: queryKeys.simulator.status,
    queryFn: getSimulatorStatus,
    refetchInterval: 5_000,
  });
}

export function useScenarios() {
  return useQuery({
    queryKey: queryKeys.simulator.scenarios,
    queryFn: getScenarios,
  });
}

export function useScenario(scenarioId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.simulator.scenario(scenarioId ?? ""),
    queryFn: () => getScenario(scenarioId!),
    enabled: Boolean(scenarioId),
  });
}

export function useScenarioRuns(page = 1) {
  return useQuery({
    queryKey: [...queryKeys.simulator.runs, page],
    queryFn: () => getScenarioRuns(page),
    refetchInterval: 5_000,
  });
}

export function useScenarioRun(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.simulator.run(runId ?? ""),
    queryFn: () => getScenarioRun(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) =>
      ["pending", "running"].includes(query.state.data?.status ?? "")
        ? 2_000
        : false,
  });
}

export function useRunScenario() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: runScenario,
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.simulator.run(run.id), run);
      void queryClient.invalidateQueries({ queryKey: queryKeys.simulator.all });
    },
  });
}

export function useCancelScenarioRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: cancelScenarioRun,
    onSuccess: (run) => {
      queryClient.setQueryData(queryKeys.simulator.run(run.id), run);
      void queryClient.invalidateQueries({ queryKey: queryKeys.simulator.all });
    },
  });
}
