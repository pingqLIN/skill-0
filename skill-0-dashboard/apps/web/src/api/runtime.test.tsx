import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { runtimeApi } from './client';
import { useDecideRuntimeHitl, useRuntimeHitlItems } from './runtime';

vi.mock('./client', () => ({
  runtimeApi: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

describe('Runtime API hooks', () => {
  it('loads a bounded queue by status', async () => {
    vi.mocked(runtimeApi.get).mockResolvedValueOnce({ data: [] });
    const { result } = renderHook(() => useRuntimeHitlItems('pending'), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(runtimeApi.get).toHaveBeenCalledWith('/api/runs/hitl/items', {
      params: { status: 'pending', limit: 100 },
    });
  });

  it('sends only the allowlisted decision and reason code', async () => {
    vi.mocked(runtimeApi.post).mockResolvedValueOnce({ data: { status: 'approved' } });
    const { result } = renderHook(() => useDecideRuntimeHitl(), {
      wrapper: createWrapper(),
    });
    await result.current.mutateAsync({
      itemId: 'item-1',
      runId: 'run-1',
      decision: 'approve',
      reasonCode: 'RUNTIME_REVIEW_APPROVED',
    });
    expect(runtimeApi.post).toHaveBeenCalledWith(
      '/api/runs/hitl/items/item-1/decision',
      { decision: 'approve', reason_code: 'RUNTIME_REVIEW_APPROVED' }
    );
  });
});
