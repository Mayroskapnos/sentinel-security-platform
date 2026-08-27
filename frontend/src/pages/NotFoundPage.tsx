import { ArrowLeft, SearchX } from "lucide-react";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="mx-auto max-w-xl rounded-xl border border-line bg-panel p-8 text-center shadow-panel sm:p-12">
      <SearchX className="mx-auto size-9 text-accent" />
      <p className="mt-5 font-mono text-xs text-accent">
        404 · ROUTE NOT FOUND
      </p>
      <h1 className="mt-2 text-2xl font-semibold text-white">
        This workspace view does not exist
      </h1>
      <p className="mt-3 text-sm leading-6 text-muted">
        The URL may be outdated or incomplete. No monitoring data was changed.
      </p>
      <Link
        className="mt-6 inline-flex items-center gap-2 rounded-md border border-accent/30 bg-accent/10 px-4 py-2 text-xs font-semibold text-accent hover:bg-accent/15"
        to="/"
      >
        <ArrowLeft className="size-3.5" /> Return to overview
      </Link>
    </section>
  );
}
