import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

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
const RulesPage = lazy(() =>
  import("./pages/RulesPage").then((module) => ({ default: module.RulesPage })),
);
const RuleDetailPage = lazy(() =>
  import("./pages/RuleDetailPage").then((module) => ({
    default: module.RuleDetailPage,
  })),
);

export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<LoadingState label="Loading workspace" />}>
        <Routes>
          <Route element={<OverviewPage />} path="/" />
          <Route element={<AssetsPage />} path="/assets" />
          <Route element={<AssetDetailPage />} path="/assets/:assetId" />
          <Route element={<EventsPage />} path="/events" />
          <Route element={<AlertsPage />} path="/alerts" />
          <Route element={<AlertDetailPage />} path="/alerts/:alertId" />
          <Route element={<RulesPage />} path="/rules" />
          <Route element={<RuleDetailPage />} path="/rules/:ruleId" />
          <Route element={<Navigate replace to="/" />} path="*" />
        </Routes>
      </Suspense>
    </AppShell>
  );
}
