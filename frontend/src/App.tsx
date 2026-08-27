import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { AppErrorBoundary } from "./components/AppErrorBoundary";
import { AppShell } from "./components/AppShell";
import { LoadingState } from "./components/data/QueryState";

const OverviewPage = lazy(() =>
  import("./pages/OverviewPage").then((module) => ({
    default: module.OverviewPage,
  })),
);
const AssetsPage = lazy(() =>
  import("./pages/AssetsPage").then((module) => ({
    default: module.AssetsPage,
  })),
);
const AssetDetailPage = lazy(() =>
  import("./pages/AssetDetailPage").then((module) => ({
    default: module.AssetDetailPage,
  })),
);
const EventsPage = lazy(() =>
  import("./pages/EventsPage").then((module) => ({
    default: module.EventsPage,
  })),
);
const AlertsPage = lazy(() =>
  import("./pages/AlertsPage").then((module) => ({
    default: module.AlertsPage,
  })),
);
const AlertDetailPage = lazy(() =>
  import("./pages/AlertDetailPage").then((module) => ({
    default: module.AlertDetailPage,
  })),
);
const IncidentsPage = lazy(() =>
  import("./pages/IncidentsPage").then((module) => ({
    default: module.IncidentsPage,
  })),
);
const IncidentDetailPage = lazy(() =>
  import("./pages/IncidentDetailPage").then((module) => ({
    default: module.IncidentDetailPage,
  })),
);
const RulesPage = lazy(() =>
  import("./pages/RulesPage").then((module) => ({ default: module.RulesPage })),
);
const RuleDetailPage = lazy(() =>
  import("./pages/RuleDetailPage").then((module) => ({
    default: module.RuleDetailPage,
  })),
);
const SystemPage = lazy(() =>
  import("./pages/SystemPage").then((module) => ({
    default: module.SystemPage,
  })),
);
const SimulatorPage = lazy(() =>
  import("./pages/SimulatorPage").then((module) => ({
    default: module.SimulatorPage,
  })),
);
const ScenarioRunPage = lazy(() =>
  import("./pages/ScenarioRunPage").then((module) => ({
    default: module.ScenarioRunPage,
  })),
);
const AttackMapPage = lazy(() =>
  import("./pages/AttackMapPage").then((module) => ({
    default: module.AttackMapPage,
  })),
);
const NotFoundPage = lazy(() =>
  import("./pages/NotFoundPage").then((module) => ({
    default: module.NotFoundPage,
  })),
);

export default function App() {
  return (
    <AppErrorBoundary>
      <AppShell>
        <Suspense fallback={<LoadingState label="Loading workspace" />}>
          <Routes>
            <Route element={<OverviewPage />} path="/" />
            <Route element={<AssetsPage />} path="/assets" />
            <Route element={<AssetDetailPage />} path="/assets/:assetId" />
            <Route element={<EventsPage />} path="/events" />
            <Route element={<AlertsPage />} path="/alerts" />
            <Route element={<AlertDetailPage />} path="/alerts/:alertId" />
            <Route element={<IncidentsPage />} path="/incidents" />
            <Route
              element={<IncidentDetailPage />}
              path="/incidents/:incidentId"
            />
            <Route element={<RulesPage />} path="/rules" />
            <Route element={<RuleDetailPage />} path="/rules/:ruleId" />
            <Route element={<SystemPage />} path="/system" />
            <Route element={<SimulatorPage />} path="/simulator" />
            <Route
              element={<ScenarioRunPage />}
              path="/simulator/runs/:runId"
            />
            <Route element={<AttackMapPage />} path="/attack-map" />
            <Route element={<NotFoundPage />} path="*" />
          </Routes>
        </Suspense>
      </AppShell>
    </AppErrorBoundary>
  );
}
