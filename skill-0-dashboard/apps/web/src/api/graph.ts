import { useQuery } from '@tanstack/react-query';
import { api } from './client';
import type { GraphData } from './types';

export function useGraphData() {
  return useQuery<GraphData>({
    queryKey: ['graph'],
    queryFn: async () => {
      const { data } = await api.get('/api/graph');
      return data;
    },
  });
}
