import { apiFetch } from "@/lib/api-client";
import type {
  BillingStatus,
  CheckoutSessionResponse,
  PortalSessionResponse,
} from "@/types/api";

export function getBillingStatus(workspaceId: string) {
  return apiFetch<BillingStatus>(`/workspaces/${workspaceId}/billing/status`);
}

export function createCheckoutSession(
  workspaceId: string,
  planCode: string,
  interval: "month" | "year" = "month",
) {
  return apiFetch<CheckoutSessionResponse>(
    `/workspaces/${workspaceId}/billing/checkout-session`,
    { method: "POST", body: { plan_code: planCode, interval } },
  );
}

export function createPortalSession(workspaceId: string) {
  return apiFetch<PortalSessionResponse>(
    `/workspaces/${workspaceId}/billing/portal-session`,
    { method: "POST" },
  );
}
