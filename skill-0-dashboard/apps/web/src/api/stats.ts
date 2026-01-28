import { useQuery } from '@tanstack/react-query';
import { api } from './client';
import type { StatsOverview, RiskDistribution, StatusDistribution } from './types';

export function useStats() {
  return useQuery<StatsOverview>({
    queryKey: ['stats'],
    queryFn: async () => {
      const { data } = await api.get('/api/stats');
      return data;
    },
    refetchInterval: 30000,
  });
}

export function useRiskDistribution() {
  return useQuery<RiskDistribution>({
    queryKey: ['stats', 'risk-distribution'],
    queryFn: async () => {
      const { data } = await api.get('/api/stats/risk-distribution');
      return data;
    },
  });
}

export function useStatusDistribution() {
  return useQuery<StatusDistribution>({
    queryKey: ['stats', 'status-distribution'],
    queryFn: async () => {
      const { data } = await api.get('/api/stats/status-distribution');
      return data;
    },
  });
}
