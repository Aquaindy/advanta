import { apiFetch } from "@/lib/api-client";
import type {
  CreateOrderRequest,
  CreateVendorRequest,
  SoloAdOrder,
  SoloAdVendor,
  SoloAdsPlaybook,
  SoloAdsPlaybookRequest,
} from "@/types/api";

const base = (workspaceId: string) => `/workspaces/${workspaceId}/solo-ads`;

// --- Vendors ---
export function listVendors(workspaceId: string) {
  return apiFetch<SoloAdVendor[]>(`${base(workspaceId)}/vendors`);
}
export function createVendor(workspaceId: string, body: CreateVendorRequest) {
  return apiFetch<SoloAdVendor>(`${base(workspaceId)}/vendors`, { method: "POST", body });
}
export function updateVendor(
  workspaceId: string,
  vendorId: string,
  body: Partial<CreateVendorRequest> & { quality_score?: number | null },
) {
  return apiFetch<SoloAdVendor>(`${base(workspaceId)}/vendors/${vendorId}`, { method: "PATCH", body });
}
export function deleteVendor(workspaceId: string, vendorId: string) {
  return apiFetch<void>(`${base(workspaceId)}/vendors/${vendorId}`, { method: "DELETE" });
}

// --- Orders ---
export function listOrders(workspaceId: string, vendorId?: string) {
  return apiFetch<SoloAdOrder[]>(`${base(workspaceId)}/orders`, {
    query: vendorId ? { vendor_id: vendorId } : undefined,
  });
}
export function createOrder(workspaceId: string, body: CreateOrderRequest) {
  return apiFetch<SoloAdOrder>(`${base(workspaceId)}/orders`, { method: "POST", body });
}
export function updateOrder(workspaceId: string, orderId: string, body: CreateOrderRequest) {
  return apiFetch<SoloAdOrder>(`${base(workspaceId)}/orders/${orderId}`, { method: "PATCH", body });
}
export function deleteOrder(workspaceId: string, orderId: string) {
  return apiFetch<void>(`${base(workspaceId)}/orders/${orderId}`, { method: "DELETE" });
}
export function scoreOrder(workspaceId: string, orderId: string) {
  return apiFetch<SoloAdOrder>(`${base(workspaceId)}/orders/${orderId}/quality-score`, {
    method: "POST",
  });
}

// --- Playbook ---
export function generatePlaybook(workspaceId: string, body: SoloAdsPlaybookRequest) {
  return apiFetch<SoloAdsPlaybook>(`${base(workspaceId)}/playbook`, { method: "POST", body });
}
