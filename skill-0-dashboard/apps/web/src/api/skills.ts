import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type {
  SkillSummary,
  SkillDetail,
  ActionReadiness,
  ActionResult,
  RevisionSummary,
  ActionJobItem,
  ActionJobSummary,
  ActionSelectionMode,
} from './types';

interface SkillListResponse {
  items: SkillSummary[];
  total: number;
  page: number;
  page_size: number;
}

interface SkillQueryParams {
  page?: number;
  page_size?: number;
  status?: string;
  risk_level?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export function useSkills(params: SkillQueryParams = {}) {
  return useQuery<SkillListResponse>({
    queryKey: ['skills', params],
    queryFn: async () => {
      const { data } = await api.get('/api/skills', { params });
      return data;
    },
  });
}

export function useSkill(skillId: string) {
  return useQuery<SkillDetail>({
    queryKey: ['skill', skillId],
    queryFn: async () => {
      const { data } = await api.get(`/api/skills/${skillId}`);
      return data;
    },
    enabled: !!skillId,
  });
}

export function useActionReadiness(skillId: string) {
  return useQuery<ActionReadiness>({
    queryKey: ['action-readiness', skillId],
    queryFn: async () => {
      const { data } = await api.get(`/api/skills/${skillId}/action-readiness`);
      return data;
    },
    enabled: !!skillId,
  });
}

export function useSkillRevisions(skillId: string) {
  return useQuery<RevisionSummary[]>({
    queryKey: ['skill-revisions', skillId],
    queryFn: async () => {
      const { data } = await api.get(`/api/skills/${skillId}/revisions`);
      return data;
    },
    enabled: !!skillId,
  });
}

export function useTriggerScan() {
  const queryClient = useQueryClient();
  return useMutation<ActionResult, Error, string>({
    mutationFn: async (skillId: string) => {
      const { data } = await api.post('/api/skills/scan', null, { params: { skill_id: skillId } });
      return data;
    },
    onSuccess: (_data, skillId) => {
      queryClient.invalidateQueries({ queryKey: ['skill', skillId] });
      queryClient.invalidateQueries({ queryKey: ['skill-revisions', skillId] });
      queryClient.invalidateQueries({ queryKey: ['action-readiness', skillId] });
    },
  });
}

export function useTriggerTest() {
  const queryClient = useQueryClient();
  return useMutation<ActionResult, Error, string>({
    mutationFn: async (skillId: string) => {
      const { data } = await api.post('/api/skills/test', null, { params: { skill_id: skillId } });
      return data;
    },
    onSuccess: (_data, skillId) => {
      queryClient.invalidateQueries({ queryKey: ['skill', skillId] });
      queryClient.invalidateQueries({ queryKey: ['skill-revisions', skillId] });
      queryClient.invalidateQueries({ queryKey: ['action-readiness', skillId] });
    },
  });
}

interface ActionJobRequest {
  skill_ids: string[];
  selection_mode?: ActionSelectionMode;
  max_attempts?: number;
}

export function useEnqueueScanJob() {
  return useMutation<ActionJobSummary, Error, ActionJobRequest>({
    mutationFn: async ({ skill_ids, selection_mode = 'explicit', max_attempts = 2 }) => {
      const { data } = await api.post('/api/skills/scan-jobs', {
        skill_ids,
        selection_mode,
        max_attempts,
      });
      return data;
    },
  });
}

export function useEnqueueTestJob() {
  return useMutation<ActionJobSummary, Error, ActionJobRequest>({
    mutationFn: async ({ skill_ids, selection_mode = 'explicit', max_attempts = 2 }) => {
      const { data } = await api.post('/api/skills/test-jobs', {
        skill_ids,
        selection_mode,
        max_attempts,
      });
      return data;
    },
  });
}

export function useActionJob(jobId: string) {
  return useQuery<ActionJobSummary>({
    queryKey: ['action-job', jobId],
    queryFn: async () => {
      const { data } = await api.get(`/api/skills/action-jobs/${jobId}`);
      return data;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'queued' || status === 'running' ? 1000 : false;
    },
  });
}

export function useActionJobItems(jobId: string) {
  return useQuery<ActionJobItem[]>({
    queryKey: ['action-job-items', jobId],
    queryFn: async () => {
      const { data } = await api.get(`/api/skills/action-jobs/${jobId}/items`);
      return data;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const items = query.state.data ?? [];
      return items.some((item) => item.status === 'queued' || item.status === 'running' || item.status === 'retrying')
        ? 1000
        : false;
    },
  });
}

export function useRetryActionJobItem() {
  return useMutation<ActionJobSummary, Error, { jobId: string; itemId: string }>({
    mutationFn: async ({ jobId, itemId }) => {
      const { data } = await api.post(`/api/skills/action-jobs/${jobId}/items/${itemId}/retry`);
      return data;
    },
  });
}
