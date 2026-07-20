// Typed API client for the PRism backend.
//
// Milestone 1: only the health check is wired. Additional calls (list analyses,
// fetch one analysis, eval metrics) are added as the backend endpoints land.

import type { AnalysisSummary, HealthResponse } from "./types";

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

// Placeholder — returns [] until the backend endpoint exists (later milestone).
export async function listAnalyses(): Promise<AnalysisSummary[]> {
  return [];
}
