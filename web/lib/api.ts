// Typed API client for the PRism backend. Called from server components, so
// fetches are uncached (no-store) to always show current data.

import type {
  AnalysisDetail,
  AnalysisSummary,
  EvalResult,
  HealthResponse,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export function listAnalyses(): Promise<AnalysisSummary[]> {
  return getJson<AnalysisSummary[]>("/api/analyses");
}

export function getAnalysis(id: string): Promise<AnalysisDetail> {
  return getJson<AnalysisDetail>(`/api/analyses/${id}`);
}

export function getEvalLatest(): Promise<EvalResult> {
  return getJson<EvalResult>("/api/eval/latest");
}
