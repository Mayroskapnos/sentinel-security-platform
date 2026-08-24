import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({
  onPageChange,
  page,
  pages,
  total,
}: PaginationProps) {
  return (
    <div className="flex flex-col gap-3 border-t border-line px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-xs text-muted">
        {total.toLocaleString()} result{total === 1 ? "" : "s"}
      </p>
      <div className="flex items-center gap-2">
        <button
          aria-label="Previous page"
          className="grid size-8 place-items-center rounded-md border border-line text-muted transition-colors hover:bg-white/[0.04] hover:text-white disabled:opacity-30"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          type="button"
        >
          <ChevronLeft className="size-4" />
        </button>
        <span className="min-w-24 text-center font-mono text-xs text-slate-400">
          Page {page} of {Math.max(pages, 1)}
        </span>
        <button
          aria-label="Next page"
          className="grid size-8 place-items-center rounded-md border border-line text-muted transition-colors hover:bg-white/[0.04] hover:text-white disabled:opacity-30"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          type="button"
        >
          <ChevronRight className="size-4" />
        </button>
      </div>
    </div>
  );
}
