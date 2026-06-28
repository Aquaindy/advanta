import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { UsageMeter } from "@/components/UsageMeter";
import { SourceCard } from "@/features/traffic/TrafficBits";
import { ApiError } from "@/lib/api-client";
import { recommendTraffic } from "@/lib/traffic";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { TrafficRecommendation, TrafficSource } from "@/types/api";

type FormState = {
  business_type: string;
  product: string;
  audience: string;
  goal: string;
  monthly_budget: string;
  business_model: string;
  preference: string;
  speed: string;
};

const EMPTY: FormState = {
  business_type: "",
  product: "",
  audience: "",
  goal: "",
  monthly_budget: "",
  business_model: "b2b",
  preference: "hybrid",
  speed: "fast",
};

export function TrafficRecommendationPage() {
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [plan, setPlan] = useState<TrafficRecommendation | null>(null);

  const mutate = useMutation({
    mutationFn: () =>
      recommendTraffic(workspaceId!, {
        business_type: form.business_type || undefined,
        product: form.product || undefined,
        audience: form.audience || undefined,
        goal: form.goal || undefined,
        monthly_budget: form.monthly_budget ? Number(form.monthly_budget) : undefined,
        business_model: form.business_model || undefined,
        preference: form.preference || undefined,
        speed: form.speed || undefined,
      }),
    onSuccess: (data) => {
      setPlan(data);
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not generate a recommendation."),
  });

  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const planCampaign = (slug: string) => navigate(`/traffic/campaigns?source=${slug}`);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header>
        <p className="text-xs uppercase tracking-wider text-grape-700">Traffic Genie</p>
        <h1 className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">Traffic recommendation</h1>
        <p className="mt-2 text-sm text-slate-500">
          Tell us about your offer and budget — the AI recommends a growth path: primary + secondary
          channels, organic support, retargeting, an Omnisend follow-up, and 7-day + 30-day plans.
        </p>
      </header>

      <UsageMeter resource="agent_runs" />

      <Card>
        <CardHeader title="Your offer" subtitle="Everything is optional, but more detail = a sharper recommendation." />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="Business type" value={form.business_type} onChange={set("business_type")} placeholder="B2B SaaS, ecommerce, coach…" />
          <Field label="Product / offer" value={form.product} onChange={set("product")} placeholder="AI analytics tool" />
          <Field label="Audience" value={form.audience} onChange={set("audience")} placeholder="Marketing teams at startups" />
          <Field label="Primary goal" value={form.goal} onChange={set("goal")} placeholder="Generate leads, sell product…" />
          <Field label="Monthly budget (USD)" value={form.monthly_budget} onChange={set("monthly_budget")} placeholder="2000" type="number" />
          <Select label="Model" value={form.business_model} onChange={set("business_model")} options={[["b2b", "B2B"], ["b2c", "B2C"]]} />
          <Select label="Preference" value={form.preference} onChange={set("preference")} options={[["hybrid", "Paid + organic"], ["paid", "Paid only"], ["organic", "Organic only"]]} />
          <Select label="Desired speed" value={form.speed} onChange={set("speed")} options={[["fast", "Fast"], ["medium", "Medium"], ["slow", "Slow / evergreen"]]} />
        </div>
        <div className="mt-5 flex items-center gap-3">
          <Button onClick={() => mutate.mutate()} disabled={mutate.isPending || !workspaceId}>
            {mutate.isPending ? "Thinking…" : "Recommend my growth path"}
          </Button>
          <Link to="/traffic" className="text-sm text-slate-500 hover:text-ink">Back to Traffic Genie</Link>
        </div>
        {error ? (
          <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div>
        ) : null}
      </Card>

      {plan ? <PlanView plan={plan} onPlan={planCampaign} /> : null}
    </div>
  );
}

function PlanView({ plan, onPlan }: { plan: TrafficRecommendation; onPlan: (slug: string) => void }) {
  const channels: { label: string; source: TrafficSource | null | undefined }[] = [
    { label: "Primary source", source: plan.primary_source },
    { label: "Secondary source", source: plan.secondary_source },
    { label: "Organic support", source: plan.organic_support },
    { label: "Retargeting", source: plan.retargeting_channel },
  ];
  return (
    <div className="flex flex-col gap-5">
      <Card className="border-grape-200 bg-grape-50/40">
        <CardHeader title="Recommended growth path" subtitle={plan.why} />
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <Stat label="Follow-up" value={plan.follow_up_journey} />
          <Stat label="Difficulty" value={plan.estimated_difficulty} />
          <Stat label="Speed" value={plan.estimated_speed} />
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {channels.map((c) =>
          c.source ? (
            <div key={c.label} className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{c.label}</span>
              <SourceCard source={c.source} onPlan={onPlan} />
            </div>
          ) : null,
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <PlanList title="7-day launch plan" items={plan.launch_plan_7_day} />
        <PlanList title="30-day optimization plan" items={plan.optimization_plan_30_day} />
      </div>

      {plan.assets_needed && plan.assets_needed.length > 0 ? (
        <Card>
          <CardHeader title="Assets you'll need" subtitle={plan.tracking_setup} />
          <div className="mt-3 flex flex-wrap gap-1.5">
            {plan.assets_needed.map((a) => (
              <span key={a} className="pill bg-slate-100 text-slate-600">{a.replace(/_/g, " ")}</span>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}

function PlanList({ title, items }: { title: string; items?: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <Card>
      <CardHeader title={title} />
      <ol className="mt-3 flex flex-col gap-2 text-sm text-slate-700">
        {items.map((step, i) => (
          <li key={i} className="flex gap-2">
            <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-grape-100 text-[11px] font-semibold text-grape-700">
              {i + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function Stat({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-medium text-ink">{value ?? "—"}</div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none transition focus:border-grape focus:ring-2 focus:ring-grape-200"
      />
    </label>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  options: [string, string][];
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <select
        value={value}
        onChange={onChange}
        className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none transition focus:border-grape focus:ring-2 focus:ring-grape-200"
      >
        {options.map(([v, l]) => (
          <option key={v} value={v}>{l}</option>
        ))}
      </select>
    </label>
  );
}
