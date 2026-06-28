import { cn } from "@/lib/utils";
import type { TrafficSource } from "@/types/api";

export const SOURCE_TYPE_LABEL: Record<string, string> = {
  paid: "Paid",
  paid_email: "Paid email",
  organic: "Organic",
  other: "Other",
};

export function statusLabel(status: string): { label: string; cls: string } {
  switch (status) {
    case "active":
      return { label: "Active", cls: "pill-success" };
    case "manual":
      return { label: "Manual mode", cls: "pill-grape" };
    case "coming_soon":
      return { label: "Coming soon", cls: "bg-slate-100 text-slate-600" };
    default:
      return { label: status, cls: "bg-slate-100 text-slate-600" };
  }
}

function levelTone(value: string): string {
  switch (value) {
    case "Fast":
    case "Free":
    case "Easy":
      return "pill-success";
    case "Slow":
    case "High":
    case "Hard":
      return "pill-warning";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

export function MetaPills({ source }: { source: TrafficSource }) {
  return (
    <div className="flex flex-wrap gap-1.5 text-[11px]">
      <span className={cn("pill", levelTone(source.speed))}>{source.speed}</span>
      <span className={cn("pill", levelTone(source.cost))}>{source.cost} cost</span>
      <span className={cn("pill", levelTone(source.difficulty))}>{source.difficulty}</span>
    </div>
  );
}

export function formatBudget(cents: number | null, currency: string | null): string {
  if (cents === null || cents === undefined) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency ?? "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

/** Compact source card used on the Traffic Genie home + recommendation. */
export function SourceCard({
  source,
  onPlan,
}: {
  source: TrafficSource;
  onPlan?: (slug: string) => void;
}) {
  const s = statusLabel(source.status);
  return (
    <div className="card flex flex-col gap-3 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-ink">{source.name}</div>
          <div className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-400">
            {SOURCE_TYPE_LABEL[source.source_type] ?? source.source_type}
          </div>
        </div>
        <span className={cn("pill shrink-0", s.cls)}>{s.label}</span>
      </div>
      <p className="line-clamp-2 text-xs text-slate-500">{source.best_for.join(" · ")}</p>
      <MetaPills source={source} />
      {onPlan ? (
        <button
          type="button"
          onClick={() => onPlan(source.slug)}
          className="mt-1 self-start text-sm font-medium text-grape-700 hover:text-grape-800"
        >
          Plan campaign →
        </button>
      ) : null}
    </div>
  );
}
