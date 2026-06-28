import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ApiError } from "@/lib/api-client";
import { generatePlaybook } from "@/lib/solo-ads";
import type { SoloAdsPlaybook } from "@/types/api";

export function SoloAdsPlaybookPanel({ workspaceId }: { workspaceId: string }) {
  const [form, setForm] = useState({
    offer_name: "",
    offer_url: "",
    audience: "",
    goal: "",
    vendor_name: "",
    campaign_name: "",
  });
  const [playbook, setPlaybook] = useState<SoloAdsPlaybook | null>(null);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const mutate = useMutation({
    mutationFn: () =>
      generatePlaybook(workspaceId, {
        offer_name: form.offer_name || undefined,
        offer_url: form.offer_url || undefined,
        audience: form.audience || undefined,
        goal: form.goal || undefined,
        vendor_name: form.vendor_name || undefined,
        campaign_name: form.campaign_name || undefined,
      }),
    onSuccess: (data) => {
      setPlaybook(data);
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not generate the playbook."),
  });

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader title="Generate a solo-ads playbook" subtitle="Vendor-ready swipes, subjects, screening checklist, follow-up and a tracking plan." />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Input label="Offer name" value={form.offer_name} onChange={set("offer_name")} placeholder="Free SEO checklist" />
          <Input label="Offer URL" value={form.offer_url} onChange={set("offer_url")} placeholder="https://…" />
          <Input label="Audience" value={form.audience} onChange={set("audience")} placeholder="Bloggers, coaches…" />
          <Input label="Goal" value={form.goal} onChange={set("goal")} placeholder="Build my email list" />
          <Input label="Vendor (optional)" value={form.vendor_name} onChange={set("vendor_name")} placeholder="For the tracking plan" />
          <Input label="Campaign (optional)" value={form.campaign_name} onChange={set("campaign_name")} placeholder="Q3 list build" />
        </div>
        {error ? <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div> : null}
        <div className="mt-5">
          <Button onClick={() => mutate.mutate()} disabled={mutate.isPending}>
            {mutate.isPending ? "Generating…" : "Generate playbook"}
          </Button>
        </div>
      </Card>

      {playbook ? <PlaybookView playbook={playbook} /> : null}
    </div>
  );
}

function PlaybookView({ playbook }: { playbook: SoloAdsPlaybook }) {
  return (
    <div className="flex flex-col gap-4">
      {playbook.offer_suitability ? (
        <Card className="border-grape-200 bg-grape-50/40">
          <CardHeader title="Offer suitability" />
          <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{playbook.offer_suitability}</p>
        </Card>
      ) : null}

      <ListBlock title="Subject lines" items={playbook.subject_lines} copyable />
      <SwipesBlock swipes={playbook.email_swipes} />

      {(playbook.landing_headline || playbook.preheader || playbook.cta_options?.length) ? (
        <Card>
          <CardHeader title="Landing & email copy" />
          <dl className="mt-3 flex flex-col gap-2 text-sm">
            {playbook.landing_headline ? <Row label="Landing headline" value={playbook.landing_headline} /> : null}
            {playbook.preheader ? <Row label="Preheader" value={playbook.preheader} /> : null}
            {playbook.thank_you_cta ? <Row label="Thank-you CTA" value={playbook.thank_you_cta} /> : null}
            {playbook.cta_options?.length ? <Row label="CTAs" value={playbook.cta_options.join("  ·  ")} /> : null}
          </dl>
        </Card>
      ) : null}

      <ListBlock title="Vendor screening checklist" items={playbook.vendor_screening_checklist} ordered />
      <ListBlock title="Omnisend follow-up sequence" items={playbook.followup_sequence} ordered />
      <ListBlock title="Tracking plan" items={playbook.tracking_plan} ordered />

      {playbook.compliance_notes?.length ? (
        <Card className="bg-amber-50">
          <CardHeader title="Compliance & quality guardrails" />
          <ul className="mt-2 flex list-disc flex-col gap-1.5 pl-5 text-xs text-amber-800">
            {playbook.compliance_notes.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}

function ListBlock({ title, items, ordered, copyable }: { title: string; items?: string[]; ordered?: boolean; copyable?: boolean }) {
  if (!items || items.length === 0) return null;
  return (
    <Card>
      <CardHeader
        title={title}
        action={copyable ? <CopyButton text={items.join("\n")} /> : undefined}
      />
      {ordered ? (
        <ol className="mt-3 flex flex-col gap-1.5 text-sm text-slate-700">
          {items.map((it, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-grape-100 text-[11px] font-semibold text-grape-700">{i + 1}</span>
              <span>{it}</span>
            </li>
          ))}
        </ol>
      ) : (
        <ul className="mt-3 flex flex-col gap-1.5">
          {items.map((it, i) => (
            <li key={i} className="rounded-lg bg-slate-50 px-3 py-1.5 text-sm text-slate-700">{it}</li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function SwipesBlock({ swipes }: { swipes?: string[] }) {
  if (!swipes || swipes.length === 0) return null;
  return (
    <Card>
      <CardHeader title="Email swipes" subtitle="Send these to the vendor — edit before use." />
      <div className="mt-3 flex flex-col gap-3">
        {swipes.map((s, i) => (
          <div key={i}>
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Swipe {i + 1}</span>
              <CopyButton text={s} />
            </div>
            <pre className="whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm leading-relaxed text-slate-700">{s}</pre>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="text-slate-700">{value}</dd>
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant="ghost"
      className="text-xs"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* clipboard unavailable */
        }
      }}
    >
      {copied ? "Copied!" : "Copy"}
    </Button>
  );
}

function Input({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none transition focus:border-grape focus:ring-2 focus:ring-grape-200"
      />
    </label>
  );
}
