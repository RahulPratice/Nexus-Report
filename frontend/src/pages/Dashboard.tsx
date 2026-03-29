import { useState } from 'react';
import { useRuns } from '../hooks/useAnalytics';
import { useProjectFeed } from '../hooks/useLiveRun';
import { formatDistanceToNow } from 'date-fns';
import { CheckCircle, XCircle, Clock, Zap, Activity } from 'lucide-react';
import type { Run } from '../types';

const STATUS_COLOR: Record<string, string> = {
  passing: 'text-green-500',
  failing: 'text-red-500',
  mixed:   'text-amber-500',
};

function RunStatusIcon({ run }: { run: Run }) {
  if (run.failed === 0) return <CheckCircle className="text-green-500 w-5 h-5" />;
  if (run.passed === 0) return <XCircle className="text-red-500 w-5 h-5" />;
  return <Activity className="text-amber-500 w-5 h-5" />;
}

function PassRateBadge({ rate }: { rate: number }) {
  const color =
    rate >= 90 ? 'bg-green-100 text-green-800' :
    rate >= 70 ? 'bg-amber-100 text-amber-800' :
                 'bg-red-100 text-red-800';
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>
      {rate.toFixed(1)}%
    </span>
  );
}

export default function Dashboard() {
  const projectId = 'YOUR_PROJECT_ID'; // wire to route param / store
  const [selectedTool, setSelectedTool] = useState<string>('');
  const { data: runs = [], isLoading } = useRuns(projectId, { tool: selectedTool || undefined });
  const { latestEvent, connected } = useProjectFeed(projectId);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Test Runs</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {connected
              ? <span className="flex items-center gap-1"><span className="w-2 h-2 bg-green-400 rounded-full inline-block animate-pulse"/> Live</span>
              : 'Connecting…'}
          </p>
        </div>
        <div className="flex gap-2">
          {['', 'playwright', 'cypress', 'jest', 'k6', 'postman'].map((tool) => (
            <button
              key={tool}
              onClick={() => setSelectedTool(tool)}
              className={`px-3 py-1.5 rounded-lg text-sm border transition-colors
                ${selectedTool === tool
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'}`}
            >
              {tool || 'All tools'}
            </button>
          ))}
        </div>
      </div>

      {/* Live event banner */}
      {latestEvent && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4 flex items-center gap-3">
          <Zap className="text-indigo-500 w-5 h-5 flex-shrink-0" />
          <span className="text-sm text-indigo-700">
            New run completed — {latestEvent.passed} passed, {latestEvent.failed} failed
            ({latestEvent.pass_rate?.toFixed(1)}%)
          </span>
        </div>
      )}

      {/* Run list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {runs.map((run: Run) => (
            <a
              key={run.id}
              href={`/runs/${run.id}`}
              className="flex items-center gap-4 p-4 hover:bg-gray-50 transition-colors"
            >
              <RunStatusIcon run={run} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-gray-900 text-sm">
                    {run.branch || 'main'}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">
                    {run.commit_sha}
                  </span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                    {run.tool}
                  </span>
                  {run.environment && (
                    <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded">
                      {run.environment}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>{run.total} tests</span>
                  <span className="text-green-600">{run.passed} passed</span>
                  {run.failed > 0 && (
                    <span className="text-red-600">{run.failed} failed</span>
                  )}
                  <Clock className="w-3 h-3" />
                  <span>{(run.duration_ms / 1000).toFixed(1)}s</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <PassRateBadge rate={run.pass_rate} />
                <span className="text-xs text-gray-400">
                  {formatDistanceToNow(new Date(run.started_at), { addSuffix: true })}
                </span>
              </div>
            </a>
          ))}
          {runs.length === 0 && (
            <div className="p-12 text-center text-gray-400">
              No runs yet. Integrate NexusReport with your test suite to get started.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
