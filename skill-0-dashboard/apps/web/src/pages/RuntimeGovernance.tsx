import { useState } from 'react';
import {
  Check,
  Eye,
  Loader2,
  RotateCcw,
  ShieldCheck,
  X,
} from 'lucide-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  type RuntimeDecision,
  type RuntimeHitlItem,
  type RuntimeHitlStatus,
  useDecideRuntimeHitl,
  useRuntimeEvidence,
  useRuntimeHitlItems,
} from '@/api/runtime';

const statuses: RuntimeHitlStatus[] = [
  'pending',
  'approved',
  'rejected',
  'confirmed',
];

const statusClasses: Record<RuntimeHitlStatus, string> = {
  pending: 'bg-amber-100 text-amber-900',
  approved: 'bg-emerald-100 text-emerald-900',
  rejected: 'bg-red-100 text-red-900',
  confirmed: 'bg-blue-100 text-blue-900',
};

const reasonCodes: Record<RuntimeDecision, string> = {
  approve: 'RUNTIME_REVIEW_APPROVED',
  reject: 'RUNTIME_REVIEW_REJECTED',
  confirm_recovered: 'RECOVERY_VERIFIED',
};

interface PendingDecision {
  item: RuntimeHitlItem;
  decision: RuntimeDecision;
  label: string;
}

function errorDetail(error: unknown) {
  return (
    (error as { response?: { data?: { detail?: string } } })?.response?.data
      ?.detail ?? 'Runtime decision failed'
  );
}

function formatValue(value: unknown) {
  if (typeof value === 'string' || typeof value === 'number') {
    return String(value);
  }
  if (typeof value === 'boolean') {
    return value ? 'yes' : 'no';
  }
  return JSON.stringify(value);
}

export function RuntimeGovernance() {
  const [status, setStatus] = useState<RuntimeHitlStatus>('pending');
  const [pendingDecision, setPendingDecision] = useState<PendingDecision | null>(
    null
  );
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const { data: items = [], isLoading, error, refetch } =
    useRuntimeHitlItems(status);
  const decisionMutation = useDecideRuntimeHitl();
  const {
    data: evidence,
    isLoading: evidenceLoading,
    error: evidenceError,
  } = useRuntimeEvidence(selectedRunId);

  const requestDecision = (
    item: RuntimeHitlItem,
    decision: RuntimeDecision,
    label: string
  ) => {
    setFeedback(null);
    setPendingDecision({ item, decision, label });
  };

  const confirmDecision = async () => {
    if (!pendingDecision) {
      return;
    }
    const { item, decision, label } = pendingDecision;
    try {
      await decisionMutation.mutateAsync({
        itemId: item.item_id,
        runId: item.run_id,
        decision,
        reasonCode: reasonCodes[decision],
      });
      setFeedback({
        type: 'success',
        message: `${label} recorded. Runtime execution remains a separate operator action.`,
      });
      setPendingDecision(null);
    } catch (mutationError) {
      setFeedback({ type: 'error', message: errorDetail(mutationError) });
    }
  };

  return (
    <PageLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-500">
              <ShieldCheck className="h-4 w-4" />
              Runtime v4 governance
            </div>
            <h1 className="text-2xl font-bold text-slate-950">Runtime HITL Queue</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-600">
              Decisions are action-scoped and recorded in the authoritative Runtime
              ledger. Approval never resumes a run, and recovery confirmation never
              skips the remaining recovery candidates.
            </p>
          </div>
          <Button variant="outline" onClick={() => refetch()} disabled={isLoading}>
            <RotateCcw className="mr-2 h-4 w-4" /> Refresh
          </Button>
        </div>

        <div className="flex flex-wrap gap-2" aria-label="Runtime queue status">
          {statuses.map((value) => (
            <Button
              key={value}
              variant={status === value ? 'default' : 'outline'}
              aria-pressed={status === value}
              onClick={() => {
                setStatus(value);
                setPendingDecision(null);
              }}
              className="capitalize"
            >
              {value}
            </Button>
          ))}
        </div>

        {feedback ? (
          <div
            role="alert"
            className={`rounded-lg border px-4 py-3 text-sm ${
              feedback.type === 'success'
                ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                : 'border-red-200 bg-red-50 text-red-900'
            }`}
          >
            {feedback.message}
          </div>
        ) : null}

        {pendingDecision ? (
          <Card className="border-slate-900 shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Confirm governance decision</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-4">
              <p className="text-sm text-slate-700">
                {pendingDecision.label} for action{' '}
                <span className="font-mono">{pendingDecision.item.action_id}</span>{' '}
                in run <span className="font-mono">{pendingDecision.item.run_id}</span>?
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setPendingDecision(null)}
                  disabled={decisionMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  onClick={confirmDecision}
                  disabled={decisionMutation.isPending}
                >
                  {decisionMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : null}
                  Confirm {pendingDecision.label}
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {isLoading ? (
          <div className="flex min-h-48 items-center justify-center">
            <Loader2 className="h-7 w-7 animate-spin text-slate-500" aria-label="Loading Runtime queue" />
          </div>
        ) : error ? (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6 text-sm text-red-900">
              {errorDetail(error)}
            </CardContent>
          </Card>
        ) : items.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center text-sm text-slate-500">
              No {status} Runtime HITL items.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {items.map((item) => (
              <Card key={item.item_id} className="overflow-hidden">
                <CardHeader className="border-b border-slate-100 bg-white">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <CardTitle className="font-mono text-sm">{item.action_id}</CardTitle>
                    <div className="flex gap-2">
                      <Badge className={statusClasses[item.status]}>{item.status}</Badge>
                      <Badge variant="outline">{item.kind}</Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4 pt-5">
                  <div className="grid gap-2 text-sm sm:grid-cols-2">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-slate-500">Skill</div>
                      <div className="mt-1 break-all font-mono text-xs">{item.skill_id}</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-slate-500">Run</div>
                      <div className="mt-1 break-all font-mono text-xs">{item.run_id}</div>
                    </div>
                  </div>

                  <dl className="grid gap-2 rounded-lg bg-slate-50 p-3 text-sm sm:grid-cols-2">
                    {Object.entries(item.request_summary).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-xs text-slate-500">{key.replaceAll('_', ' ')}</dt>
                        <dd className="mt-0.5 break-words font-medium text-slate-800">
                          {formatValue(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>

                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setSelectedRunId(item.run_id)}
                    >
                      <Eye className="mr-2 h-4 w-4" /> Evidence
                    </Button>
                    {item.status === 'pending' && item.kind === 'action_approval' ? (
                      <Button onClick={() => requestDecision(item, 'approve', 'Approve')}>
                        <Check className="mr-2 h-4 w-4" /> Approve
                      </Button>
                    ) : null}
                    {item.status === 'pending' && item.kind === 'recovery_confirmation' ? (
                      <Button
                        onClick={() =>
                          requestDecision(item, 'confirm_recovered', 'Confirm recovered')
                        }
                      >
                        <Check className="mr-2 h-4 w-4" /> Confirm recovered
                      </Button>
                    ) : null}
                    {item.status === 'pending' ? (
                      <Button
                        variant="destructive"
                        onClick={() => requestDecision(item, 'reject', 'Reject')}
                      >
                        <X className="mr-2 h-4 w-4" /> Reject
                      </Button>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {selectedRunId ? (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">Run evidence</CardTitle>
              <Button variant="ghost" onClick={() => setSelectedRunId(null)}>
                Close
              </Button>
            </CardHeader>
            <CardContent>
              {evidenceLoading ? (
                <Loader2 className="h-6 w-6 animate-spin" aria-label="Loading Runtime evidence" />
              ) : evidenceError ? (
                <p className="text-sm text-red-700">{errorDetail(evidenceError)}</p>
              ) : evidence ? (
                <div className="grid gap-4 text-sm md:grid-cols-2 xl:grid-cols-4">
                  <div><span className="text-slate-500">Status</span><div className="font-medium">{evidence.run_ref.status}</div></div>
                  <div><span className="text-slate-500">Events</span><div className="font-medium">{evidence.event_count}</div></div>
                  <div><span className="text-slate-500">Last event</span><div className="font-medium">{evidence.last_event_type}</div></div>
                  <div><span className="text-slate-500">Confidence</span><div className="font-medium">{Math.round(evidence.confidence * 100)}%</div></div>
                  {evidence.governance_ref ? (
                    <div className="md:col-span-2 xl:col-span-4 rounded-lg bg-slate-50 p-3">
                      <span className="text-slate-500">Governance revision</span>
                      <div className="mt-1 font-mono text-xs">{evidence.governance_ref.revision_id}</div>
                      <div className="mt-1 text-xs text-slate-600">
                        approved by {evidence.governance_ref.approved_by} · revision {evidence.governance_ref.revision_number}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>
        ) : null}
      </div>
    </PageLayout>
  );
}
