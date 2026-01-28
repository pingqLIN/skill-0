import { useQuery } from '@tanstack/react-query';
import { api } from './client';
import type { SkillSummary, SkillDetail } from './types';

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
