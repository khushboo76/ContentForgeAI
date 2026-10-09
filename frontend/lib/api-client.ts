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

async function handleJsonResponse(res: Response) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export async function listOutputTypes(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/output-types`);
  const data = await res.json();
  return data.output_types;
}

export async function generateOutputs(payload: GenerateRequest) {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleJsonResponse(res);
}

export async function ingestFile(file: File): Promise<string> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/ingest-file`, { method: "POST", body: formData });
  const data = await handleJsonResponse(res);
  return data.source_content;
}

export async function ingestUrl(url: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/ingest-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
    body: formData,
  });
  return handleJsonResponse(res);
}
