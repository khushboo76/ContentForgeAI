// Thin client for calling the FastAPI backend from the dashboard.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type GenerationParams = Partial<{
  tone: string;
  sentiment: string;
  audience: string;
  language: string;
  detail_level: string;
}>;

export interface GenerateRequest {
  source_content: string;
  output_types: string[];
  params?: GenerationParams;
}

export interface ConnectedAccount {
  id: string;
  platform: "linkedin" | "gmail";
  account_name: string;
  account_handle?: string | null;
  created_at: string;
}

export interface PublicationRecord {
  id: string;
  channel: "linkedin" | "gmail" | "email";
  status: "published" | "failed";
  output_type?: string;
  external_id?: string;
  external_url?: string;
  recipient?: string;
  content_summary?: string;
  error_message?: string;
  published_at: string;
}

export function getUserId(): string {
  if (typeof window === "undefined") return "default_operator";
  let uid = localStorage.getItem("content_engine_user_id");
  if (!uid) {
    uid = "usr_" + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
    localStorage.setItem("content_engine_user_id", uid);
  }
  return uid;
}

function getHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return {
    "X-User-Id": getUserId(),
    ...extra,
  };
}

async function handleJsonResponse(res: Response) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export async function listOutputTypes(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/output-types`, { headers: getHeaders() });
  const data = await res.json();
  return data.output_types;
}

export async function generateOutputs(payload: GenerateRequest) {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  return handleJsonResponse(res);
}

export async function ingestFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/ingest-file`, {
    method: "POST",
    headers: getHeaders(),
    body: formData,
  });
  const data = await handleJsonResponse(res);
  return data.source_content;
}

export async function ingestUrl(url: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/ingest-url`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ url }),
  });
  const data = await handleJsonResponse(res);
  return data.source_content;
}

export async function generateFromMedia(
  file: File,
  outputTypes: string[],
  params: GenerationParams
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("output_types", JSON.stringify(outputTypes));
  formData.append("params", JSON.stringify(params));
  const res = await fetch(`${API_BASE}/api/generate-from-media`, {
    method: "POST",
    headers: getHeaders(),
    body: formData,
  });
  return handleJsonResponse(res);
}

// ============================================================================
// OAuth & Account Management
// ============================================================================

export async function getAuthorizationUrl(platform: "linkedin" | "gmail") {
  const res = await fetch(`${API_BASE}/api/auth/${platform}/authorize-url`, {
    headers: getHeaders(),
  });
  return handleJsonResponse(res);
}

export async function completeOAuthCallback(platform: "linkedin" | "gmail", code: string, state: string) {
  const res = await fetch(`${API_BASE}/api/auth/${platform}/callback`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ code, state }),
  });
  return handleJsonResponse(res);
}

export async function listConnectedAccounts(): Promise<ConnectedAccount[]> {
  const res = await fetch(`${API_BASE}/api/accounts`, {
    headers: getHeaders(),
  });
  const data = await handleJsonResponse(res);
  return data.accounts;
}

export async function disconnectAccount(accountId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/accounts/${accountId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  await handleJsonResponse(res);
}

// ============================================================================
// Publishing Endpoints
// ============================================================================

export async function publishToLinkedIn(payload: {
  account_id: string;
  text: string;
  output_id?: string;
  output_type?: string;
}) {
  const res = await fetch(`${API_BASE}/api/publish/linkedin`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  return handleJsonResponse(res);
}

export async function sendEmailDeliverable(payload: {
  account_id: string;
  recipients: string[];
  subject: string;
  body_text: string;
  body_html?: string;
  output_id?: string;
  output_type?: string;
}) {
  const res = await fetch(`${API_BASE}/api/publish/email`, {
    method: "POST",
    headers: getHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(payload),
  });
  return handleJsonResponse(res);
}

export async function getPublishHistory(): Promise<PublicationRecord[]> {
  const res = await fetch(`${API_BASE}/api/publish/history`, {
    headers: getHeaders(),
  });
  const data = await handleJsonResponse(res);
  return data.publications;
}
