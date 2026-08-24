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

export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<LoadingState label="Loading workspace" />}>
        <Routes>
          <Route element={<OverviewPage />} path="/" />
          <Route element={<AssetsPage />} path="/assets" />
          <Route element={<AssetDetailPage />} path="/assets/:assetId" />
          <Route element={<EventsPage />} path="/events" />
          <Route element={<Navigate replace to="/" />} path="*" />
        </Routes>
      </Suspense>
    </AppShell>
  );
}
