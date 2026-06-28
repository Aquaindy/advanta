import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { SourceCard } from "@/features/traffic/TrafficBits";
import { getTrafficCatalog, listTrafficCampaigns } from "@/lib/traffic";
import { cn } from "@/lib/utils";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { TrafficRecipe } from "@/types/api";

export function TrafficGeniePage() {
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const navigate = useNavigate();
  const [category, setCategory] = useState<string>("all");

  const catalog = useQuery({
    queryKey: ["traffic", "catalog", workspaceId],
    queryFn: () => getTrafficCatalog(workspaceId!),
    enabled: !!workspaceId,
  });

  const campaigns = useQuery({
    queryKey: ["traffic", "campaigns", workspaceId],
    queryFn: () => listTrafficCampaigns(workspaceId!),
    enabled: !!workspaceId,
  });

  const sources = useMemo(() => {
    const all = catalog.data?.sources ?? [];
    return category === "all" ? all : all.filter((s) => s.category === category);
  }, [catalog.data, category]);

  const planCampaign = (slug: string) => navigate(`/traffic/campaigns?source=${slug}`);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-grape-700">Traffic Genie</p>
          <h1 className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">Choose where your traffic comes from</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-500">
            Create the campaign. Choose the traffic. Capture the lead. Nurture the buyer. Optimize with AI.
            Plan paid, organic, paid-email and growth-loop sources — then generate assets, tracking links,
            and Omnisend follow-ups.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/traffic/utm-builder"><Button variant="secondary">UTM builder</Button></Link>
          <Link to="/traffic/recommendation"><Button>Recommend my path</Button></Link>
        </div>
      </header>

      <Card className="border-grape-200 bg-grape-gradient text-white">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold">Not sure where to start?</h3>
            <p className="mt-1 text-sm text-white/80">
              Answer a few questions and get a primary + secondary channel, organic support, retargeting,
              and a 7-day launch plan.
            </p>
          </div>
          <Link to="/traffic/recommendation">
            <Button variant="secondary">Get AI recommendation →</Button>
          </Link>
        </div>
      </Card>

      {/* Recipes */}
      {catalog.data?.recipes && catalog.data.recipes.length > 0 ? (
        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold text-ink">Traffic recipes</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {catalog.data.recipes.map((r) => (
              <RecipeCard key={r.slug} recipe={r} />
            ))}
          </div>
        </section>
      ) : null}

      {/* Active campaigns summary */}
      {campaigns.data && campaigns.data.length > 0 ? (
        <Card>
          <CardHeader
            title="Your traffic campaigns"
            subtitle={`${campaigns.data.length} campaign${campaigns.data.length === 1 ? "" : "s"}`}
            action={<Link to="/traffic/campaigns" className="text-sm font-medium text-grape-700 hover:text-grape-800">View all →</Link>}
          />
          <ul className="mt-3 flex flex-col divide-y divide-slate-100">
            {campaigns.data.slice(0, 4).map((c) => (
              <li key={c.id}>
                <Link to={`/traffic/campaigns/${c.id}`} className="flex items-center justify-between gap-3 py-2.5 text-sm hover:text-grape-700">
                  <span className="font-medium text-ink">{c.name}</span>
                  <span className="text-xs text-slate-400">{c.source_slug} · {c.status}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {/* Source catalog */}
      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-ink">Traffic sources</h2>
        </div>

        <div className="flex flex-wrap gap-1.5">
          <CategoryChip label="All" active={category === "all"} onClick={() => setCategory("all")} />
          {catalog.data?.categories.map((c) => (
            <CategoryChip key={c.slug} label={c.name} active={category === c.slug} onClick={() => setCategory(c.slug)} />
          ))}
        </div>

        {catalog.isLoading ? (
          <p className="text-sm text-slate-400">Loading sources…</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sources.map((s) => (
              <SourceCard key={s.slug} source={s} onPlan={planCampaign} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function RecipeCard({ recipe }: { recipe: TrafficRecipe }) {
  return (
    <div className="card flex flex-col gap-2 p-4">
      <div className="text-sm font-semibold text-ink">{recipe.name}</div>
      <p className="line-clamp-3 text-xs text-slate-500">{recipe.goal}</p>
      <div className="mt-auto flex flex-wrap gap-1 pt-2">
        {recipe.sources.slice(0, 3).map((s) => (
          <span key={s} className="pill bg-slate-100 text-[10px] text-slate-600">{s.replace(/_/g, " ")}</span>
        ))}
        {recipe.sources.length > 3 ? (
          <span className="pill bg-slate-100 text-[10px] text-slate-500">+{recipe.sources.length - 3}</span>
        ) : null}
      </div>
    </div>
  );
}

function CategoryChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full px-3 py-1.5 text-xs font-medium transition",
        active ? "bg-grape text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200",
      )}
    >
      {label}
    </button>
  );
}
