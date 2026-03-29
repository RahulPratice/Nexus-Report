import type {
  Reporter,
  FullConfig,
  Suite,
  TestCase,
  TestResult,
  FullResult,
} from '@playwright/test/reporter';

export interface NexusReporterOptions {
  serverUrl: string;
  apiKey: string;
  projectId: string;
  environment?: string;
}

class NexusReporter implements Reporter {
  private options: NexusReporterOptions;
  private startTime: number = 0;
  private results: Record<string, unknown>[] = [];
  private suites: Record<string, unknown>[] = [];

  constructor(options: NexusReporterOptions) {
    this.options = options;
  }

  onBegin(config: FullConfig, suite: Suite): void {
    this.startTime = Date.now();
    console.log(`[NexusReport] Starting run for project ${this.options.projectId}`);
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    const lastResult = result;
    this.results.push({
      title: test.title,
      file: test.location.file,
      line: test.location.line,
      status: result.status,
      duration: result.duration,
      retry: result.retry,
      error: result.error
        ? { message: result.error.message, stack: result.error.stack }
        : undefined,
      steps: result.steps.map((s) => ({
        title: s.title,
        duration: s.duration,
        error: s.error?.message,
      })),
      attachments: result.attachments.map((a) => ({
        name: a.name,
        contentType: a.contentType,
        path: a.path,
      })),
    });
  }

  async onEnd(result: FullResult): Promise<void> {
    const payload = {
      tool: 'playwright',
      _nexus_project_id: this.options.projectId,
      _nexus_env: this.options.environment,
      _nexus_branch: process.env.GITHUB_REF_NAME || process.env.CI_COMMIT_REF_NAME || '',
      _nexus_commit: process.env.GITHUB_SHA || process.env.CI_COMMIT_SHA || '',
      _nexus_ci: this.detectCI(),
      _nexus_ci_url: process.env.GITHUB_SERVER_URL
        ? `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}/actions/runs/${process.env.GITHUB_RUN_ID}`
        : undefined,
      startTime: this.startTime,
      stats: { duration: Date.now() - this.startTime },
      suites: this.buildSuites(),
    };

    try {
      const response = await fetch(`${this.options.serverUrl}/api/v1/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.options.apiKey,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        console.error(`[NexusReport] Failed to ingest: ${response.status} ${response.statusText}`);
        return;
      }

      const data = await response.json();
      console.log(`[NexusReport] ✅ Run ingested: ${data.run_id}`);
      console.log(`[NexusReport] 📊 ${data.passed} passed, ${data.failed} failed (${data.pass_rate?.toFixed(1)}%)`);
      console.log(`[NexusReport] 🔗 ${this.options.serverUrl}/runs/${data.run_id}`);
    } catch (error) {
      console.error('[NexusReport] Network error during ingest:', error);
    }
  }

  private buildSuites(): Record<string, unknown>[] {
    // Group results by file/suite
    const suiteMap: Record<string, Record<string, unknown>[]> = {};
    for (const r of this.results) {
      const key = (r.file as string) || 'unknown';
      if (!suiteMap[key]) suiteMap[key] = [];
      suiteMap[key].push(r);
    }
    return Object.entries(suiteMap).map(([file, specs]) => ({
      title: file.split('/').pop() || file,
      file,
      specs: specs.map((s) => ({
        title: s.title,
        file: s.file,
        tests: [{ status: s.status, duration: s.duration, results: [s] }],
      })),
    }));
  }

  private detectCI(): string {
    if (process.env.GITHUB_ACTIONS) return 'github_actions';
    if (process.env.GITLAB_CI)    return 'gitlab_ci';
    if (process.env.CIRCLECI)     return 'circleci';
    if (process.env.JENKINS_URL)  return 'jenkins';
    return 'unknown';
  }
}

export default NexusReporter;
