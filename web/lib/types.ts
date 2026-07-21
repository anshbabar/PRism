// Shared types mirroring the backend JSON (snake_case, matched exactly so no
// field remapping is needed). See app/api/routes_analyses.py and app/ai/schema.py.

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export type RiskBand = "low" | "medium" | "high";

export interface RiskSignal {
  category: string;
  severity: number;
  file_path: string | null;
  detail: string;
}

export interface RiskResult {
  score: number; // 1..5
  band: RiskBand;
  signals: RiskSignal[];
  rationale: string;
}

export interface TopConcern {
  title: string;
  detail: string;
}

export interface SuggestedTest {
  area: string;
  reason: string;
}

export interface AIReview {
  summary: string;
  risk_score: number; // 1..5, clamped
  risk_categories: string[];
  top_concerns: TopConcern[];
  suggested_tests: SuggestedTest[];
  regression_risks: string[];
  github_review_markdown: string;
}

export interface ChangedFile {
  path: string;
  status: string;
  additions: number;
  deletions: number;
}

export interface SimilarPR {
  analysis_id: string;
  repository: string;
  number: number;
  title: string;
  risk_score: number;
  risk_band: RiskBand;
  similarity: number; // 0..1
  summary: string;
}

export interface AnalysisSummary {
  analysis_id: string;
  repository: string;
  number: number;
  title: string;
  author: string;
  status: string;
  deterministic_score: number;
  final_score: number;
  risk_band: RiskBand;
  top_concern: string | null;
  files_changed: number;
  created_at: string;
}

export interface AnalysisDetail {
  analysis_id: string;
  repository: string;
  number: number;
  title: string;
  author: string;
  url: string;
  description: string;
  status: string;
  provider: string;
  model: string;
  prompt_version: string;
  deterministic_score: number;
  final_score: number;
  risk_band: RiskBand;
  created_at: string;
  risk: RiskResult;
  review: AIReview;
  changed_files: ChangedFile[];
  similar: SimilarPR[];
}

export interface EvalMetrics {
  valid_json_rate: number;
  risk_score_accuracy_within_1: number;
  risk_category_precision: number;
  risk_category_recall: number;
  suggested_test_overlap: number;
  average_latency_ms: number;
}

export interface EvalFixtureRow {
  name: string;
  expected_band: string;
  expected_score: number;
  predicted_score: number;
  score_within_1: boolean;
  category_tp: number;
  category_fp: number;
  category_fn: number;
  test_overlap: number | null;
  latency_ms: number;
}

export interface EvalResult {
  generated_at: string;
  provider: string;
  model: string;
  prompt_version: string;
  fixture_count: number;
  metrics: EvalMetrics;
  fixtures: EvalFixtureRow[];
}
