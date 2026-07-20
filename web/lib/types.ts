// Shared types mirroring the backend review contract (see docs/technical-design.md §9.2).
// These are placeholders for Milestone 1 and will be filled in as the API lands.

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export type RiskCategory =
  | "auth"
  | "db_schema"
  | "api_contract"
  | "dependency"
  | "test_removed"
  | "missing_tests"
  | "high_churn"
  | "error_handling";

// Placeholder shape of a stored PR analysis — expanded in later milestones.
export interface AnalysisSummary {
  id: string;
  repo: string;
  number: number;
  title: string;
  riskScore: number; // 1..5
}
