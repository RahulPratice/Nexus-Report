/**
 * NexusReport Cypress Plugin
 * Add to cypress.config.ts and cypress/support/e2e.ts
 *
 * Usage:
 *   // cypress.config.ts
 *   import { defineConfig } from 'cypress';
 *   import { nexusPlugin } from '@nexusreport/cypress-plugin';
 *
 *   export default defineConfig({
 *     e2e: {
 *       setupNodeEvents(on, config) {
 *         nexusPlugin(on, config, {
 *           serverUrl: 'http://localhost:8000',
 *           apiKey: 'your-api-key',
 *           projectId: 'your-project-id',
 *         });
 *         return config;
 *       },
 *     },
 *   });
 */

export interface NexusCypressOptions {
  serverUrl: string;
  apiKey: string;
  projectId: string;
  environment?: string;
}

interface CypressTestResult {
  title: string[];
  state: string;
  duration: number;
  err?: { message: string; stack?: string };
  attempts: number;
}

interface CypressRunResult {
  stats: {
    startedAt: string;
    duration: number;
    tests: number;
    passes: number;
    failures: number;
    pending: number;
  };
  tests: CypressTestResult[];
  spec: { relative: string };
}

export function nexusPlugin(
  on: Cypress.PluginEvents,
  config: Cypress.PluginConfigOptions,
  options: NexusCypressOptions,
): void {
  const allResults: Record<string, unknown>[] = [];
  let globalStats = { start: '', duration: 0 };

  on('after:run', async (results: { runs: CypressRunResult[] }) => {
    const runs = results.runs || [];

    for (const run of runs) {
      if (!globalStats.start) {
        globalStats.start = run.stats.startedAt;
      }
      globalStats.duration += run.stats.duration;

      for (const test of run.tests || []) {
        allResults.push({
          title: test.title.join(' > '),
          file: run.spec.relative,
          state: test.state,
          duration: test.duration,
          attempts: test.attempts,
          err: test.err,
        });
      }
    }

    const payload = {
      tool: 'cypress',
      _nexus_project_id: options.projectId,
      _nexus_env: options.environment,
      _nexus_branch: process.env.GITHUB_REF_NAME || process.env.CI_COMMIT_REF_NAME || '',
      _nexus_commit: process.env.GITHUB_SHA || process.env.CI_COMMIT_SHA || '',
      stats: {
        start: globalStats.start,
        duration: globalStats.duration,
      },
      results: buildMochawesomeShape(allResults),
    };

    try {
      const res = await fetch(`${options.serverUrl}/api/v1/ingest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': options.apiKey,
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      console.log(`[NexusReport] ✅ Run ingested: ${data.run_id}`);
    } catch (e) {
      console.error('[NexusReport] Failed to ingest:', e);
    }
  });
}

function buildMochawesomeShape(
  tests: Record<string, unknown>[],
): Record<string, unknown>[] {
  const suiteMap: Record<string, Record<string, unknown>[]> = {};
  for (const t of tests) {
    const file = (t.file as string) || 'unknown';
    if (!suiteMap[file]) suiteMap[file] = [];
    suiteMap[file].push(t);
  }
  return Object.entries(suiteMap).map(([file, suiteTests]) => ({
    title: file.split('/').pop() || file,
    file,
    tests: suiteTests.map((t) => ({
      title: t.title,
      state: t.state,
      duration: t.duration,
      err: t.err,
      attempts: t.attempts,
    })),
  }));
}
