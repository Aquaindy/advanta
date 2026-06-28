import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ApiError } from "@/lib/api-client";
import { createUtmLink, deleteUtmLink, listUtmLinks } from "@/lib/traffic";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { UtmLink } from "@/types/api";

function normalize(v: string): string {
  return v.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

export function UtmBuilderPage() {
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const queryClient = useQueryClient();
  const [params] = useSearchParams();
  const campaignId = params.get("campaign");

  const [destination, setDestination] = useState("");
  const [source, setSource] = useState("");
  const [medium, setMedium] = useState("");
  const [campaign, setCampaign] = useState("");
  const [content, setContent] = useState("");
  const [term, setTerm] = useState("");
  const [vendor, setVendor] = useState("");
  const [error, setError] = useState<string | null>(null);

  const links = useQuery({
    queryKey: ["traffic", "utm-links", workspaceId],
    queryFn: () => listUtmLinks(workspaceId!),
    enabled: !!workspaceId,
  });

  const create = useMutation({
    mutationFn: () =>
      createUtmLink(workspaceId!, {
        destination_url: destination.trim(),
        source,
        medium,
        campaign,
        content: content || null,
        term: term || null,
        vendor_name: vendor || null,
        campaign_id: campaignId,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["traffic", "utm-links", workspaceId] });
      setError(null);
      setContent("");
      setTerm("");
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not create link."),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteUtmLink(workspaceId!, id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["traffic", "utm-links", workspaceId] }),
  });

  const canBuild = destination.trim() && source && medium && campaign;
  const preview =
    canBuild && /^https?:\/\//i.test(destination.trim())
      ? buildPreview(destination.trim(), { source, medium, campaign, content, term })
      : null;

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <header>
        <p className="text-xs uppercase tracking-wider text-grape-700">Traffic Genie</p>
        <h1 className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">Smart UTM builder</h1>
        <p className="mt-2 text-sm text-slate-500">
          Generate consistent tracking links for every traffic source. Values are normalized to
          lowercase snake_case so the same campaign always rolls up cleanly.
        </p>
      </header>

      <Card>
        <CardHeader title="Build a link" subtitle="Source, medium and campaign are required." />
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Input label="Destination URL" value={destination} onChange={setDestination} placeholder="https://example.com/offer" required className="sm:col-span-2" />
          <Input label="Source" value={source} onChange={setSource} placeholder="solo_ad_vendor, google, tiktok" required />
          <Input label="Medium" value={medium} onChange={setMedium} placeholder="paid_email, cpc, organic" required />
          <Input label="Campaign" value={campaign} onChange={setCampaign} placeholder="lead_magnet_launch" required />
          <Input label="Content (optional)" value={content} onChange={setContent} placeholder="email_swipe_a" />
          <Input label="Term (optional)" value={term} onChange={setTerm} placeholder="make_money_online" />
          <Input label="Vendor (optional)" value={vendor} onChange={setVendor} placeholder="For solo ads" />
        </div>

        {preview ? (
          <div className="mt-4 rounded-xl bg-slate-50 p-3">
            <div className="text-xs uppercase tracking-wider text-slate-400">Preview</div>
            <code className="mt-1 block break-all text-xs text-grape-800">{preview}</code>
          </div>
        ) : null}

        {error ? <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div> : null}

        <div className="mt-5">
          <Button onClick={() => create.mutate()} disabled={create.isPending || !canBuild}>
            {create.isPending ? "Saving…" : "Generate & save link"}
          </Button>
        </div>
      </Card>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold text-ink">Saved links</h2>
        {links.isLoading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : links.data && links.data.length > 0 ? (
          <div className="flex flex-col gap-2">
            {links.data.map((l) => (
              <LinkRow key={l.id} link={l} onDelete={() => remove.mutate(l.id)} />
            ))}
          </div>
        ) : (
          <EmptyState title="No tracking links yet" description="Build your first UTM link above to start tracking every source consistently." />
        )}
      </section>
    </div>
  );
}

function LinkRow({ link, onDelete }: { link: UtmLink; onDelete: () => void }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(link.generated_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };
  return (
    <div className="card flex flex-col gap-2 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5 text-[11px]">
          <span className="pill pill-grape">{link.source}</span>
          <span className="pill bg-slate-100 text-slate-600">{link.medium}</span>
          <span className="pill bg-slate-100 text-slate-600">{link.campaign}</span>
          {link.vendor_name ? <span className="pill pill-warning">{link.vendor_name}</span> : null}
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" onClick={copy} className="text-xs">{copied ? "Copied!" : "Copy"}</Button>
          <button type="button" onClick={onDelete} className="text-xs font-medium text-danger hover:underline">Delete</button>
        </div>
      </div>
      <code className="block break-all text-xs text-slate-600">{link.generated_url}</code>
    </div>
  );
}

function buildPreview(
  url: string,
  parts: { source: string; medium: string; campaign: string; content: string; term: string },
): string {
  try {
    const u = new URL(url);
    u.searchParams.set("utm_source", normalize(parts.source));
    u.searchParams.set("utm_medium", normalize(parts.medium));
    u.searchParams.set("utm_campaign", normalize(parts.campaign));
    if (parts.content) u.searchParams.set("utm_content", normalize(parts.content));
    if (parts.term) u.searchParams.set("utm_term", normalize(parts.term));
    return u.toString();
  } catch {
    return "";
  }
}

function Input({
  label,
  value,
  onChange,
  placeholder,
  required,
  className,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 text-sm ${className ?? ""}`}>
      <span className="text-slate-500">{label}{required ? " *" : ""}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none transition focus:border-grape focus:ring-2 focus:ring-grape-200"
      />
    </label>
  );
}
