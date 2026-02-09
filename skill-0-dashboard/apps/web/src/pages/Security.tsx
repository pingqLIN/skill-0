import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useFindingsByRule } from '@/api/stats';
import { useScans } from '@/api/scans';

const MAX_FINDINGS = 8;
const MAX_SCANS = 10;

function formatDate(value?: string) {
  if (!value) return 'Unknown';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function Security() {
  const { data: findings, isLoading: findingsLoading } = useFindingsByRule();
  const { data: scans, isLoading: scansLoading } = useScans();

  const isLoading = findingsLoading || scansLoading;
  const topFindings = findings?.slice(0, MAX_FINDINGS) || [];
  const recentScans = scans?.slice(0, MAX_SCANS) || [];

  if (isLoading) {
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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Security</h1>
        <Link
          to="/skills"
          className="text-sm text-slate-600 hover:text-slate-900 transition-colors"
        >
          Back to Skills
        </Link>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Findings by Rule</CardTitle>
          </CardHeader>
          <CardContent>
            {topFindings.length === 0 ? (
              <p className="text-muted-foreground">No findings available.</p>
            ) : (
              <div className="space-y-3">
                {topFindings.map((finding) => (
                  <div
                    key={`${finding.rule_id}-${finding.rule_name}`}
                    className="flex flex-col gap-1 rounded-md border border-slate-200 p-3"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="font-medium text-slate-900">
                        {finding.rule_name || finding.rule_id}
                      </div>
                      <div className="text-sm text-slate-600">
                        {finding.count} findings
                      </div>
                    </div>
                    <div className="text-sm text-slate-600">
                      {finding.rule_id} · {finding.severity}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Scans</CardTitle>
          </CardHeader>
          <CardContent>
            {recentScans.length === 0 ? (
              <p className="text-muted-foreground">No scan history yet.</p>
            ) : (
              <div className="space-y-3">
                {recentScans.map((scan) => (
                  <div
                    key={scan.scan_id}
                    className="flex flex-col gap-1 rounded-md border border-slate-200 p-3"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div className="font-medium text-slate-900">
                        {scan.skill_name}
                      </div>
                      <div className="text-sm text-slate-600">
                        {scan.findings_count} findings
                      </div>
                    </div>
                    <div className="text-sm text-slate-600">
                      Risk: {scan.risk_level} · Score: {scan.risk_score} · {formatDate(scan.scanned_at)}
                    </div>
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
