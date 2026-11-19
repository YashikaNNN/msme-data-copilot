const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "msme_auth_token";

export type Business = {
  id: number;
  business_name: string;
  owner_name: string;
  email: string;
  created_at?: string | null;
};

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

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail || data.message || response.statusText;
  } catch {
    return response.statusText || "Request failed";
  }
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (extra) Object.assign(headers, extra);
  return headers;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    cache: "no-store",
    headers: authHeaders(),
  });
  if (response.status === 401) {
    setToken(null);
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const isForm = body instanceof FormData;
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    method: "POST",
    headers: isForm ? authHeaders() : authHeaders({ "Content-Type": "application/json" }),
    body: isForm ? body : body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (response.status === 401) {
    setToken(null);
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
  }
  if (!response.ok) throw new Error(await parseError(response));
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function apiDelete(path: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export async function downloadAuthenticated(path: string, fallbackName: string) {
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] || fallbackName;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function exportUrl(path: string): string {
  return `${API_BASE}/api/v1${path}`;
}
