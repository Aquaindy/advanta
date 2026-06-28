import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { SoloAdsPlaybookPanel } from "@/features/traffic/SoloAdsPlaybook";
import { ApiError } from "@/lib/api-client";
import {
  createOrder,
  createVendor,
  deleteOrder,
  deleteVendor,
  listOrders,
  listVendors,
  scoreOrder,
} from "@/lib/solo-ads";
import { cn } from "@/lib/utils";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { SoloAdOrder, SoloAdVendor } from "@/types/api";

type Tab = "orders" | "vendors" | "playbook";

function money(cents: number | null | undefined, currency?: string | null): string {
  if (cents === null || cents === undefined) return "—";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency ?? "USD",
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

function verdictTone(verdict: string | null): string {
  switch (verdict) {
    case "Excellent":
    case "Strong":
      return "pill-success";
    case "Promising":
      return "pill-grape";
    case "Weak":
      return "pill-warning";
    case "Risky":
    case "Poor Quality":
      return "pill-danger";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

export function SoloAdsPage() {
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const [tab, setTab] = useState<Tab>("orders");

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header>
        <p className="text-xs uppercase tracking-wider text-grape-700">Traffic Genie · Paid email</p>
        <h1 className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">Solo Ads</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          Turn paid email traffic into trackable campaigns. Manage vendors, log click orders with
          ROI, score traffic quality, and generate vendor-ready swipes + follow-up.
        </p>
      </header>

      <div className="flex flex-wrap gap-1.5">
        <TabChip label="Orders & ROI" active={tab === "orders"} onClick={() => setTab("orders")} />
        <TabChip label="Vendors" active={tab === "vendors"} onClick={() => setTab("vendors")} />
        <TabChip label="Playbook" active={tab === "playbook"} onClick={() => setTab("playbook")} />
      </div>

      {!workspaceId ? null : tab === "orders" ? (
        <OrdersTab workspaceId={workspaceId} />
      ) : tab === "vendors" ? (
        <VendorsTab workspaceId={workspaceId} />
      ) : (
        <SoloAdsPlaybookPanel workspaceId={workspaceId} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

function OrdersTab({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();
  const [showNew, setShowNew] = useState(false);

  const vendors = useQuery({
    queryKey: ["solo-ads", "vendors", workspaceId],
    queryFn: () => listVendors(workspaceId),
  });
  const orders = useQuery({
    queryKey: ["solo-ads", "orders", workspaceId],
    queryFn: () => listOrders(workspaceId),
  });

  const vendorName = useMemo(() => {
    const m = new Map<string, string>();
    for (const v of vendors.data ?? []) m.set(v.id, v.name);
    return m;
  }, [vendors.data]);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["solo-ads", "orders", workspaceId] });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowNew((v) => !v)}>{showNew ? "Close" : "Log an order"}</Button>
      </div>

      {showNew ? (
        <NewOrderForm
          workspaceId={workspaceId}
          vendors={vendors.data ?? []}
          onClose={() => setShowNew(false)}
          onCreated={() => {
            invalidate();
            setShowNew(false);
          }}
        />
      ) : null}

      {orders.isLoading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : orders.data && orders.data.length > 0 ? (
        <div className="flex flex-col gap-3">
          {orders.data.map((o) => (
            <OrderCard
              key={o.id}
              order={o}
              vendorName={o.vendor_id ? vendorName.get(o.vendor_id) ?? "Unknown vendor" : "No vendor"}
              onChanged={invalidate}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No solo-ad orders yet"
          description="Log a click order with what you paid and what it produced — opt-ins, sales, revenue — and the Quality Guard will score the traffic."
          action={<Button onClick={() => setShowNew(true)}>Log an order</Button>}
        />
      )}
    </div>
  );
}

function OrderCard({
  order,
  vendorName,
  onChanged,
}: {
  order: SoloAdOrder;
  vendorName: string;
  onChanged: () => void;
}) {
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId)!;
  const queryClient = useQueryClient();

  const score = useMutation({
    mutationFn: () => scoreOrder(workspaceId, order.id),
    onSuccess: () => onChanged(),
  });
  const remove = useMutation({
    mutationFn: () => deleteOrder(workspaceId, order.id),
    onSuccess: () => {
      onChanged();
      queryClient.invalidateQueries({ queryKey: ["solo-ads", "vendors", workspaceId] });
    },
  });

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-ink">{order.name || vendorName}</div>
          <div className="text-xs text-slate-500">{vendorName} · {order.status}</div>
        </div>
        {order.quality_verdict ? (
          <span className={cn("pill", verdictTone(order.quality_verdict))}>
            {order.quality_score}/100 · {order.quality_verdict}
          </span>
        ) : (
          <span className="pill bg-slate-100 text-slate-500">Not scored</span>
        )}
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4 lg:grid-cols-7">
        <Stat label="Delivered" value={`${order.clicks_delivered}/${order.clicks_purchased}`} />
        <Stat label="Cost" value={money(order.cost_cents, order.currency)} />
        <Stat label="Opt-ins" value={`${order.optins}${order.optin_rate != null ? ` (${(order.optin_rate * 100).toFixed(0)}%)` : ""}`} />
        <Stat label="Sales" value={String(order.sales)} />
        <Stat label="CPL" value={money(order.cpl_cents, order.currency)} />
        <Stat label="EPC" value={money(order.epc_cents, order.currency)} />
        <Stat label="ROI" value={order.roi != null ? `${(order.roi * 100).toFixed(0)}%` : "—"} tone={order.roi != null && order.roi < 0 ? "danger" : undefined} />
      </dl>

      {order.quality_flags && order.quality_flags.length > 0 ? (
        <ul className="mt-3 flex flex-col gap-1.5">
          {order.quality_flags.map((f, i) => (
            <li key={i} className="rounded-lg bg-amber-50 px-3 py-1.5 text-xs text-amber-800">{f}</li>
          ))}
        </ul>
      ) : order.quality_note ? (
        <p className="mt-3 rounded-lg bg-slate-50 px-3 py-1.5 text-xs text-slate-600">{order.quality_note}</p>
      ) : null}

      <div className="mt-4 flex items-center gap-2">
        <Button variant="secondary" onClick={() => score.mutate()} disabled={score.isPending} className="text-xs">
          {score.isPending ? "Scoring…" : order.quality_verdict ? "Re-score" : "Run Quality Guard"}
        </Button>
        <button
          type="button"
          onClick={() => { if (window.confirm("Delete this order?")) remove.mutate(); }}
          className="text-xs font-medium text-danger hover:underline"
        >
          Delete
        </button>
      </div>
    </Card>
  );
}

function NewOrderForm({
  workspaceId,
  vendors,
  onClose,
  onCreated,
}: {
  workspaceId: string;
  vendors: SoloAdVendor[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [vendorId, setVendorId] = useState("");
  const [name, setName] = useState("");
  const [f, setF] = useState({
    clicks_purchased: "",
    clicks_delivered: "",
    unique_clicks: "",
    cost: "",
    optins: "",
    sales: "",
    revenue: "",
    refunds: "",
  });
  const [error, setError] = useState<string | null>(null);
  const num = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF((s) => ({ ...s, [k]: e.target.value }));
  const toInt = (v: string) => (v ? Math.round(Number(v)) : 0);
  const toCents = (v: string) => (v ? Math.round(Number(v) * 100) : 0);

  const create = useMutation({
    mutationFn: () =>
      createOrder(workspaceId, {
        vendor_id: vendorId || null,
        name: name || null,
        clicks_purchased: toInt(f.clicks_purchased),
        clicks_delivered: toInt(f.clicks_delivered),
        unique_clicks: toInt(f.unique_clicks),
        cost_cents: toCents(f.cost),
        optins: toInt(f.optins),
        sales: toInt(f.sales),
        revenue_cents: toCents(f.revenue),
        refunds: toInt(f.refunds),
        currency: "USD",
        status: "completed",
      }),
    onSuccess: onCreated,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not log the order."),
  });

  return (
    <Card>
      <CardHeader title="Log a solo-ad order" subtitle="Enter the real numbers — economics + quality are computed from them." />
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-500">Vendor</span>
          <select value={vendorId} onChange={(e) => setVendorId(e.target.value)} className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none focus:border-grape focus:ring-2 focus:ring-grape-200">
            <option value="">No vendor</option>
            {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        </label>
        <NumInput label="Order name (optional)" value={name} onChange={(e) => setName(e.target.value)} text />
        <NumInput label="Clicks purchased" value={f.clicks_purchased} onChange={num("clicks_purchased")} />
        <NumInput label="Clicks delivered" value={f.clicks_delivered} onChange={num("clicks_delivered")} />
        <NumInput label="Unique clicks" value={f.unique_clicks} onChange={num("unique_clicks")} />
        <NumInput label="Cost (USD)" value={f.cost} onChange={num("cost")} />
        <NumInput label="Opt-ins" value={f.optins} onChange={num("optins")} />
        <NumInput label="Sales" value={f.sales} onChange={num("sales")} />
        <NumInput label="Revenue (USD)" value={f.revenue} onChange={num("revenue")} />
        <NumInput label="Refunds" value={f.refunds} onChange={num("refunds")} />
      </div>
      {error ? <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div> : null}
      <div className="mt-5 flex items-center gap-2">
        <Button onClick={() => create.mutate()} disabled={create.isPending}>{create.isPending ? "Saving…" : "Save order"}</Button>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Vendors
// ---------------------------------------------------------------------------

function VendorsTab({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient();
  const [showNew, setShowNew] = useState(false);
  const vendors = useQuery({
    queryKey: ["solo-ads", "vendors", workspaceId],
    queryFn: () => listVendors(workspaceId),
  });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["solo-ads", "vendors", workspaceId] });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setShowNew((v) => !v)}>{showNew ? "Close" : "Add vendor"}</Button>
      </div>
      {showNew ? <NewVendorForm workspaceId={workspaceId} onClose={() => setShowNew(false)} onCreated={() => { invalidate(); setShowNew(false); }} /> : null}

      {vendors.isLoading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : vendors.data && vendors.data.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {vendors.data.map((v) => <VendorCard key={v.id} vendor={v} workspaceId={workspaceId} onChanged={invalidate} />)}
        </div>
      ) : (
        <EmptyState
          title="No vendors yet"
          description="Add the email-list owners you buy clicks from. Their quality score rolls up automatically as you score orders."
          action={<Button onClick={() => setShowNew(true)}>Add vendor</Button>}
        />
      )}
    </div>
  );
}

function VendorCard({ vendor, workspaceId, onChanged }: { vendor: SoloAdVendor; workspaceId: string; onChanged: () => void }) {
  const remove = useMutation({ mutationFn: () => deleteVendor(workspaceId, vendor.id), onSuccess: onChanged });
  return (
    <Card className="flex flex-col gap-2 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-ink">{vendor.name}</div>
          <div className="mt-0.5 truncate text-xs text-slate-500">{[vendor.niche, vendor.countries].filter(Boolean).join(" · ") || "—"}</div>
        </div>
        {vendor.quality_score != null ? (
          <span className={cn("pill", vendor.quality_score >= 70 ? "pill-success" : vendor.quality_score >= 40 ? "pill-warning" : "pill-danger")}>
            {vendor.quality_score}/100
          </span>
        ) : <span className="pill bg-slate-100 text-slate-500">Unrated</span>}
      </div>
      <div className="flex flex-wrap gap-1.5 text-[11px]">
        <span className="pill bg-slate-100 text-slate-600">{vendor.status}</span>
        {vendor.average_cpc_cents != null ? <span className="pill bg-slate-100 text-slate-600">~{money(vendor.average_cpc_cents)}/click</span> : null}
      </div>
      {vendor.notes ? <p className="line-clamp-2 text-xs text-slate-500">{vendor.notes}</p> : null}
      <button type="button" onClick={() => { if (window.confirm("Delete this vendor?")) remove.mutate(); }} className="mt-1 self-start text-xs font-medium text-danger hover:underline">
        Delete
      </button>
    </Card>
  );
}

function NewVendorForm({ workspaceId, onClose, onCreated }: { workspaceId: string; onClose: () => void; onCreated: () => void }) {
  const [f, setF] = useState({ name: "", niche: "", countries: "", contact_email: "", website: "", notes: "" });
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF((s) => ({ ...s, [k]: e.target.value }));
  const create = useMutation({
    mutationFn: () => createVendor(workspaceId, {
      name: f.name.trim(), niche: f.niche || null, countries: f.countries || null,
      contact_email: f.contact_email || null, website: f.website || null, notes: f.notes || null,
    }),
    onSuccess: onCreated,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not add the vendor."),
  });
  return (
    <Card>
      <CardHeader title="Add a solo-ad vendor" />
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <NumInput label="Name *" value={f.name} onChange={set("name")} text />
        <NumInput label="Niche" value={f.niche} onChange={set("niche")} text />
        <NumInput label="Countries" value={f.countries} onChange={set("countries")} text />
        <NumInput label="Contact email" value={f.contact_email} onChange={set("contact_email")} text />
        <NumInput label="Website" value={f.website} onChange={set("website")} text />
        <NumInput label="Notes" value={f.notes} onChange={set("notes")} text />
      </div>
      {error ? <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">{error}</div> : null}
      <div className="mt-5 flex items-center gap-2">
        <Button onClick={() => create.mutate()} disabled={create.isPending || !f.name.trim()}>{create.isPending ? "Adding…" : "Add vendor"}</Button>
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
      </div>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Small bits
// ---------------------------------------------------------------------------

function TabChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("rounded-full px-4 py-1.5 text-sm font-medium transition", active ? "bg-grape text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200")}
    >
      {label}
    </button>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "danger" }) {
  return (
    <div>
      <div className="text-xs text-slate-400">{label}</div>
      <div className={cn("font-medium", tone === "danger" ? "text-danger" : "text-ink")}>{value}</div>
    </div>
  );
}

function NumInput({
  label,
  value,
  onChange,
  text,
}: {
  label: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  text?: boolean;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-500">{label}</span>
      <input
        type={text ? "text" : "number"}
        value={value}
        onChange={onChange}
        className="rounded-xl border border-slate-200 bg-surface px-3 py-2 text-ink shadow-sm outline-none transition focus:border-grape focus:ring-2 focus:ring-grape-200"
      />
    </label>
  );
}
