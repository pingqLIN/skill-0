import { useQuery } from '@tanstack/react-query';
import { api } from './client';
import type { ScanListItem } from './types';

export function useScans() {
  return useQuery<ScanListItem[]>({
    queryKey: ['scans'],
    queryFn: async () => {
      const { data } = await api.get('/api/scans');
      return data;
    },
  });
}
