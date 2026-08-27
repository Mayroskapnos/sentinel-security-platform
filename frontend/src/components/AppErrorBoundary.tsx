import { AlertTriangle, RotateCcw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  failed: boolean;
}

export class AppErrorBoundary extends Component<
  { children: ReactNode },
  State
> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error("SENTINEL UI render failure", error, info);
    }
  }

  render() {
    if (!this.state.failed) return this.props.children;

    return (
      <main className="grid min-h-screen place-items-center bg-canvas p-6 text-slate-100">
        <section className="w-full max-w-lg rounded-xl border border-line bg-panel p-8 text-center shadow-panel">
          <AlertTriangle className="mx-auto size-8 text-amber-300" />
          <h1 className="mt-4 text-xl font-semibold">Workspace unavailable</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            SENTINEL could not render this view. Reload the workspace; if the
            problem persists, inspect the API and browser logs.
          </p>
          <button
            className="mt-6 inline-flex items-center gap-2 rounded-md border border-accent/30 bg-accent/10 px-4 py-2 text-xs font-semibold text-accent hover:bg-accent/15"
            onClick={() => window.location.reload()}
            type="button"
          >
            <RotateCcw className="size-3.5" /> Reload workspace
          </button>
        </section>
      </main>
    );
  }
}
