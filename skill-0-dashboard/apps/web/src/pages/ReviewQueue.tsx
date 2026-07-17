import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { PageLayout } from '@/components/layout/PageLayout';
import { ReviewCard } from '@/components/cards/ReviewCard';
import { usePendingReviews, useApproveSkill, useRejectSkill } from '@/api/reviews';
import {
  useActionJob,
  useActionJobItems,
  useCancelActionJob,
  useEnqueueScanJob,
  useEnqueueTestJob,
  useRetryActionJobFailures,
} from '@/api/skills';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  CheckCircle,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Shield,
  TestTube,
  XCircle,
} from 'lucide-react';
import type { ActionJobItem, ActionJobSummary } from '@/api/types';

type FilterType = 'all' | 'safe' | 'risky';
type ActionKind = 'scan' | 'test' | null;

interface Feedback {
  message: string;
  type: 'success' | 'error';
}

const riskColors: Record<string, string> = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  medium: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900',
  blocked: 'bg-gray-100 text-gray-800',
};

const actionJobStatusColors: Record<string, string> = {
  queued: 'bg-blue-100 text-blue-800',
  running: 'bg-indigo-100 text-indigo-800',
  completed: 'bg-green-100 text-green-800',
  completed_with_failures: 'bg-amber-100 text-amber-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-800',
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

function formatTelemetryValue(value: string | null | undefined) {
  return value ?? '-';
}

function getActionJobFeedback(
  actionJob: ActionJobSummary | undefined,
  actionKind: ActionKind,
): Feedback | null {
  if (!actionJob || !actionKind) {
    return null;
  }

  const kindLabel = actionKind === 'test' ? 'Test' : 'Scan';
  const completedCount = actionJob.summary.succeeded + actionJob.summary.failed + actionJob.summary.skipped;
  if (actionJob.status === 'queued') {
    const retryLabel = actionJob.selection_mode.startsWith('retry_') ? ' retry' : '';
    return { message: `${kindLabel}${retryLabel} job queued`, type: 'success' };
  }
  if (actionJob.status === 'running') {
    return {
      message: `${kindLabel} job running - ${completedCount}/${actionJob.summary.total} completed`,
      type: 'success',
    };
  }
  if (actionJob.status === 'completed') {
    return {
      message: `${kindLabel} job complete - ${actionJob.summary.succeeded}/${actionJob.summary.total} succeeded`,
      type: 'success',
    };
  }
  if (actionJob.status === 'cancelled') {
    return { message: `${kindLabel} job cancelled`, type: 'error' };
  }
  return {
    message: actionJob.error_message ?? `${kindLabel} job finished with failures`,
    type: 'error',
  };
}

export function ReviewQueue() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<FilterType>('all');
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [isBulkApproving, setIsBulkApproving] = useState(false);
  const [activeJobId, setActiveJobId] = useState('');
  const [dismissedJobId, setDismissedJobId] = useState('');
  const [actionKind, setActionKind] = useState<ActionKind>(null);
  const [showJobDetails, setShowJobDetails] = useState(false);
  const { data: skills, isLoading } = usePendingReviews();
  const approveMutation = useApproveSkill();
  const rejectMutation = useRejectSkill();
  const scanJobMutation = useEnqueueScanJob();
  const testJobMutation = useEnqueueTestJob();
  const cancelJobMutation = useCancelActionJob();
  const retryFailuresMutation = useRetryActionJobFailures();
  const { data: actionJob } = useActionJob(activeJobId);
  const { data: actionJobItems = [] } = useActionJobItems(activeJobId);

  const safeSkills = skills?.filter((skill) => ['safe', 'low'].includes(skill.risk_level)) || [];
  const riskySkills = skills?.filter((skill) => ['medium', 'high', 'critical'].includes(skill.risk_level)) || [];
  const filteredSkills =
    filter === 'safe'
      ? safeSkills
      : filter === 'risky'
        ? riskySkills
        : skills || [];

  const safeCount = safeSkills.length;
  const riskyCount = riskySkills.length;
  const pendingCount = skills?.length || 0;
  const actionJobFeedback =
    actionJob?.job_id === dismissedJobId
      ? null
      : getActionJobFeedback(actionJob, actionKind);
  const visibleFeedback =
    feedback?.type === 'error' ? feedback : actionJobFeedback ?? feedback;

  useEffect(() => {
    if (!actionJob || actionJob.status === 'queued' || actionJob.status === 'running') {
      return;
    }

    queryClient.invalidateQueries({ queryKey: ['reviews'] });
    queryClient.invalidateQueries({ queryKey: ['skills'] });
    queryClient.invalidateQueries({ queryKey: ['stats'] });
  }, [actionJob, queryClient]);

  const handleApprove = (skillId: string, reason: string) => {
    approveMutation.mutate(
      { skillId, reason },
      {
        onSuccess: (data) => setFeedback({ message: `Skill ${data.skill_id}: ${data.status}`, type: 'success' }),
        onError: (err: unknown) => {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          setFeedback({ message: detail || 'Approve failed', type: 'error' });
        },
      }
    );
  };

  const handleReject = (skillId: string, reason: string) => {
    rejectMutation.mutate(
      { skillId, reason },
      {
        onSuccess: (data) => setFeedback({ message: `Skill ${data.skill_id}: ${data.status}`, type: 'success' }),
        onError: (err: unknown) => {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          setFeedback({ message: detail || 'Reject failed', type: 'error' });
        },
      }
    );
  };

  const handleBulkApproveSafe = async () => {
    if (safeSkills.length === 0 || isBulkApproving) {
      return;
    }

    setIsBulkApproving(true);
    const targets = [...safeSkills];
    let approvedCount = 0;
    const failures: string[] = [];

    try {
      for (const skill of targets) {
        try {
          await approveMutation.mutateAsync({
            skillId: skill.skill_id,
            reason: 'Bulk approved safe skill',
          });
          approvedCount += 1;
        } catch (err: unknown) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          failures.push(`${skill.name}: ${detail || 'Approve failed'}`);
        }
      }

      if (failures.length === 0) {
        setFeedback({
          message: `Bulk approved ${approvedCount} safe skill(s)`,
          type: 'success',
        });
      } else {
        setFeedback({
          message: `Bulk approved ${approvedCount}/${targets.length} safe skill(s). ${failures.length} failed.`,
          type: 'error',
        });
      }
    } finally {
      setIsBulkApproving(false);
    }
  };

  const handleBatchAction = async (kind: Exclude<ActionKind, null>) => {
    if (!skills || skills.length === 0) {
      return;
    }

    setFeedback(null);
    setActionKind(kind);
    setActiveJobId('');
    setShowJobDetails(false);

    const queueJob = kind === 'scan' ? scanJobMutation : testJobMutation;
    const job = await queueJob.mutateAsync({
      skill_ids: skills.map((skill) => skill.skill_id),
    }).catch((error: Error) => {
      setFeedback({ message: error.message, type: 'error' });
      return null;
    });

    if (!job) {
      return;
    }

    setActiveJobId(job.job_id);
    setFeedback({
      message: `${kind === 'scan' ? 'Scan' : 'Test'} job queued`,
      type: 'success',
    });
  };

  const retriableFailedItems = actionJobItems.filter((item) =>
    item.status === 'failed' &&
    item.attempt_number < item.max_attempts &&
    item.error_code !== null &&
    !NON_RETRIABLE_ERROR_CODES.has(item.error_code)
  );

  const handleRetryFailures = async () => {
    const targetJobId = actionJob?.job_id ?? activeJobId;
    if (!targetJobId || retriableFailedItems.length === 0) {
      return;
    }

    setFeedback(null);
    const retryJob = await retryFailuresMutation.mutateAsync({ jobId: targetJobId }).catch((error: Error) => {
      setFeedback({ message: error.message, type: 'error' });
      return null;
    });

    if (!retryJob) {
      return;
    }

    setActiveJobId(retryJob.job_id);
    setShowJobDetails(true);
    setFeedback({
      message: `${actionKind === 'test' ? 'Test' : 'Scan'} retry job queued`,
      type: 'success',
    });
  };

  const handleCancelJob = async () => {
    const targetJobId = actionJob?.job_id ?? activeJobId;
    if (!targetJobId) {
      return;
    }

    setFeedback(null);
    const cancelledJob = await cancelJobMutation.mutateAsync({ jobId: targetJobId }).catch((error: Error) => {
      setFeedback({ message: error.message, type: 'error' });
      return null;
    });

    if (!cancelledJob) {
      return;
    }

    setFeedback({
      message: `${actionKind === 'test' ? 'Test' : 'Scan'} job cancelled`,
      type: 'error',
    });
    queryClient.invalidateQueries({ queryKey: ['action-job-items', targetJobId] });
  };

  const activeActionPending =
    isBulkApproving ||
    approveMutation.isPending ||
    rejectMutation.isPending ||
    scanJobMutation.isPending ||
    testJobMutation.isPending ||
    cancelJobMutation.isPending ||
    retryFailuresMutation.isPending ||
    actionJob?.status === 'queued' ||
    actionJob?.status === 'running';

  const renderActionJobRow = (item: ActionJobItem, job: ActionJobSummary) => {
    const row = item.result ?? {};
    return (
      <TableRow key={item.item_id}>
        <TableCell className="font-mono text-xs">{item.skill_id}</TableCell>
        <TableCell>
          <Badge className={actionJobStatusColors[item.status] ?? 'bg-gray-100 text-gray-800'}>
            {item.status}
          </Badge>
        </TableCell>
        <TableCell>{item.attempt_number}/{item.max_attempts}</TableCell>
        <TableCell className="font-mono text-xs">{item.retry_of_item_id ?? '-'}</TableCell>
        <TableCell className="font-mono text-xs">{item.claimed_by ?? '-'}</TableCell>
        <TableCell className="font-mono text-xs">{formatLeaseExpiry(item.lease_expires_at)}</TableCell>
        <TableCell className="font-mono text-xs">{item.suggested_next_step ?? '-'}</TableCell>
        {job.job_type === 'scan_batch' && (
          <>
            <TableCell>
              <Badge className={riskColors[String(row.risk_level)] ?? 'bg-gray-100 text-gray-800'}>
                {String(row.risk_level ?? '-')}
              </Badge>
            </TableCell>
            <TableCell>{row.risk_score !== undefined ? String(row.risk_score) : '-'}</TableCell>
          </>
        )}
        {job.job_type === 'test_batch' && (
          <>
            <TableCell>{typeof row.overall_score === 'number' ? `${Math.round(row.overall_score * 100)}%` : '-'}</TableCell>
            <TableCell>
              {row.passed === true ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : row.passed === false ? (
                <XCircle className="h-4 w-4 text-red-600" />
              ) : (
                '-'
              )}
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

  return (
    <PageLayout>
      <div className="flex flex-col gap-4 mb-6 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Review Queue</h1>
          <p className="text-sm text-muted-foreground">
            Process pending skills, then fan out async scan and test jobs when the queue is stable.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {pendingCount > 0 && (
            <>
              <Button
                variant="outline"
                onClick={() => void handleBatchAction('scan')}
                disabled={activeActionPending}
              >
                <Shield className="h-4 w-4 mr-2" />
                {scanJobMutation.isPending || (actionKind === 'scan' && (actionJob?.status === 'queued' || actionJob?.status === 'running'))
                  ? 'Scanning pending...'
                  : `Scan Pending (${pendingCount})`}
              </Button>
              <Button
                variant="outline"
                onClick={() => void handleBatchAction('test')}
                disabled={activeActionPending}
              >
                <TestTube className="h-4 w-4 mr-2" />
                {testJobMutation.isPending || (actionKind === 'test' && (actionJob?.status === 'queued' || actionJob?.status === 'running'))
                  ? 'Testing pending...'
                  : `Test Pending (${pendingCount})`}
              </Button>
            </>
          )}
          {safeCount > 0 && (
            <Button
              variant="outline"
              onClick={handleBulkApproveSafe}
              disabled={activeActionPending}
            >
              <CheckCircle className="h-4 w-4 mr-2" />
              {isBulkApproving ? `Approving ${safeCount}...` : `Bulk Approve Safe (${safeCount})`}
            </Button>
          )}
        </div>
      </div>

      {visibleFeedback && (
        <div
          className={`mb-4 px-4 py-3 rounded-lg text-sm flex justify-between items-center ${
            visibleFeedback.type === 'success'
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}
        >
          <span>{visibleFeedback.message}</span>
          <div className="ml-4 flex items-center gap-3">
            {actionJob && (
              <>
                {(actionJob.status === 'queued' || actionJob.status === 'running') && (
                  <button
                    onClick={() => void handleCancelJob()}
                    className="text-xs underline inline-flex items-center gap-1"
                    disabled={cancelJobMutation.isPending}
                  >
                    {cancelJobMutation.isPending ? 'Cancelling...' : 'Cancel job'}
                  </button>
                )}
              </>
            )}
            {actionJob && (
              <button
                onClick={() => setShowJobDetails((value) => !value)}
                className="text-xs underline inline-flex items-center gap-1"
              >
                {showJobDetails ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                {showJobDetails ? 'Hide details' : 'Show details'}
              </button>
            )}
            <button
              onClick={() => {
                setFeedback(null);
                setDismissedJobId(actionJob?.job_id ?? '');
              }}
              aria-label="Dismiss feedback message"
              className="font-bold"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {actionJob && showJobDetails && (
        <Card className="mb-6 border-slate-200">
          <CardHeader className="py-3">
            <CardTitle className="text-sm flex items-center gap-2">
              {actionKind === 'test' ? <TestTube className="h-4 w-4" /> : <Shield className="h-4 w-4" />}
              {actionKind === 'test' ? 'Test' : 'Scan'} Job
              <Badge className={actionJobStatusColors[actionJob.status] ?? 'bg-gray-100 text-gray-800'}>
                {actionJob.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="py-3 space-y-3 text-sm">
            <div className="flex flex-wrap gap-4 text-muted-foreground">
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
              <span>
                Running: <strong>{actionJob.summary.running}</strong>
              </span>
              <span>
                Cancelled: <strong>{actionJob.summary.cancelled}</strong>
              </span>
            </div>
            <div className="grid gap-2 text-muted-foreground md:grid-cols-2 xl:grid-cols-3">
              <span>
                Active workers: <strong className="font-mono">{actionJob.active_workers.length > 0 ? actionJob.active_workers.join(', ') : '-'}</strong>
              </span>
              <span>
                Lease horizon: <strong className="font-mono">{formatTelemetryValue(actionJob.active_lease_expires_at)}</strong>
              </span>
              <span>
                Last item start: <strong className="font-mono">{formatTelemetryValue(actionJob.last_item_started_at)}</strong>
              </span>
              <span>
                Last item finish: <strong className="font-mono">{formatTelemetryValue(actionJob.last_item_completed_at)}</strong>
              </span>
              <span>
                Cancelled by: <strong className="font-mono">{formatTelemetryValue(actionJob.cancelled_by)}</strong>
              </span>
              <span>
                Cancelled at: <strong className="font-mono">{formatTelemetryValue(actionJob.cancelled_at)}</strong>
              </span>
            </div>

            {actionJobItems.length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Skill ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Attempt</TableHead>
                    <TableHead>Retry Of</TableHead>
                    <TableHead>Worker</TableHead>
                    <TableHead>Lease Expires</TableHead>
                    <TableHead>Next Step</TableHead>
                    {actionJob.job_type === 'scan_batch' && (
                      <>
                        <TableHead>Risk Level</TableHead>
                        <TableHead>Risk Score</TableHead>
                      </>
                    )}
                    {actionJob.job_type === 'test_batch' && (
                      <>
                        <TableHead>Score</TableHead>
                        <TableHead>Passed</TableHead>
                      </>
                    )}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {actionJobItems.map((item) => renderActionJobRow(item, actionJob))}
                </TableBody>
              </Table>
            )}

            {(actionJob.error_code || actionJob.error_message || actionJobItems.some((item) => item.error_code || item.error_message)) && (
              <div className="rounded-md bg-red-50 border border-red-200 p-3 text-sm space-y-1">
                {actionJob.error_code && (
                  <div>
                    <span className="font-medium">Job error code:</span> {actionJob.error_code}
                  </div>
                )}
                {actionJob.error_message && (
                  <div>
                    <span className="font-medium">Job message:</span> {actionJob.error_message}
                  </div>
                )}
                {actionJobItems
                  .filter((item) => item.error_code || item.error_message)
                  .map((item) => (
                    <div key={item.item_id}>
                      <span className="font-medium">{item.skill_id}:</span> {item.error_message ?? item.error_code}
                    </div>
                  ))}
                {retriableFailedItems.length > 0 && (
                  <div className="pt-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => void handleRetryFailures()}
                      disabled={retryFailuresMutation.isPending}
                    >
                      <RotateCcw className="h-4 w-4 mr-2" />
                      {retryFailuresMutation.isPending
                        ? 'Retrying failed items...'
                        : `Retry Failed Items (${retriableFailedItems.length})`}
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <div className="flex gap-2 mb-6">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All ({pendingCount})
        </Button>
        <Button
          variant={filter === 'safe' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('safe')}
        >
          Safe Only ({safeCount})
        </Button>
        <Button
          variant={filter === 'risky' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('risky')}
          className={filter === 'risky' ? 'bg-red-600 hover:bg-red-700' : ''}
        >
          Needs Review ({riskyCount})
        </Button>
      </div>

      {filteredSkills.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">All caught up!</h3>
            <p className="text-muted-foreground">No skills pending review.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredSkills.map((skill) => (
            <ReviewCard
              key={skill.skill_id}
              skill={skill}
              onApprove={handleApprove}
              onReject={handleReject}
              isApproving={activeActionPending}
              isRejecting={activeActionPending}
            />
          ))}
        </div>
      )}

      {skills && skills.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold">{skills.length}</p>
                <p className="text-sm text-muted-foreground">Total Pending</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">{safeCount}</p>
                <p className="text-sm text-muted-foreground">Safe to Approve</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">{riskyCount}</p>
                <p className="text-sm text-muted-foreground">Needs Review</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </PageLayout>
  );
}
