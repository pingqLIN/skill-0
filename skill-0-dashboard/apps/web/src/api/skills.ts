import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type { SkillSummary, SkillDetail, ActionReadiness, ActionResult } from './types';

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

export function useTriggerScan() {
  const queryClient = useQueryClient();
  return useMutation<ActionResult, Error, string>({
    mutationFn: async (skillId: string) => {
      const { data } = await api.post('/api/skills/scan', null, { params: { skill_id: skillId } });
      return data;
    },
    onSuccess: (_data, skillId) => {
      queryClient.invalidateQueries({ queryKey: ['skill', skillId] });
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
      queryClient.invalidateQueries({ queryKey: ['action-readiness', skillId] });
    },
  });
}
