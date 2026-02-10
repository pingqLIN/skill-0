<<<<<<< Updated upstream
<<<<<<< Updated upstream
import { PageLayout } from '@/components/layout/PageLayout';
import { StatCard } from '@/components/cards/StatCard';
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart';
import { useStats, useRiskDistribution } from '@/api/stats';
import { Package, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: riskDist, isLoading: riskLoading } = useRiskDistribution();

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Skills" value={stats?.total_skills ?? 0} icon={Package} />
        <StatCard title="Pending Review" value={stats?.pending_count ?? 0} icon={Clock} variant="warning" />
        <StatCard title="Approved" value={stats?.approved_count ?? 0} icon={CheckCircle} variant="success" />
        <StatCard title="High Risk" value={stats?.high_risk_count ?? 0} icon={AlertTriangle} variant="danger" />
      </div>
      
      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {riskDist && <RiskDistributionChart data={riskDist} />}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Activity timeline coming soon...</p>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
=======
=======
>>>>>>> Stashed changes
import { PageLayout } from '@/components/layout/PageLayout';
import { StatCard } from '@/components/cards/StatCard';
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart';
import { useStats, useRiskDistribution } from '@/api/stats';
import { Package, Clock, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useStats();
  const { data: riskDist, isLoading: riskLoading } = useRiskDistribution();

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard title="Total Skills" value={stats?.total_skills ?? 0} icon={Package} />
        <StatCard title="Pending Review" value={stats?.pending_count ?? 0} icon={Clock} variant="warning" />
        <StatCard title="Approved" value={stats?.approved_count ?? 0} icon={CheckCircle} variant="success" />
        <StatCard title="High Risk" value={stats?.high_risk_count ?? 0} icon={AlertTriangle} variant="danger" />
      </div>
      
      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {riskDist && <RiskDistributionChart data={riskDist} />}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">Activity timeline coming soon...</p>
          </CardContent>
        </Card>
      </div>
    </PageLayout>
  );
}
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
