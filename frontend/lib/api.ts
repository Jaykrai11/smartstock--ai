import type { Catalog, ForecastResponse, ModelInfo, Overview, Recommendation, SimResponse } from "./types";

// Single place that knows the backend URL. NEXT_PUBLIC_* is exposed to the browser: never put secrets here.
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7860").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function request<T>(path: string, init?: RequestInit, timeoutMs = 60_000): Promise<T> {
  const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_URL}${path}`, { ...init, signal: ctl.signal, headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) } });
    if (!res.ok) {
      let msg = `Request failed (${res.status})`;
      try {
        const body = await res.json();
        if (typeof body.detail === "string") msg = body.detail;
        else if (Array.isArray(body.detail)) msg = body.detail.map((d: any) => `${(d.loc ?? []).slice(1).join(".")}: ${d.msg}`).join("; ");
      } catch { /* non-JSON error body */ }
      throw new ApiError(msg, res.status);
    }
    return (await res.json()) as T;
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if ((e as Error).name === "AbortError") throw new ApiError("The API took too long to respond. It may be waking up — try again in a moment.", 0);
    throw new ApiError("Can't reach the SmartStock API. Check that the backend is running and that its CORS settings allow this site.", 0);
  } finally { clearTimeout(timer); }
}

const post = <T,>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => request<{ status: string; model_version: string | null }>("/health"),
  catalog: () => request<Catalog>("/catalog"),
  overview: () => request<Overview>("/overview"),
  modelInfo: () => request<ModelInfo>("/model-info"),
  forecast: (b: { item_id: string; store_id: string; horizon: number; price_multiplier: number }) => post<ForecastResponse>("/forecast", b),
  recommendation: (b: Record<string, unknown>) => post<Recommendation>("/recommendation", b),
  simulate: (b: Record<string, unknown>) => post<SimResponse>("/simulate", b),
};
