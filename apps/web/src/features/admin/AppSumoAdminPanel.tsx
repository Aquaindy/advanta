import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Card, CardHeader } from "@/components/ui/Card";
import { ApiError } from "@/lib/api-client";
import {
  deactivateAppSumoCode,
  generateAppSumoCodes,
  getAppSumoStats,
  type GenerateCodesResult,
} from "@/lib/appsumo";
import { cn } from "@/lib/utils";


/**
 * Superuser-only AppSumo code management: mint batches (to upload to AppSumo),
 * see redemption stats, and deactivate refunded codes. Rendered on the Admin
 * page.
 */
export function AppSumoAdminPanel() {
  const queryClient = useQueryClient();
  const stats = useQuery({
    queryKey: ["admin", "appsumo-stats"],
    queryFn: getAppSumoStats,
  });

  const [count, setCount] = useState(100);
  const [batch, setBatch] = useState("");
  const [prefix, setPrefix] = useState("ADV");
  const [generated, setGenerated] = useState<GenerateCodesResult | null>(null);
  const [copied, setCopied] = useState(false);

  const [deactivateCode, setDeactivateCode] = useState("");
  const [deactivateMsg, setDeactivateMsg] = useState<string | null>(null);

  const generate = useMutation({
    mutationFn: () => generateAppSumoCodes({ count, batch: batch || undefined, prefix }),
    onSuccess: (data) => {
      setGenerated(data);
      setCopied(false);
      queryClient.invalidateQueries({ queryKey: ["admin", "appsumo-stats"] });
    },
  });

  const deactivate = useMutation({
    mutationFn: () => deactivateAppSumoCode(deactivateCode.trim()),
    onSuccess: () => {
      setDeactivateMsg(`Deactivated ${deactivateCode.trim()}. Workspace downgraded if it was redeemed.`);
      setDeactivateCode("");
      queryClient.invalidateQueries({ queryKey: ["admin", "appsumo-stats"] });
    },
    onError: (err) =>
      setDeactivateMsg(err instanceof ApiError ? err.message : "Could not deactivate that code."),
  });

  function copyCodes() {
    if (!generated) return;
    void navigator.clipboard.writeText(generated.codes.join("\n")).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function downloadCsv() {
    if (!generated) return;
    const csv = "code\n" + generated.codes.join("\n") + "\n";
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `appsumo-codes${generated.batch ? `-${generated.batch}` : ""}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const tiles: { label: string; value: number; tone?: "success" | "grape" | "warning" }[] = [
    { label: "Total codes", value: stats.data?.total ?? 0 },
    { label: "Unredeemed", value: stats.data?.unredeemed ?? 0, tone: "grape" },
    { label: "Redeemed", value: stats.data?.redeemed ?? 0, tone: "success" },
    { label: "Refunded", value: stats.data?.refunded ?? 0, tone: "warning" },
  ];

  return (
    <Card>
      <CardHeader
        title="AppSumo codes"
        subtitle="Mint lifetime-deal codes, then upload the CSV to AppSumo."
      />

      <div className="mt-3 grid gap-3 sm:grid-cols-4">
        {tiles.map((t) => (
          <div key={t.label} className="rounded-2xl border border-slate-100 bg-surface px-4 py-3">
            <div className="text-[11px] uppercase tracking-wider text-slate-400">{t.label}</div>
            <div
              className={cn(
                "mt-1 text-2xl font-semibold",
                t.tone === "grape" && "text-grape-700",
                t.tone === "success" && "text-success",
                t.tone === "warning" && "text-warning",
                !t.tone && "text-ink",
              )}
            >
              {t.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* Generate batch */}
      <form
        className="mt-5 flex flex-wrap items-end gap-3 border-t border-slate-100 pt-5"
        onSubmit={(e) => {
          e.preventDefault();
          generate.mutate();
        }}
      >
        <label className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-wider text-slate-400">Count</span>
          <input
            type="number"
            min={1}
            max={10000}
            value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(10000, Number(e.target.value) || 1)))}
            className="w-28 rounded-xl border border-slate-200 bg-surface px-3 py-2 text-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-wider text-slate-400">Batch label</span>
          <input
            value={batch}
            onChange={(e) => setBatch(e.target.value)}
            placeholder="launch-2026"
            className="w-44 rounded-xl border border-slate-200 bg-surface px-3 py-2 text-sm text-ink"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[11px] uppercase tracking-wider text-slate-400">Prefix</span>
          <input
            value={prefix}
            onChange={(e) => setPrefix(e.target.value)}
            className="w-24 rounded-xl border border-slate-200 bg-surface px-3 py-2 text-sm uppercase text-ink"
          />
        </label>
        <button
          type="submit"
          disabled={generate.isPending}
          className="rounded-xl bg-grape px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-grape-800 disabled:opacity-60"
        >
          {generate.isPending ? "Minting…" : "Generate codes"}
        </button>
      </form>

      {generate.error ? (
        <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-500/15 dark:text-red-300">
          {generate.error instanceof ApiError ? generate.error.message : "Generation failed."}
        </p>
      ) : null}

      {generated ? (
        <div className="mt-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-ink">
              {generated.generated} codes minted
              {generated.batch ? ` · ${generated.batch}` : ""}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={copyCodes}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                {copied ? "Copied!" : "Copy"}
              </button>
              <button
                type="button"
                onClick={downloadCsv}
                className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
              >
                Download CSV
              </button>
            </div>
          </div>
          <textarea
            readOnly
            value={generated.codes.join("\n")}
            rows={Math.min(8, generated.codes.length)}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-surface-muted px-3 py-2 font-mono text-xs text-slate-700"
          />
        </div>
      ) : null}

      {/* Deactivate (refund) */}
      <form
        className="mt-5 flex flex-wrap items-end gap-3 border-t border-slate-100 pt-5"
        onSubmit={(e) => {
          e.preventDefault();
          setDeactivateMsg(null);
          if (deactivateCode.trim()) deactivate.mutate();
        }}
      >
        <label className="flex flex-1 flex-col gap-1">
          <span className="text-[11px] uppercase tracking-wider text-slate-400">
            Deactivate a refunded code
          </span>
          <input
            value={deactivateCode}
            onChange={(e) => setDeactivateCode(e.target.value)}
            placeholder="ADV-XXXX-XXXX-XXXX"
            className="w-full rounded-xl border border-slate-200 bg-surface px-3 py-2 font-mono text-sm uppercase text-ink"
          />
        </label>
        <button
          type="submit"
          disabled={deactivate.isPending || !deactivateCode.trim()}
          className="rounded-xl border border-danger/30 px-4 py-2 text-sm font-semibold text-danger transition hover:bg-red-50 disabled:opacity-60 dark:hover:bg-red-500/10"
        >
          {deactivate.isPending ? "Working…" : "Deactivate"}
        </button>
      </form>
      {deactivateMsg ? (
        <p className="mt-2 text-sm text-slate-600">{deactivateMsg}</p>
      ) : null}
    </Card>
  );
}
