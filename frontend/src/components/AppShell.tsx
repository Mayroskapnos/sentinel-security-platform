import {
  Activity,
  BellRing,
  Boxes,
  CircleDotDashed,
  Crosshair,
  Gauge,
  Network,
  ScrollText,
  Settings,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { useHealth } from "../hooks/useHealth";
import { useTelemetry } from "../realtime/TelemetryContext";
import { BrandMark } from "./BrandMark";
import { HealthBadge } from "./HealthBadge";
import { TelemetryBadge } from "./TelemetryBadge";

interface NavigationItem {
  label: string;
  icon: LucideIcon;
  to: string;
}

const primaryNavigation: NavigationItem[] = [
  { label: "Overview", icon: Gauge, to: "/" },
  { label: "Assets", icon: Boxes, to: "/assets" },
  { label: "Events", icon: Activity, to: "/events" },
  { label: "Alerts", icon: BellRing, to: "/alerts" },
  { label: "Incidents", icon: ShieldCheck, to: "/incidents" },
  { label: "Attack Map", icon: Network, to: "/attack-map" },
  { label: "Detection Rules", icon: ScrollText, to: "/rules" },
  { label: "Attack Simulator", icon: Crosshair, to: "/simulator" },
];

function Navigation({ compact = false }: { compact?: boolean }) {
  const baseClass = `group flex shrink-0 items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-colors`;

  return (
    <nav
      aria-label="Primary navigation"
      className={
        compact
          ? "flex gap-1 overflow-x-auto px-4 pb-3"
          : "flex flex-1 flex-col gap-1 px-3"
      }
    >
      {primaryNavigation.map(({ icon: Icon, label, to }) => (
        <NavLink
          className={({ isActive }) =>
            `${baseClass} ${
              isActive
                ? "border-accent/20 bg-accent/10 font-medium text-accent"
                : "border-transparent text-muted hover:bg-white/[0.035] hover:text-slate-200"
            }`
          }
          end={to === "/"}
          key={label}
          to={to}
        >
          <Icon className="size-[18px]" strokeWidth={1.8} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const health = useHealth();
  const telemetry = useTelemetry();
  const isHealthy = health.data?.status === "healthy" && !health.isError;

  return (
    <div className="min-h-screen bg-canvas text-slate-100">
      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-line bg-[#0c121b] lg:flex">
        <div className="flex h-[74px] items-center gap-3 border-b border-line px-5">
          <BrandMark />
          <div>
            <p className="text-sm font-semibold tracking-[0.2em] text-white">
              SENTINEL
            </p>
            <p className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-muted">
              Security operations
            </p>
          </div>
        </div>

        <div className="px-6 pb-2 pt-6 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">
          Workspace
        </div>
        <Navigation />

        <div className="border-t border-line p-3">
          <NavLink
            className={({ isActive }) =>
              `flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition-colors ${
                isActive
                  ? "border-accent/20 bg-accent/10 font-medium text-accent"
                  : "border-transparent text-muted hover:bg-white/[0.035] hover:text-slate-200"
              }`
            }
            to="/system"
          >
            <Settings className="size-[18px]" strokeWidth={1.8} />
            System
          </NavLink>
          <div className="mt-2 flex items-center gap-3 rounded-lg border border-line bg-black/10 p-3">
            <CircleDotDashed className="size-5 text-accent" />
            <div>
              <p className="text-xs font-medium text-slate-300">
                Control plane
              </p>
              <p className="text-[11px] text-muted">
                v{health.data?.version ?? "unknown"}
              </p>
            </div>
          </div>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-[74px] items-center justify-between border-b border-line bg-canvas/90 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 lg:hidden">
            <BrandMark />
            <span className="text-sm font-semibold tracking-[0.18em]">
              SENTINEL
            </span>
          </div>
          <div className="hidden lg:block">
            <p className="text-xs uppercase tracking-[0.18em] text-muted">
              Security Monitoring &amp; Attack Detection Platform
            </p>
          </div>
          <div className="flex items-center gap-2">
            <TelemetryBadge state={telemetry.connectionState} />
            <HealthBadge isHealthy={isHealthy} isLoading={health.isLoading} />
          </div>
        </header>

        <div className="border-b border-line bg-[#0c121b] pt-3 lg:hidden">
          <Navigation compact />
        </div>

        <main className="px-4 py-6 sm:px-6 sm:py-8 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
