import { lazy, Suspense } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { StatCard } from '@/components/cards/StatCard';
import { useAuditLog } from '@/api/audit';
import { useStats, useRiskDistribution } from '@/api/stats';
import { Package, Clock, CheckCircle, AlertTriangle, Gauge } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

const RiskDistributionChart = lazy(() =>
  import('@/components/charts/RiskDistributionChart').then((module) => ({
    default: module.RiskDistributionChart,
  }))
);

const activityTypeClasses: Record<string, string> = {
  create: 'bg-green-100 text-green-800',
  update: 'bg-blue-100 text-blue-800',
  approve: 'bg-emerald-100 text-emerald-800',
  reject: 'bg-red-100 text-red-800',
  scan: 'bg-purple-100 text-purple-800',
  test: 'bg-amber-100 text-amber-800',
  block: 'bg-gray-100 text-gray-800',
  import: 'bg-indigo-100 text-indigo-800',
};

function formatActivityTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function summarizeActivityDetails(details: Record<string, unknown> | null) {
  if (!details || typeof details !== 'object') {
    return 'No extra details';
  }

  const reason = details.reason;
  if (typeof reason === 'string' && reason.trim()) {
    return reason.trim();
  }

  const entries = Object.entries(details).filter(([, value]) => {
    return value !== null && value !== undefined && value !== '';
  });

  if (entries.length === 0) {
    return 'No extra details';
  }

  const preview = entries
    .slice(0, 2)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ');

  return preview.length > 96 ? `${preview.slice(0, 93)}...` : preview;
}

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: riskDist, isLoading: riskLoading } = useRiskDistribution();
  const { data: auditLog, isLoading: auditLoading } = useAuditLog({
    page: 1,
    page_size: 5,
  });

  const recentActivities = auditLog?.items ?? [];

  if (statsLoading || riskLoading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <StatCard title="Total Skills" value={stats?.total_skills ?? 0} icon={Package} />
        <StatCard title="Pending Review" value={stats?.pending_count ?? 0} icon={Clock} variant="warning" />
        <StatCard title="Approved" value={stats?.approved_count ?? 0} icon={CheckCircle} variant="success" />
        <StatCard title="High Risk" value={stats?.high_risk_count ?? 0} icon={AlertTriangle} variant="danger" />
        <StatCard
          title="Average Fidelity"
          value={`${Math.round((stats?.avg_fidelity_score ?? 0) * 100)}%`}
          icon={Gauge}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {riskDist && (
              <Suspense
                fallback={
                  <div className="flex h-[250px] items-center justify-center text-sm text-muted-foreground">
                    Loading chart...
                  </div>
                }
              >
                <RiskDistributionChart data={riskDist} />
              </Suspense>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>Recent Activity</CardTitle>
            <Link
              to="/audit"
              className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-900"
            >
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {auditLoading ? (
              <div className="flex h-[250px] items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-slate-900" />
              </div>
            ) : recentActivities.length === 0 ? (
              <div className="flex h-[250px] items-center justify-center text-sm text-muted-foreground">
                No recent audit activity yet.
              </div>
            ) : (
              <div className="space-y-2">
                {recentActivities.map((event) => (
                  <div
                    key={event.event_id}
                    className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2"
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          className={
                            activityTypeClasses[event.event_type] ??
                            'bg-slate-100 text-slate-700'
                          }
                        >
                          {event.event_type}
                        </Badge>
                        {event.skill_id ? (
                          <Link
                            to={`/skills/${event.skill_id}`}
                            className="truncate text-sm font-medium text-slate-900 transition-colors hover:text-slate-600"
                          >
                            {event.skill_name || event.skill_id}
                          </Link>
                        ) : (
                          <span className="truncate text-sm font-medium text-slate-900">
                            {event.skill_name || 'System event'}
                          </span>
                        )}
                      </div>
                      <p className="truncate text-xs text-muted-foreground">
                        {event.actor} · {summarizeActivityDetails(event.details)}
                      </p>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {formatActivityTime(event.timestamp)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
