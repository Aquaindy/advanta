import { apiFetch } from "@/lib/api-client";
import { API_BASE_URL } from "@/lib/constants";
import { useAuthStore } from "@/stores/auth-store";
import type {
  AgentRunDetail,
  SuggestedCopy,
  SuggestedCopyType,
} from "@/types/api";

export function listSuggestedCopies(
  workspaceId: string,
  params?: { copy_type?: SuggestedCopyType; profile_id?: string },
) {
  const qs = new URLSearchParams();
  if (params?.copy_type) qs.set("copy_type", params.copy_type);
  if (params?.profile_id) qs.set("profile_id", params.profile_id);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiFetch<SuggestedCopy[]>(
    `/workspaces/${workspaceId}/suggested-copies${suffix}`,
  );
}

/** Runs the Growth Content Studio agent (billed as one agent run / 10 AI credits). */
export function generateSuggestedCopies(
  workspaceId: string,
  payload: { product_name?: string; profile_id?: string },
) {
  return apiFetch<AgentRunDetail>(
    `/workspaces/${workspaceId}/suggested-copies/generate`,
    { method: "POST", body: payload },
  );
}

export function deleteSuggestedCopy(workspaceId: string, copyId: string) {
  return apiFetch<void>(
    `/workspaces/${workspaceId}/suggested-copies/${copyId}`,
    { method: "DELETE" },
  );
}

type DownloadFormat = "txt" | "docx";

async function fetchBlob(path: string): Promise<Blob> {
  const token = useAuthStore.getState().accessToken;
  const url = new URL(path, API_BASE_URL.replace(/\/$/, "") + "/");
  const response = await fetch(url.toString(), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error(`Download failed (${response.status}).`);
  }
  return response.blob();
}

export function fetchSuggestedCopyBlob(
  workspaceId: string,
  copyId: string,
  format: DownloadFormat,
): Promise<Blob> {
  return fetchBlob(
    `workspaces/${workspaceId}/suggested-copies/${copyId}/download?format=${format}`,
  );
}

export function fetchSuggestedCopiesBundleBlob(
  workspaceId: string,
  format: DownloadFormat,
  params?: { copy_type?: SuggestedCopyType; profile_id?: string },
): Promise<Blob> {
  const qs = new URLSearchParams({ format });
  if (params?.copy_type) qs.set("copy_type", params.copy_type);
  if (params?.profile_id) qs.set("profile_id", params.profile_id);
  return fetchBlob(
    `workspaces/${workspaceId}/suggested-copies/download?${qs.toString()}`,
  );
}

/** Trigger a browser download for an already-fetched blob. */
export function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
