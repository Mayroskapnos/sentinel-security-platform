import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { OverviewPage } from "./pages/OverviewPage";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route element={<OverviewPage />} path="/" />
        <Route element={<Navigate replace to="/" />} path="*" />
      </Routes>
    </AppShell>
  );
}
