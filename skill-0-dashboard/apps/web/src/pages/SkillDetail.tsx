import { useParams, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { PageLayout } from '@/components/layout/PageLayout';
import {
  useSkill,
  useSkillRevisions,
  useActionReadiness,
  useEnqueueScanJob,
  useEnqueueTestJob,
  useActionJob,
  useActionJobItems,
  useRetryActionJobItem,
} from '@/api/skills';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArrowLeft, Shield, TestTube, FileText, CheckCircle, XCircle, ExternalLink, Scale, Lock, User, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import type { ActionJobItem, ActionJobSummary } from '@/api/types';

const riskColors: Record<string, string> = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  medium: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900',
  blocked: 'bg-gray-100 text-gray-800',
};

const statusColors: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  blocked: 'bg-gray-100 text-gray-800',
};

const severityColors: Record<string, string> = {
  critical: 'text-red-600',
  high: 'text-orange-600',
  medium: 'text-yellow-600',
  low: 'text-green-600',
  info: 'text-blue-600',
};

const NON_RETRIABLE_ERROR_CODES = new Set([
  'PATH_NOT_FOUND',
  'SOURCE_PATH_MISSING',
  'SOURCE_PATH_NOT_ALLOWED',
  'INSTALLED_PATH_MISSING',
  'INSTALLED_PATH_NOT_ALLOWED',
]);

function formatLeaseExpiry(leaseExpiresAt: string | null) {
  return leaseExpiresAt ?? '-';
}

export function SkillDetail() {
  const { skillId } = useParams<{ skillId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: skill, isLoading, error } = useSkill(skillId || '');
  const { data: revisions } = useSkillRevisions(skillId || '');
  const { data: readiness } = useActionReadiness(skillId || '');
  const scanJobMutation = useEnqueueScanJob();
  const testJobMutation = useEnqueueTestJob();
  const retryJobItemMutation = useRetryActionJobItem();
  const [actionMessage, setActionMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [actionKind, setActionKind] = useState<'scan' | 'test' | null>(null);
  const [activeJobId, setActiveJobId] = useState('');
  const [showDetails, setShowDetails] = useState(false);
  const { data: actionJob } = useActionJob(activeJobId);
  const { data: actionJobItems = [] } = useActionJobItems(activeJobId);

  useEffect(() => {
    if (!skillId || !actionJob) {
      return;
    }

    const kindLabel = actionKind === 'test' ? 'Test' : 'Scan';
    if (actionJob.status === 'queued') {
      setActionMessage({ text: `${kindLabel} job queued`, ok: true });
      return;
    }

    if (actionJob.status === 'running') {
      const done = actionJob.summary.succeeded + actionJob.summary.failed + actionJob.summary.skipped;
      setActionMessage({
        text: `${kindLabel} job running — ${done}/${actionJob.summary.total} completed`,
        ok: true,
      });
      return;
    }

    if (actionJob.status === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['skill', skillId] });
      queryClient.invalidateQueries({ queryKey: ['skill-revisions', skillId] });
      queryClient.invalidateQueries({ queryKey: ['action-readiness', skillId] });
      if (actionKind === 'scan') {
        const riskScore = actionJobItems[0]?.result?.risk_score;
        setActionMessage({
          text: `Scan complete — risk score: ${riskScore !== undefined ? String(riskScore) : '-'}`,
          ok: true,
        });
      } else {
        const overallScore = actionJobItems[0]?.result?.overall_score;
        setActionMessage({
          text: `Test complete — score: ${typeof overallScore === 'number' ? Math.round(overallScore * 100) : 0}%`,
          ok: true,
        });
      }
      return;
    }

    if (actionJob.status === 'completed_with_failures' || actionJob.status === 'failed') {
      queryClient.invalidateQueries({ queryKey: ['skill', skillId] });
      queryClient.invalidateQueries({ queryKey: ['skill-revisions', skillId] });
      queryClient.invalidateQueries({ queryKey: ['action-readiness', skillId] });
      const failedItem = actionJobItems.find((item) => item.status === 'failed');
      setActionMessage({
        text: failedItem?.error_message ?? actionJob.error_message ?? `${kindLabel} job failed`,
        ok: false,
      });
    }
  }, [actionJob, actionJobItems, actionKind, queryClient, skillId]);

  const handleScan = async () => {
    if (!skillId) return;
    setActionMessage(null);
    setActiveJobId('');
    setShowDetails(false);
    setActionKind('scan');
    const job = await scanJobMutation.mutateAsync({ skill_ids: [skillId] }).catch((e: Error) => {
      setActionMessage({ text: e.message, ok: false });
      return null;
    });
    if (!job) return;
    setActiveJobId(job.job_id);
    setActionMessage({ text: 'Scan job queued', ok: true });
  };

  const handleTest = async () => {
    if (!skillId) return;
    setActionMessage(null);
    setActiveJobId('');
    setShowDetails(false);
    setActionKind('test');
    const job = await testJobMutation.mutateAsync({ skill_ids: [skillId] }).catch((e: Error) => {
      setActionMessage({ text: e.message, ok: false });
      return null;
    });
    if (!job) return;
    setActiveJobId(job.job_id);
    setActionMessage({ text: 'Test job queued', ok: true });
  };

  const actionJobStatusColors: Record<string, string> = {
    queued: 'bg-blue-100 text-blue-800',
    running: 'bg-indigo-100 text-indigo-800',
    completed: 'bg-green-100 text-green-800',
    completed_with_failures: 'bg-amber-100 text-amber-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-gray-100 text-gray-800',
  };

  const activeActionPending =
    scanJobMutation.isPending ||
    testJobMutation.isPending ||
    retryJobItemMutation.isPending ||
    actionJob?.status === 'queued' ||
    actionJob?.status === 'running';

  const retriableFailedItem = actionJobItems.find((item) =>
    item.status === 'failed' &&
    item.attempt_number < item.max_attempts &&
    item.error_code !== null &&
    !NON_RETRIABLE_ERROR_CODES.has(item.error_code)
  );

  const handleRetryFailedItem = async () => {
    const targetJobId = actionJob?.job_id ?? activeJobId;
    if (!targetJobId || !retriableFailedItem) {
      return;
    }

    setActionMessage(null);
    const retryJob = await retryJobItemMutation.mutateAsync({
      jobId: targetJobId,
      itemId: retriableFailedItem.item_id,
    }).catch((e: Error) => {
      setActionMessage({ text: e.message, ok: false });
      return null;
    });

    if (!retryJob) {
      return;
    }

    setActiveJobId(retryJob.job_id);
    setActionMessage({
      text: `${actionKind === 'test' ? 'Test' : 'Scan'} retry job queued`,
      ok: true,
    });
    setShowDetails(true);
  };

  const renderActionJobRow = (item: ActionJobItem, job: ActionJobSummary) => {
    const row = item.result ?? {};
    return (
      <TableRow key={item.item_id}>
        <TableCell className="font-mono text-xs">{item.skill_id}</TableCell>
        <TableCell className="font-mono text-xs">{item.target_revision_id ?? '-'}</TableCell>
        <TableCell>
          <Badge className={actionJobStatusColors[item.status] ?? 'bg-gray-100 text-gray-800'}>
            {item.status}
          </Badge>
        </TableCell>
        <TableCell>{item.attempt_number}/{item.max_attempts}</TableCell>
        <TableCell className="font-mono text-xs">{item.claimed_by ?? '-'}</TableCell>
        <TableCell className="font-mono text-xs">{formatLeaseExpiry(item.lease_expires_at)}</TableCell>
        {job.job_type === 'scan_batch' && (
          <>
            <TableCell>
              <Badge className={riskColors[String(row.risk_level)] ?? 'bg-gray-100 text-gray-800'}>
                {String(row.risk_level ?? '-')}
              </Badge>
            </TableCell>
            <TableCell>{row.risk_score !== undefined ? String(row.risk_score) : '-'}</TableCell>
            <TableCell>{row.findings_count !== undefined ? String(row.findings_count) : '-'}</TableCell>
          </>
        )}
        {job.job_type === 'test_batch' && (
          <>
            <TableCell>{typeof row.overall_score === 'number' ? `${Math.round(row.overall_score * 100)}%` : '-'}</TableCell>
            <TableCell>
              {row.passed === true ? <CheckCircle className="h-4 w-4 text-green-600" /> : row.passed === false ? <XCircle className="h-4 w-4 text-red-600" /> : '-'}
            </TableCell>
          </>
        )}
      </TableRow>
    );
  };

  if (isLoading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </PageLayout>
    );
  }

  if (error || !skill) {
    return (
      <PageLayout>
        <div className="text-center py-12">
          <p className="text-red-500 mb-4">Failed to load skill details</p>
          <Button onClick={() => navigate('/skills')}>Back to Skills</Button>
        </div>
      </PageLayout>
    );
  }

  const revisionHistory = revisions ?? skill.revision_history ?? [];

  return (
    <PageLayout>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate('/skills')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      </div>

      {/* Action Feedback */}
      {actionMessage && (
        <div className={`mb-2 px-4 py-3 rounded-md text-sm flex items-center gap-2 ${actionMessage.ok ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {actionMessage.ok ? <CheckCircle className="h-4 w-4 shrink-0" /> : <XCircle className="h-4 w-4 shrink-0" />}
          {actionMessage.text}
          {actionJob && (
            <button
              className="ml-auto text-xs underline opacity-70 hover:opacity-100 flex items-center gap-1"
              onClick={() => setShowDetails(v => !v)}
            >
              {showDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {showDetails ? 'Hide details' : 'Show details'}
            </button>
          )}
        </div>
      )}

      {/* Action Result Details Panel */}
      {actionJob && showDetails && (
        <Card className="mb-4 border-slate-200">
          <CardHeader className="py-3">
            <CardTitle className="text-sm flex items-center gap-2">
              {actionKind === 'scan' ? <Shield className="h-4 w-4" /> : <TestTube className="h-4 w-4" />}
              {actionKind === 'scan' ? 'Scan' : 'Test'} Job
              <Badge className={actionJobStatusColors[actionJob.status] ?? 'bg-gray-100 text-gray-800'}>
                {actionJob.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="py-3 space-y-3 text-sm">
            <div className="flex gap-4 text-muted-foreground">
              <span>
                Job ID: <strong className="font-mono">{actionJob.job_id}</strong>
              </span>
              <span>
                Total: <strong>{actionJob.summary.total}</strong>
              </span>
              <span>
                Succeeded: <strong>{actionJob.summary.succeeded}</strong>
              </span>
              <span>
                Failed: <strong>{actionJob.summary.failed}</strong>
              </span>
            </div>

            {actionJobItems.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Skill ID</TableHead>
                    <TableHead>Revision</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Attempt</TableHead>
                    <TableHead>Worker</TableHead>
                    <TableHead>Lease Expires</TableHead>
                    {actionJob.job_type === 'scan_batch' && <>
                      <TableHead>Risk Level</TableHead>
                      <TableHead>Risk Score</TableHead>
                      <TableHead>Findings</TableHead>
                    </>}
                    {actionJob.job_type === 'test_batch' && <>
                      <TableHead>Score</TableHead>
                      <TableHead>Passed</TableHead>
                    </>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {actionJobItems.map((item) => renderActionJobRow(item, actionJob))}
                </TableBody>
              </Table>
            )}

            {(actionJob.error_code || actionJob.error_message || actionJobItems.some((item) => item.error_code || item.error_message)) && (
              <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm space-y-1">
                {actionJob.error_code && <div><span className="font-medium">Job error code:</span> {actionJob.error_code}</div>}
                {actionJob.error_message && <div><span className="font-medium">Job message:</span> {actionJob.error_message}</div>}
                {actionJobItems.filter((item) => item.error_code || item.error_message).map((item) => (
                  <div key={item.item_id}>
                    <span className="font-medium">{item.skill_id}:</span> {item.error_message ?? item.error_code}
                  </div>
                ))}
                {retriableFailedItem && (
                  <div className="pt-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleRetryFailedItem}
                      disabled={retryJobItemMutation.isPending}
                    >
                      {retryJobItemMutation.isPending ? 'Retrying…' : 'Retry failed item'}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Title & Status */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">{skill.name}</h1>
          <div className="flex gap-2">
            <Badge className={statusColors[skill.status]}>
              {skill.status}
            </Badge>
            <Badge className={riskColors[skill.risk_level]}>
              {skill.risk_level} ({skill.risk_score})
            </Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <div className="relative group">
            <Button
              variant="outline"
              size="sm"
              onClick={handleScan}
              disabled={!readiness?.can_scan || activeActionPending}
              title={readiness?.can_scan ? 'Run security scan' : (readiness?.reasons.join('; ') ?? 'Checking readiness…')}
            >
              {scanJobMutation.isPending || (actionJob?.status === 'queued' || actionJob?.status === 'running') && actionKind === 'scan' ? 'Scanning…' : 'Re-scan'}
              {readiness && !readiness.can_scan && <AlertCircle className="h-3 w-3 ml-1 text-amber-500" />}
            </Button>
          </div>
          <div className="relative group">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTest}
              disabled={!readiness?.can_test || activeActionPending}
              title={readiness?.can_test ? 'Run fidelity test' : (readiness?.reasons.join('; ') ?? 'Checking readiness…')}
            >
              {testJobMutation.isPending || (actionJob?.status === 'queued' || actionJob?.status === 'running') && actionKind === 'test' ? 'Testing…' : 'Re-test'}
              {readiness && !readiness.can_test && <AlertCircle className="h-3 w-3 ml-1 text-amber-500" />}
            </Button>
          </div>
          {skill.status === 'pending' && (
            <>
              <Button variant="default" size="sm" className="bg-green-600 hover:bg-green-700">Approve</Button>
              <Button variant="destructive" size="sm">Reject</Button>
            </>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Metadata */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Metadata
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Author</span>
              <span>{skill.author_name}</span>
            </div>
            {skill.author_email && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Email</span>
                <a href={`mailto:${skill.author_email}`} className="text-blue-600 hover:text-blue-800">
                  {skill.author_email}
                </a>
              </div>
            )}
            {skill.author_org && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Organization</span>
                <span>{skill.author_org}</span>
              </div>
            )}
            {skill.author_url && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Author URL</span>
                <a href={skill.author_url} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
                  Link <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Source</span>
              {skill.source_url ? (
                <a
                  href={skill.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors"
                >
                  Original
                  <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <span>{skill.source_type}</span>
              )}
            </div>
            {skill.source_path && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Path</span>
                <span className="text-sm font-mono truncate max-w-[200px]" title={skill.source_path}>
                  {skill.source_path}
                </span>
              </div>
            )}
            {skill.source_commit && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Commit</span>
                <span className="text-sm font-mono">{skill.source_commit.slice(0, 8)}</span>
              </div>
            )}
            {skill.current_revision_id && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Revision</span>
                <span className="text-sm font-mono">{skill.current_revision_id.slice(0, 8)}</span>
              </div>
            )}
            {skill.source_checksum && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Checksum</span>
                <span className="text-sm font-mono">{skill.source_checksum.slice(0, 12)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version</span>
              <span>{skill.version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span>{skill.created_at ? new Date(skill.created_at).toLocaleDateString() : '-'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Updated</span>
              <span>{new Date(skill.updated_at).toLocaleDateString()}</span>
            </div>
          </CardContent>
        </Card>

        {/* Fidelity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TestTube className="h-5 w-5" />
              Fidelity Testing
            </CardTitle>
          </CardHeader>
          <CardContent>
            {skill.fidelity_score !== null && skill.fidelity_score !== undefined && (
              <div className="flex justify-between items-center mb-3">
                <span className="text-muted-foreground">Fidelity Score</span>
                <span className="text-2xl font-bold">
                  {Math.round(skill.fidelity_score * 100)}%
                </span>
              </div>
            )}
            {skill.fidelity_passed !== null && skill.fidelity_passed !== undefined && (
              <div className="flex justify-between items-center mb-3">
                <span className="text-muted-foreground">Result</span>
                {skill.fidelity_passed ? (
                  <span className="flex items-center gap-1 text-green-600">
                    <CheckCircle className="h-4 w-4" /> Passed
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-red-600">
                    <XCircle className="h-4 w-4" /> Failed
                  </span>
                )}
              </div>
            )}
            {skill.test_history && skill.test_history.length > 0 ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Latest Score</span>
                  <span className="text-2xl font-bold">
                    {Math.round((skill.test_history[0].overall_score || 0) * 100)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Semantic</span>
                  <span>{Math.round((skill.test_history[0].semantic_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Structure</span>
                  <span>{Math.round((skill.test_history[0].structure_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Keywords</span>
                  <span>{Math.round((skill.test_history[0].keyword_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Status</span>
                  {skill.test_history[0].passed ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle className="h-4 w-4" /> Passed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-600">
                      <XCircle className="h-4 w-4" /> Failed
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No fidelity tests yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* License & Governance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* License */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scale className="h-5 w-5" />
              License & Rights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">License</span>
              <span className="font-medium">{skill.license_spdx}</span>
            </div>
            {skill.license_url && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">License URL</span>
                <a href={skill.license_url} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
                  View <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Attribution Required</span>
              <Badge className={skill.requires_attribution ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'}>
                {skill.requires_attribution ? 'Yes' : 'No'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Commercial Use</span>
              <Badge className={skill.commercial_allowed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                {skill.commercial_allowed ? 'Allowed' : 'Not Allowed'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Modification</span>
              <Badge className={skill.modification_allowed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                {skill.modification_allowed ? 'Allowed' : 'Not Allowed'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Governance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Governance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {skill.approved_by && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Approved By</span>
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" /> {skill.approved_by}
                </span>
              </div>
            )}
            {skill.approved_at && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Approved At</span>
                <span>{new Date(skill.approved_at).toLocaleString()}</span>
              </div>
            )}
            {skill.security_scanned_at && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Last Scan</span>
                <span>{new Date(skill.security_scanned_at).toLocaleString()}</span>
              </div>
            )}
            {skill.scanner_version && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Scanner Version</span>
                <span className="font-mono text-sm">{skill.scanner_version}</span>
              </div>
            )}
            {skill.installed_path && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Installed At</span>
                <span className="text-sm font-mono truncate max-w-[200px]" title={skill.installed_path}>
                  {skill.installed_path}
                </span>
              </div>
            )}
            {skill.installed_at && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Install Date</span>
                <span>{new Date(skill.installed_at).toLocaleString()}</span>
              </div>
            )}
            {readiness?.revision_id && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Ready On Revision</span>
                <span className="text-sm font-mono">{readiness.revision_id.slice(0, 8)}</span>
              </div>
            )}
            {!skill.approved_by && !skill.security_scanned_at && !skill.installed_path && (
              <p className="text-muted-foreground">No governance data recorded</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Revision History */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Revision History</CardTitle>
        </CardHeader>
        <CardContent>
          {revisionHistory.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Revision</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Commit</TableHead>
                  <TableHead>Checksum</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {revisionHistory.map((revision) => (
                  <TableRow key={revision.revision_id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">r{revision.revision_number}</span>
                        {revision.is_current && (
                          <Badge variant="outline" className="text-xs">
                            current
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs font-mono text-muted-foreground">
                        {revision.revision_id.slice(0, 8)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColors[revision.status] ?? 'bg-slate-100 text-slate-700'}>
                        {revision.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {revision.source_commit ? revision.source_commit.slice(0, 8) : '-'}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {revision.source_checksum ? revision.source_checksum.slice(0, 12) : '-'}
                    </TableCell>
                    <TableCell>
                      <Badge className={riskColors[revision.risk_level] ?? 'bg-slate-100 text-slate-700'}>
                        {revision.risk_level} ({revision.risk_score})
                      </Badge>
                    </TableCell>
                    <TableCell>{new Date(revision.updated_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground">No revision history recorded</p>
          )}
        </CardContent>
      </Card>

      {/* Security Findings */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security Findings ({skill.security_findings?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {skill.security_findings && skill.security_findings.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Context</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Content</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {skill.security_findings.map((finding, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <div className="font-medium">{finding.rule_id}</div>
                      <div className="text-sm text-muted-foreground">{finding.rule_name}</div>
                      {finding.detection_standard && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {finding.standard_url ? (
                            <a href={finding.standard_url} target="_blank" rel="noopener noreferrer"
                               className="text-blue-600 hover:text-blue-800"
                               onClick={(e) => e.stopPropagation()}>
                              {finding.detection_standard}
                            </a>
                          ) : (
                            <span>{finding.detection_standard}</span>
                          )}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className={severityColors[finding.severity] || 'text-gray-600'}>
                        {finding.severity}
                      </span>
                      {finding.severity_changed && finding.original_severity && (
                        <div className="text-xs text-muted-foreground mt-1">
                          was: {finding.original_severity}
                          {finding.adjustment_reason && (
                            <span className="block">{finding.adjustment_reason}</span>
                          )}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      {finding.context_type && (
                        <Badge variant="outline" className="text-xs">
                          {finding.context_type}
                        </Badge>
                      )}
                      {finding.in_code_block && (
                        <Badge variant="outline" className="text-xs ml-1 bg-slate-50">
                          {finding.code_block_language || 'code'}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {finding.file_path && (
                        <span className="text-sm">
                          {finding.file_path}:{finding.line_number}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                        {finding.line_content?.slice(0, 50)}
                        {(finding.line_content?.length || 0) > 50 && '...'}
                      </code>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              No security findings
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scan History */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Scan History</CardTitle>
        </CardHeader>
        <CardContent>
          {skill.scan_history && skill.scan_history.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Findings</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {skill.scan_history.map((scan) => (
                  <TableRow key={scan.scan_id}>
                    <TableCell>{new Date(scan.scanned_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={riskColors[scan.risk_level]}>
                        {scan.risk_level}
                      </Badge>
                    </TableCell>
                    <TableCell>{scan.risk_score}</TableCell>
                    <TableCell>{scan.findings_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground">No scan history</p>
          )}
        </CardContent>
      </Card>

      {/* Audit Log */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {skill.audit_events && skill.audit_events.length > 0 ? (
            <div className="space-y-3">
              {skill.audit_events.slice(0, 10).map((event) => (
                <div key={event.event_id} className="flex items-start gap-3 text-sm">
                  <span className="text-muted-foreground whitespace-nowrap">
                    {new Date(event.timestamp).toLocaleString()}
                  </span>
                  <span className="font-medium uppercase text-xs bg-slate-100 px-2 py-1 rounded">
                    {event.event_type}
                  </span>
                  <span className="text-muted-foreground">by {event.actor}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No activity recorded</p>
          )}
        </CardContent>
      </Card>
    </PageLayout>
  );
}
