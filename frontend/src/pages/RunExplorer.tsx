import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useRunResults } from '../hooks/useAnalytics';
import { Brain, AlertTriangle, Clock, RefreshCw, ChevronDown, ChevronRight, Video, Image } from 'lucide-react';
import type { TestResult, TestStatus } from '../types';

const STATUS_STYLES: Record<TestStatus, string> = {
  passed:  'bg-green-50  text-green-700  border-green-200',
  failed:  'bg-red-50    text-red-700    border-red-200',
  skipped: 'bg-gray-50   text-gray-500   border-gray-200',
  flaky:   'bg-amber-50  text-amber-700  border-amber-200',
  pending: 'bg-gray-50   text-gray-500   border-gray-200',
  broken:  'bg-purple-50 text-purple-700 border-purple-200',
};

const CATEGORY_ICON: Record<string, string> = {
  assertion_failure:   '🔴',
  timeout:             '⏱️',
  network_error:       '🌐',
  element_not_found:   '🔍',
  auth_failure:        '🔐',
  data_issue:          '📦',
  environment_issue:   '⚙️',
  flaky_race_condition:'🎲',
  unknown:             '❓',
};

function FlakyScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.7 ? 'bg-red-500' : score >= 0.4 ? 'bg-amber-400' : score >= 0.2 ? 'bg-yellow-300' : 'bg-green-400';
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500">{pct}%</span>
    </div>
  );
}

function AIPanel({ test }: { test: TestResult }) {
  if (!test.ai_category && !test.ai_root_cause) return null;
  return (
    <div className="mt-3 bg-indigo-50 border border-indigo-100 rounded-lg p-3 space-y-2">
      <div className="flex items-center gap-2 text-indigo-700 text-xs font-medium">
        <Brain className="w-3.5 h-3.5" />
        AI Analysis
        {test.ai_confidence && (
          <span className="ml-auto text-indigo-400">{Math.round((test.ai_confidence || 0) * 100)}% confident</span>
        )}
      </div>
      <div className="flex items-center gap-2 text-sm text-gray-700">
        <span>{CATEGORY_ICON[test.ai_category || 'unknown']}</span>
        <span className="font-medium capitalize">{test.ai_category?.replace(/_/g, ' ')}</span>
      </div>
      {test.ai_root_cause && (
        <p className="text-xs text-gray-600">{test.ai_root_cause}</p>
      )}
      {test.ai_fix && (
        <div className="text-xs text-gray-700 bg-white border border-indigo-100 rounded p-2 mt-1 whitespace-pre-line">
          <span className="font-medium text-indigo-600">Suggested fix:</span>
          {'\n'}{test.ai_fix}
        </div>
      )}
    </div>
  );
}

function TestCard({ test }: { test: TestResult }) {
  const [expanded, setExpanded] = useState(false);
  const isFailed = test.status === 'failed' || test.status === 'broken';

  return (
    <div className={`border rounded-xl overflow-hidden ${STATUS_STYLES[test.status]}`}>
      <button
        className="w-full flex items-center gap-3 p-3 text-left"
        onClick={() => setExpanded(!expanded)}
      >
        {expanded ? <ChevronDown className="w-4 h-4 flex-shrink-0" /> : <ChevronRight className="w-4 h-4 flex-shrink-0" />}
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{test.name}</div>
          <div className="text-xs opacity-60 truncate">{test.suite}</div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          {test.flaky_score != null && test.flaky_score > 0.2 && (
            <FlakyScoreBar score={test.flaky_score} />
          )}
          {test.retry_count > 0 && (
            <span className="flex items-center gap-1 text-xs">
              <RefreshCw className="w-3 h-3" />
              {test.retry_count}x
            </span>
          )}
          <Clock className="w-3 h-3 opacity-50" />
          <span className="text-xs">{(test.duration_ms / 1000).toFixed(2)}s</span>
          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_STYLES[test.status]}`}>
            {test.status}
          </span>
        </div>
      </button>

      {expanded && (
        <div className="border-t border-current border-opacity-10 p-3 space-y-3">
          {isFailed && <AIPanel test={test} />}

          {test.error_message && (
            <div>
              <div className="text-xs font-medium text-red-700 mb-1 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Error
              </div>
              <pre className="text-xs bg-white rounded p-2 overflow-x-auto text-red-900 border border-red-100">
                {test.error_message}
              </pre>
            </div>
          )}

          {test.stack_trace && (
            <details>
              <summary className="text-xs text-gray-500 cursor-pointer">Stack trace</summary>
              <pre className="text-xs bg-white rounded p-2 overflow-x-auto text-gray-700 mt-1 border border-gray-100">
                {test.stack_trace}
              </pre>
            </details>
          )}

          <div className="flex gap-2">
            {test.screenshot_url && (
              <a href={test.screenshot_url} target="_blank" rel="noreferrer"
                 className="flex items-center gap-1 text-xs text-blue-600 hover:underline">
                <Image className="w-3 h-3" /> Screenshot
              </a>
            )}
            {test.video_url && (
              <a href={test.video_url} target="_blank" rel="noreferrer"
                 className="flex items-center gap-1 text-xs text-blue-600 hover:underline">
                <Video className="w-3 h-3" /> Video
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RunExplorer() {
  const { runId = '' } = useParams<{ runId: string }>();
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const { data: results = [], isLoading } = useRunResults(runId, {
    status: statusFilter || undefined,
    search: search || undefined,
  });

  const counts = results.reduce((acc: Record<string, number>, t: TestResult) => {
    acc[t.status] = (acc[t.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search tests…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-48 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 ring-indigo-300 outline-none"
        />
        {(['', 'failed', 'passed', 'skipped', 'flaky'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              statusFilter === s
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'
            }`}
          >
            {s || 'All'} {s && counts[s] != null ? `(${counts[s]})` : ''}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {isLoading
          ? Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-12 bg-gray-100 rounded-xl animate-pulse" />
            ))
          : results.map((test: TestResult) => (
              <TestCard key={test.id} test={test} />
            ))
        }
      </div>
    </div>
  );
}
