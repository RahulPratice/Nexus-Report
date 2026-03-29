/**
 * NexusReport Jest Reporter
 *
 * Usage in jest.config.ts:
 *   reporters: [
 *     'default',
 *     ['@nexusreport/jest-reporter', {
 *       serverUrl: 'http://localhost:8000',
 *       apiKey: 'your-api-key',
 *       projectId: 'your-project-id',
 *     }]
 *   ]
 */
import type {
  Reporter,
  Context,
  Test,
  TestResult,
  AggregatedResult,
} from '@jest/reporters';

interface NexusJestOptions {
  serverUrl: string;
  apiKey: string;
  projectId: string;
  environment?: string;
}

class NexusJestReporter implements Reporter {
  private options: NexusJestOptions;

  constructor(_globalConfig: unknown, options: NexusJestOptions) {
    this.options = options;
  }

  onRunComplete(_contexts: Set<Context>, results: AggregatedResult): void {
    this.sendResults(results).catch((e) =>
      console.error('[NexusReport] Failed to send results:', e)
    );
  }

  private async sendResults(results: AggregatedResult): Promise<void> {
    const payload = {
      tool: 'jest',
      _nexus_project_id: this.options.projectId,
      _nexus_env: this.options.environment,
      _nexus_branch: process.env.GITHUB_REF_NAME || '',
      _nexus_commit: process.env.GITHUB_SHA || '',
      startTime: results.startTime,
      testResults: results.testResults.map((suite: TestResult) => ({
        testFilePath: suite.testFilePath,
        perfStats: suite.perfStats,
        testResults: suite.testResults.map((t) => ({
          title: t.title,
          ancestorTitles: t.ancestorTitles,
          status: t.status,
          duration: t.duration,
          failureMessages: t.failureMessages,
        })),
      })),
    };

    const res = await fetch(`${this.options.serverUrl}/api/v1/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.options.apiKey,
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    console.log(`\n[NexusReport] ✅ Run ingested: ${data.run_id}`);
    console.log(`[NexusReport] 🔗 ${this.options.serverUrl}/runs/${data.run_id}\n`);
  }

  getLastError(): Error | undefined {
    return undefined;
  }
}

export default NexusJestReporter;
