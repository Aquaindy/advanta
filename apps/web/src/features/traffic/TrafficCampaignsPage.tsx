import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { statusLabel } from "@/features/traffic/TrafficBits";
import { ApiError } from "@/lib/api-client";
import { createTrafficCampaign, getTrafficCatalog, listTrafficCampaigns } from "@/lib/traffic";
import { cn } from "@/lib/utils";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { TrafficCampaign } from "@/types/api";

export function TrafficCampaignsPage() {
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const prefillSource = params.get("source");

  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    if (prefillSource) setShowNew(true);
  }, [prefillSource]);

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

  const sourceName = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of catalog.data?.sources ?? []) map.set(s.slug, s.name);
    return map;
  }, [catalog.data]);

  const closeNew = () => {
    setShowNew(false);
    if (prefillSource) {
      params.delete("source");
      setParams(params, { replace: true });
    }
  };

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-grape-700">Traffic Genie</p>
          <h1 className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">Traffic campaigns</h1>
          <p className="mt-2 text-sm text-slate-500">
            Plan a campaign for any traffic source, generate its assets with AI, and build tracking links.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/traffic"><Button variant="secondary">Browse sources</Button></Link>
          <Button onClick={() => (showNew ? closeNew() : setShowNew(true))}>
            {showNew ? "Close" : "New campaign"}
          </Button>
        </div>
      </header>

      {showNew && workspaceId ? (
        <NewCampaignForm
          workspaceId={workspaceId}
          defaultSource={prefillSource}
          sources={catalog.data?.sources ?? []}
          onCancel={closeNew}
          onCreated={(id) => {
            queryClient.invalidateQueries({ queryKey: ["traffic", "campaigns", workspaceId] });
            navigate(`/traffic/campaigns/${id}`);
          }}
        />
      ) : null}

      {campaigns.isLoading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : campaigns.data && campaigns.data.length > 0 ? (
        <ul className="flex flex-col divide-y divide-slate-100 overflow-hidden rounded-2xl border border-slate-100 bg-surface shadow-card">
          {campaigns.data.map((c) => (
            <CampaignRow key={c.id} campaign={c} sourceName={sourceName.get(c.source_slug) ?? c.source_slug} />
          ))}
        </ul>
      ) : (
        <EmptyState
          title="No traffic campaigns yet"
          description="Pick a traffic source and plan your first campaign — then generate ad copy, scripts, email swipes or SEO content with AI."
          action={<Button onClick={() => setShowNew(true)}>New campaign</Button>}
        />
      )}
    </div>
  );
}

function CampaignRow({ campaign, sourceName }: { campaign: TrafficCampaign; sourceName: string }) {
  const s = statusLabel(campaign.status === "draft" ? "manual" : "active");
  return (
    <li>
      <Link
        to={`/traffic/campaigns/${campaign.id}`}
        className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 transition hover:bg-grape-50"
      >
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-semibold text-ink">{campaign.name}</div>
          <div className="mt-0.5 text-xs text-slate-500">
            {sourceName}
            {campaign.goal ? ` · ${campaign.goal}` : ""}
            {campaign.offer_name ? ` · ${campaign.offer_name}` : ""}
          </div>
        </div>
        <span className={cn("pill", s.cls)}>{campaign.status}</span>
      </Link>
    </li>
  );
}

function NewCampaignForm({
  workspaceId,
  defaultSource,
  sources,
  onCancel,
  onCreated,
}: {
  workspaceId: string;
  defaultSource: string | null;
  sources: { slug: string; name: string; category: string }[];
  onCancel: () => void;
  onCreated: (id: string) => void;
}) {
  const [sourceSlug, setSourceSlug] = useState(defaultSource ?? sources[0]?.slug ?? "");
  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [offerName, setOfferName] = useState("");
  const [offerUrl, setOfferUrl] = useState("");
  const [audience, setAudience] = useState("");
  const [budget, setBudget] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (defaultSource) setSourceSlug(defaultSource);
  }, [defaultSource]);

  const create = useMutation({
    mutationFn: () =>
      createTrafficCampaign(workspaceId, {
        source_slug: sourceSlug,
        name: name.trim(),
        goal: goal || null,
        offer_name: offerName || null,
        offer_url: offerUrl || null,
        audience: audience || null,
        budget_cents: budget ? Math.round(Number(budget) * 100) : null,
        currency: budget ? "USD" : null,
      }),
    onSuccess: (c) => onCreated(c.id),
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not create the campaign."),
  });

  return (
    <Card>
      <CardHeader title="New traffic campaign" subtitle="Source-agnostic — works in manual mode before any API publishing." />
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-500">Traffic source</span>
          <select
            value={sourceSlug}
            onChange={(e) => setSourceSlug(e.target.value)}
            className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none transition focus:border-grape focus:ring-2 focus:ring-grape-200"
          >
            {sources.map((s) => (
              <option key={s.slug} value={s.slug}>{s.name}</option>
            ))}
          </select>
        </label>
        <Input label="Campaign name" value={name} onChange={setName} placeholder="Black Friday lead push" required />
        <Input label="Goal" value={goal} onChange={setGoal} placeholder="Generate leads" />
        <Input label="Offer name" value={offerName} onChange={setOfferName} placeholder="Free SEO checklist" />
        <Input label="Offer URL" value={offerUrl} onChange={setOfferUrl} placeholder="https://…" />
        <Input label="Audience" value={audience} onChange={setAudience} placeholder="Marketing teams" />
        <Input label="Budget (USD)" value={budget} onChange={setBudget} placeholder="2000" type="number" />
      </div>
      {error ? <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div> : null}
      <div className="mt-5 flex items-center gap-2">
        <Button onClick={() => create.mutate()} disabled={create.isPending || !name.trim() || !sourceSlug}>
          {create.isPending ? "Creating…" : "Create campaign"}
        </Button>
        <Button variant="ghost" onClick={onCancel}>Cancel</Button>
      </div>
    </Card>
  );
}

function Input({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}{required ? " *" : ""}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none transition focus:border-grape focus:ring-2 focus:ring-grape-200"
      />
    </label>
  );
}
