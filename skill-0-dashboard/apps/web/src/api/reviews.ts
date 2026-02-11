import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type { SkillSummary } from './types';

export function usePendingReviews() {
  return useQuery<SkillSummary[]>({
    queryKey: ['reviews', 'pending'],
    queryFn: async () => {
      const { data } = await api.get('/api/reviews');
      return data;
    },
  });
}

export function useApproveSkill() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ skillId, reason }: { skillId: string; reason: string }) => {
      const { data } = await api.post(`/api/reviews/${skillId}/approve`, {
        reason,
        reviewer: 'admin',
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}

export function useRejectSkill() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ skillId, reason }: { skillId: string; reason: string }) => {
      const { data } = await api.post(`/api/reviews/${skillId}/reject`, {
        reason,
        reviewer: 'admin',
      });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
      queryClient.invalidateQueries({ queryKey: ['skills'] });
      queryClient.invalidateQueries({ queryKey: ['stats'] });
    },
  });
}
