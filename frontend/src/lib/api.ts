const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail || data.message || response.statusText;
  } catch {
    return response.statusText || "Request failed";
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    method: "POST",
    headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(await parseError(response));
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, { method: "DELETE" });
  if (!response.ok) throw new Error(await parseError(response));
}

export function exportUrl(path: string): string {
  return `${API_BASE}/api/v1${path}`;
}

export type Dataset = {
  id: number;
  name: string;
  description: string;
  category: string;
  status: string;
  is_sample: boolean;
  row_count: number;
  column_count: number;
  quality_score: number | null;
  created_at?: string;
  updated_at?: string;
};
