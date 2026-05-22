import { apiFetch } from "@/lib/api-client";

export type AppSumoCode = {
  code: string;
  redeemed_at: string | null;
};

export type AppSumoStatus = {
  tier: number;
  codes_redeemed: number;
  max_tier: number;
  can_stack_more: boolean;
  plan_code: string | null;
  plan_display_name: string | null;
  codes: AppSumoCode[];
};

export function getAppSumoStatus(workspaceId: string) {
  return apiFetch<AppSumoStatus>(`/workspaces/${workspaceId}/appsumo/status`);
}

export function redeemAppSumoCode(workspaceId: string, code: string) {
  return apiFetch<AppSumoStatus>(`/workspaces/${workspaceId}/appsumo/redeem`, {
    method: "POST",
    body: { code },
  });
}

// --- Admin (superuser) ------------------------------------------------------

export type AppSumoCodeStats = {
  total: number;
  redeemed: number;
  refunded: number;
  unredeemed: number;
};

export type GenerateCodesResult = {
  generated: number;
  batch: string | null;
  codes: string[];
};

export function getAppSumoStats() {
  return apiFetch<AppSumoCodeStats>("/appsumo/admin/codes/stats");
}

export function generateAppSumoCodes(payload: {
  count: number;
  batch?: string;
  prefix?: string;
}) {
  return apiFetch<GenerateCodesResult>("/appsumo/admin/codes", {
    method: "POST",
    body: payload,
  });
}

export function deactivateAppSumoCode(code: string) {
  return apiFetch<{ deactivated: boolean }>("/appsumo/admin/codes/deactivate", {
    method: "POST",
    body: { code },
  });
}
