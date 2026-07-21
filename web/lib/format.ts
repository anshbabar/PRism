// Small pure formatting/mapping helpers shared across components. Pure functions
// so they are trivially unit-testable.

import type { RiskBand } from "./types";

export function bandFromScore(score: number): RiskBand {
  if (score <= 2) return "low";
  if (score === 3) return "medium";
  return "high";
}

export function bandLabel(band: RiskBand): string {
  return band.charAt(0).toUpperCase() + band.slice(1);
}

// Colors chosen for contrast on the dark theme (green / amber / red).
export function bandColor(band: RiskBand): string {
  switch (band) {
    case "low":
      return "#3fb950";
    case "medium":
      return "#d29922";
    case "high":
      return "#f85149";
  }
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function humanizeCategory(category: string): string {
  return category
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
