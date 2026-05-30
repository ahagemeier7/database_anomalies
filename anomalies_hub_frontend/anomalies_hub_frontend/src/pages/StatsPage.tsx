import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3, Bell, Clock, ShieldCheck, AlertTriangle, Target,
} from 'lucide-react';
import { fraudService } from '../services/services';
import type { DashboardStats, TableStats } from '../types/types';
import { Card, PageHeader, Skeleton, SkeletonCard, ErrorBanner, EmptyState } from '../components/ui';

function HistoryChart({ data }: { data: { date: string; frauds: number; false_positives: number }[] }) {
  if (!data.length) {
    return (
      <EmptyState
        icon={BarChart3}
        title="No chart data yet"
        description="Data will appear as anomalies are detected and reviewed."
      />
    );
  }

  const maxVal = Math.max(...data.map(d => Math.max(d.frauds, d.false_positives)), 1);
  const barWidth = 20;
  const gap = 12;
  const groupWidth = barWidth * 2 + gap;
  const chartHeight = 200;
  const chartWidth = Math.max(data.length * (groupWidth + 24) + 40, 200);

  return (
    <svg width="100%" viewBox={`0 0 ${chartWidth} 260`} className="w-full">
      {/* Y axis grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
        const y = 40 + chartHeight * (1 - ratio);
        return (
          <g key={ratio}>
            <line x1={50} y1={y} x2={chartWidth} y2={y} stroke="#f1f5f9" strokeDasharray={ratio === 0 ? 'none' : '4 3'} />
            <text x={46} y={y + 4} textAnchor="end" fontSize={11} fill="#94a3b8">
              {Math.round(maxVal * ratio)}
            </text>
          </g>
        );
      })}

      {/* Bars */}
      {data.map((d, i) => {
        const x = 60 + i * (groupWidth + 24);
        const fraudsH = (d.frauds / maxVal) * chartHeight;
        const falsePosH = (d.false_positives / maxVal) * chartHeight;
        const labelX = x + groupWidth / 2;

        return (
          <g key={d.date}>
            {/* Fraud bar */}
            <rect x={x} y={40 + chartHeight - fraudsH} width={barWidth} height={fraudsH} rx={3} fill="#6366f1" />
            {/* False positive bar */}
            <rect x={x + barWidth + gap} y={40 + chartHeight - falsePosH} width={barWidth} height={falsePosH} rx={3} fill="#f59e0b" />
            {/* Value labels */}
            <text x={x + barWidth / 2} y={35 + chartHeight - fraudsH} textAnchor="middle" fontSize={10} fill="#6366f1">
              {d.frauds > 0 ? d.frauds : ''}
            </text>
            <text x={x + barWidth + gap + barWidth / 2} y={35 + chartHeight - falsePosH} textAnchor="middle" fontSize={10} fill="#d97706">
              {d.false_positives > 0 ? d.false_positives : ''}
            </text>
            {/* Date label */}
            <text x={labelX} y={260} textAnchor="middle" fontSize={11} fill="#64748b">
              {new Date(d.date + 'T00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </text>
          </g>
        );
      })}

      {/* Legend */}
      <rect x={chartWidth / 2 - 80} y={12} width={10} height={10} rx={2} fill="#6366f1" />
      <text x={chartWidth / 2 - 66} y={21} fontSize={11} fill="#64748b">Frauds</text>
      <rect x={chartWidth / 2} y={12} width={10} height={10} rx={2} fill="#f59e0b" />
      <text x={chartWidth / 2 + 14} y={21} fontSize={11} fill="#64748b">False Positives</text>
    </svg>
  );
}

export default function StatsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [tableStats, setTableStats] = useState<TableStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchStats = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      fraudService.getStats(),
      fraudService.getStatsByTable(),
    ])
      .then(([global, byTable]) => {
        setStats(global);
        setTableStats(byTable);
      })
      .catch(() => setError('Failed to load statistics. Is the backend running?'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchStats(); }, []);

  const summaryCards = stats ? [
    { label: 'Total Alerts', value: stats.total_alerts, icon: Bell, color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'Pending', value: stats.pending_reviews, icon: Clock, color: 'text-amber-600', bg: 'bg-amber-50' },
    { label: 'Confirmed Frauds', value: stats.confirmed_frauds, icon: ShieldCheck, color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'False Positives', value: stats.false_positives, icon: AlertTriangle, color: 'text-red-600', bg: 'bg-red-50' },
    { label: 'Precision', value: `${stats.model_metrics.precision}%`, icon: Target, color: 'text-blue-600', bg: 'bg-blue-50' },
  ] : [];

  return (
    <div>
      <PageHeader
        title="Statistics"
        subtitle="Model performance overview and per-table precision"
      />

      {loading && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
            {[...Array(5)].map((_, i) => <SkeletonCard key={i} />)}
          </div>
          <Card><Skeleton className="h-64 w-full" /></Card>
          <div className="mt-8 space-y-4">
            {[...Array(3)].map((_, i) => <Skeleton className="h-12 w-full" key={i} />)}
          </div>
        </>
      )}

      {error && <ErrorBanner message={error} onRetry={fetchStats} />}

      {!loading && !error && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
            {summaryCards.map(card => {
              const Icon = card.icon;
              return (
                <Card key={card.label}>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${card.bg}`}>
                      <Icon className={`h-5 w-5 ${card.color}`} />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">{card.label}</p>
                      <p className="text-xl font-bold text-gray-900">{card.value}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* History Chart */}
          <Card title="Last 7 Days — Frauds vs False Positives">
            <HistoryChart data={stats?.history_chart ?? []} />
          </Card>

          {/* Per-Table Breakdown */}
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Precision by Table</h3>

            {tableStats.length === 0 ? (
              <EmptyState
                icon={BarChart3}
                title="No table data yet"
                description="Anomaly data grouped by table will appear here."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 font-medium text-gray-500">Table</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Total</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Confirmed</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">False Pos.</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Pending</th>
                      <th className="text-right py-3 px-4 font-medium text-gray-500">Precision</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableStats.map(row => (
                      <tr
                        key={row.origin_table}
                        className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                        onClick={() => navigate(`/revisions/${row.origin_table}`)}
                      >
                        <td className="py-3 px-4 font-medium text-gray-900">{row.origin_table}</td>
                        <td className="py-3 px-4 text-right text-gray-600">{row.total_alerts}</td>
                        <td className="py-3 px-4 text-right text-emerald-600">{row.confirmed_frauds}</td>
                        <td className="py-3 px-4 text-right text-red-500">{row.false_positives}</td>
                        <td className="py-3 px-4 text-right text-amber-600">{row.pending_reviews}</td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  row.precision >= 80 ? 'bg-emerald-500' : row.precision >= 50 ? 'bg-amber-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${Math.min(row.precision, 100)}%` }}
                              />
                            </div>
                            <span className={`font-semibold w-12 text-right ${
                              row.precision >= 80 ? 'text-emerald-600' : row.precision >= 50 ? 'text-amber-600' : 'text-red-600'
                            }`}>
                              {row.precision}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
