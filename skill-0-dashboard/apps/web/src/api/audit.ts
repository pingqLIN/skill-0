import { useQuery } from '@tanstack/react-query';
import { api } from './client';
import type { AuditListResponse } from './types';

interface AuditQueryParams {
  page?: number;
  page_size?: number;
  skill_id?: string;
  event_type?: string;
  from_date?: string;
  to_date?: string;
}

export function useAuditLog(params: AuditQueryParams = {}) {
  return useQuery<AuditListResponse>({
    queryKey: ['audit', params],
    queryFn: async () => {
      const { data } = await api.get('/api/audit', { params });
      return data;
    },
  });
}
