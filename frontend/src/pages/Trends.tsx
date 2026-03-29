import { useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { usePassRateTrend, useFlakyTests, useErrorBreakdown } from '../hooks/useAnalytics';
import { format } from 'date-fns';
import { TrendingUp, AlertTriangle, Zap } from 'lucide-react';

const CATEGORY_COLORS: Record<string, string> = {
  assertion_failure:    '#ef4444',
  timeout:              '#f97316',
  network_error:        '#3b82f6',
  element_not_found:    '#8b5cf6',
  auth_failure:         '#ec4899',
  data_issue:           '#f59e0b',
  environment_issue:    '#6b7280',
  flaky_race_condition: '#14b8a6',
  unknown:              '#d1d5db',
};

const FLAKY_COLORS: Record<string, string> = {
  'very flaky': '#ef4444',
  'flaky':      '#f97316',
  'unstable':   '#f59e0b',
  'stable':     '#22c55e',
};

function SectionTitle({ icon: Icon, title }: { icon: React.FC<{ className?: string }>, title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon className="w-5 h-5 text-indigo-500" />
      <h2 className="text-base font-semibold text-gray-800">{title}</h2>
    </div>
  );
}

export default function Trends() {
  const projectId = 'YOUR_PROJECT_ID';
  const [days, setDays] = useState(30);

  const { data: trend = [] }   = usePassRateTrend(projectId, days);
  const { data: flaky = [] }   = useFlakyTests(projectId);
  const { data: errors = [] }  = useErrorBreakdown(projectId, days);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-10">

      {/* Controls */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-500">Time range:</span>
        {[7, 14, 30, 90].map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              days === d
                ? 'bg-indigo-600 text-white border-indigo-600'
                : 'bg-white text-gray-600 border-gray-200 hover:border-indigo-300'
            }`}
          >
            {d}d
          </button>
        ))}
      </div>

      {/* Pass Rate Trend */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6">
        <SectionTitle icon={TrendingUp} title="Pass rate over time" />
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={trend.map(d => ({
            ...d,
            date: format(new Date(d.date), 'MMM d'),
          }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} unit="%" />
            <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
            <Line
              type="monotone"
              dataKey="pass_rate"
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              name="Pass rate"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-6">

        {/* Error Breakdown */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <SectionTitle icon={AlertTriangle} title="Failure categories" />
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={errors}
                dataKey="count"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={80}
                label={({ category, percent }) =>
                  `${category?.replace(/_/g, ' ')} ${(percent * 100).toFixed(0)}%`
                }
                labelLine={false}
              >
                {errors.map((entry) => (
                  <Cell
                    key={entry.category}
                    fill={CATEGORY_COLORS[entry.category] || '#d1d5db'}
                  />
                ))}
              </Pie>
              <Tooltip formatter={(v) => [v, 'failures']} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Flaky Tests */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6">
          <SectionTitle icon={Zap} title="Flakiest tests" />
          <div className="space-y-2 max-h-52 overflow-y-auto">
            {flaky.slice(0, 10).map((t) => (
              <div key={t.name} className="flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-gray-800 truncate">{t.name}</div>
                  <div className="text-xs text-gray-400 truncate">{t.suite}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${Math.round(t.flaky_score * 100)}%`,
                        background: FLAKY_COLORS[t.label],
                      }}
                    />
                  </div>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full font-medium"
                    style={{
                      background: FLAKY_COLORS[t.label] + '20',
                      color: FLAKY_COLORS[t.label],
                    }}
                  >
                    {t.label}
                  </span>
                </div>
              </div>
            ))}
            {flaky.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-8">
                No flaky tests detected 🎉
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
