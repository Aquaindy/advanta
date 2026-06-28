import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { getTrafficCatalog, listTrafficCampaigns, listUtmLinks } from "@/lib/traffic";
import { useWorkspaceStore } from "@/stores/workspace-store";

export function TrafficDashboardPage() {
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId);

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
  const links = useQuery({
    queryKey: ["traffic", "utm-links", workspaceId],
    queryFn: () => listUtmLinks(workspaceId!),
    enabled: !!workspaceId,
  });

  const typeBySlug = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of catalog.data?.sources ?? []) map.set(s.slug, s.source_type);
    return map;
  }, [catalog.data]);

  const counts = useMemo(() => {
    const list = campaigns.data ?? [];
    let paid = 0;
    let paid_email = 0;
    let organic = 0;
    for (const c of list) {
      const t = typeBySlug.get(c.source_slug);
      if (t === "paid") paid += 1;
      else if (t === "paid_email") paid_email += 1;
      else if (t === "organic") organic += 1;
    }
    return {
      total: list.length,
      active: list.filter((c) => c.status === "active").length,
      paid,
      paid_email,
      organic,
    };
  }, [campaigns.data, typeBySlug]);

  const hasData = (campaigns.data?.length ?? 0) > 0 || (links.data?.length ?? 0) > 0;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-grape-700">Traffic Genie</p>
          <h1 className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">Traffic dashboard</h1>
          <p className="mt-2 text-sm text-slate-500">
            Your traffic campaigns and tracking links at a glance.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/traffic/recommendation"><Button variant="secondary">AI recommendation</Button></Link>
          <Link to="/traffic/campaigns"><Button>New campaign</Button></Link>
        </div>
      </header>

      {!hasData ? (
        <EmptyState
          title="No traffic activity yet"
          description="Plan a traffic campaign or build a tracking link, and this dashboard will summarize your paid, organic and paid-email mix."
          action={<Link to="/traffic"><Button>Open Traffic Genie</Button></Link>}
        />
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <StatCard label="Campaigns" value={counts.total} />
            <StatCard label="Active" value={counts.active} />
            <StatCard label="Paid" value={counts.paid} />
            <StatCard label="Organic" value={counts.organic} />
            <StatCard label="Paid email" value={counts.paid_email} />
          </section>

          <Card>
            <CardHeader
              title="Tracking links"
              subtitle={`${links.data?.length ?? 0} UTM link${(links.data?.length ?? 0) === 1 ? "" : "s"} built`}
              action={<Link to="/traffic/utm-builder" className="text-sm font-medium text-grape-700 hover:text-grape-800">UTM builder →</Link>}
            />
          </Card>

          <Card className="bg-slate-50">
            <CardHeader
              title="Performance metrics"
              subtitle="Clicks, leads, sales and ROI populate as you connect analytics sources and import results."
            />
            <p className="mt-2 text-sm text-slate-500">
              Quantitative performance (CPC, CPL, ROAS, EPC, quality scores) comes from connected
              platforms and is rolled out in a later Traffic Genie phase — we don't show estimated or
              placeholder numbers here.
            </p>
          </Card>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card className="p-4">
      <div className="text-xs uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-ink">{value}</div>
    </Card>
  );
}
