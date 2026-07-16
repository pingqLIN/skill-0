import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { runtimeApi } from './client';

export type RuntimeHitlStatus = 'pending' | 'approved' | 'rejected' | 'confirmed';
export type RuntimeHitlKind = 'action_approval' | 'recovery_confirmation';
export type RuntimeDecision = 'approve' | 'reject' | 'confirm_recovered';

export interface RuntimeHitlItem {
  item_id: string;
  run_id: string;
  skill_id: string;
  action_id: string;
  kind: RuntimeHitlKind;
  status: RuntimeHitlStatus;
  request_summary: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface RuntimeEvidence {
  projection_version: string;
  run_ref: { run_id: string; status: string };
  event_count: number;
  last_event_type: string;
  source_event_watermark: number;
  counts: Record<string, number>;
  confidence: number;
  known_failure_patterns: string[];
  element_refs: string[];
  governance_ref?: {
    policy: string;
    canonical_skill_id: string;
    governance_skill_id: string;
    revision_id: string;
    revision_number: number;
    artifact_digest: string;
    approved_by: string;
    approved_at: string;
  };
}

export function useRuntimeHitlItems(status: RuntimeHitlStatus) {
  return useQuery<RuntimeHitlItem[]>({
    queryKey: ['runtime', 'hitl', status],
    queryFn: async () => {
      const { data } = await runtimeApi.get('/api/runs/hitl/items', {
        params: { status, limit: 100 },
      });
      return data;
    },
  });
}

export function useRuntimeEvidence(runId: string | null) {
  return useQuery<RuntimeEvidence>({
    queryKey: ['runtime', 'evidence', runId],
    queryFn: async () => {
      const { data } = await runtimeApi.get(`/api/runs/${runId}/evidence`);
      return data;
    },
    enabled: Boolean(runId),
  });
}

export function useDecideRuntimeHitl() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      itemId,
      runId,
      decision,
      reasonCode,
    }: {
      itemId: string;
      runId: string;
      decision: RuntimeDecision;
      reasonCode: string;
    }) => {
      const { data } = await runtimeApi.post(
        `/api/runs/hitl/items/${itemId}/decision`,
        { decision, reason_code: reasonCode }
      );
      return { item: data as RuntimeHitlItem, runId };
    },
    onSuccess: ({ runId }) => {
      queryClient.invalidateQueries({ queryKey: ['runtime', 'hitl'] });
      queryClient.invalidateQueries({ queryKey: ['runtime', 'evidence', runId] });
    },
  });
}
