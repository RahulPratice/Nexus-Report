export type TestStatus = 'passed' | 'failed' | 'skipped' | 'flaky' | 'pending' | 'broken';
export type ErrorCategory =
  | 'assertion_failure'
  | 'timeout'
  | 'network_error'
  | 'element_not_found'
  | 'auth_failure'
  | 'data_issue'
  | 'environment_issue'
  | 'flaky_race_condition'
  | 'unknown';

export interface AIAnalysis {
  category: ErrorCategory;
  confidence: number;
  root_cause: string;
  suggested_fix: string;
  is_likely_flaky: boolean;
}

export interface TestStep {
  name: string;
  status: TestStatus;
  duration_ms: number;
  error?: string;
  screenshot_url?: string;
}

export interface TestResult {
  id: string;
  name: string;
  suite: string;
  file_path?: string;
  status: TestStatus;
  duration_ms: number;
  started_at?: string;
  error_message?: string;
  stack_trace?: string;
  ai_category?: ErrorCategory;
  ai_root_cause?: string;
  ai_fix?: string;
  ai_confidence?: number;
  flaky_score?: number;
  retry_count: number;
  browser?: string;
  platform?: string;
  device?: string;
  screenshot_url?: string;
  video_url?: string;
  trace_url?: string;
  tags: string[];
  steps: TestStep[];
}

export interface Run {
  id: string;
  project_id: string;
  tool: string;
  branch?: string;
  commit_sha?: string;
  environment?: string;
  ci_run_url?: string;
  started_at: string;
  finished_at?: string;
  duration_ms: number;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  flaky: number;
  pass_rate: number;
}

export interface Project {
  id: string;
  name: string;
  slug: string;
  description?: string;
  repo_url?: string;
  created_at: string;
}

export interface PassRateTrend {
  date: string;
  pass_rate: number;
  tool: string;
  branch: string;
  failed: number;
  total: number;
}

export interface FlakyTest {
  name: string;
  suite: string;
  flaky_score: number;
  run_count: number;
  label: 'very flaky' | 'flaky' | 'unstable' | 'stable';
}

export interface ErrorBreakdown {
  category: ErrorCategory;
  count: number;
}

export interface MultiProjectSummary {
  project_id: string;
  avg_pass_rate: number;
  run_count: number;
  total_failures: number;
}
