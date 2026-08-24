import { AlertTriangle, Database, LoaderCircle } from "lucide-react";

import { ApiError } from "../../api/client";

export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return (
    <div className="grid min-h-64 place-items-center p-8" role="status">
      <div className="text-center text-sm text-muted">
        <LoaderCircle className="mx-auto mb-3 size-5 animate-spin text-accent" />
        {label}
      </div>
    </div>
  );
}

export function ErrorState({ error }: { error: Error | null }) {
  const message =
    error instanceof ApiError
      ? error.message
      : "The requested data could not be loaded.";
  return (
    <div className="grid min-h-64 place-items-center p-8" role="alert">
      <div className="max-w-md text-center">
        <AlertTriangle className="mx-auto mb-3 size-6 text-amber-400" />
        <p className="text-sm font-medium text-slate-200">
          Unable to load data
        </p>
        <p className="mt-2 text-xs leading-5 text-muted">{message}</p>
      </div>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="grid min-h-64 place-items-center p-8">
      <div className="text-center">
        <Database className="mx-auto mb-3 size-6 text-slate-600" />
        <p className="text-sm text-slate-300">{message}</p>
        <p className="mt-1 text-xs text-muted">
          Adjust the filters or seed the demo dataset.
        </p>
      </div>
    </div>
  );
}
