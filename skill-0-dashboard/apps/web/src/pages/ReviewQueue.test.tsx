import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { ReviewQueue } from './ReviewQueue';

const mockApproveMutate = vi.fn();
const mockApproveMutateAsync = vi.fn();
const mockRejectMutate = vi.fn();
const mockRejectMutateAsync = vi.fn();
const mockEnqueueScanMutateAsync = vi.fn();
const mockEnqueueTestMutateAsync = vi.fn();
const mockRetryFailuresMutateAsync = vi.fn();

let currentActionJob: Record<string, unknown> | undefined;
let currentActionJobItems: Array<Record<string, unknown>> = [];

const pendingSkills = [
  {
    skill_id: 'sk_001',
    current_revision_id: 'rev_001',
    revision_id: 'rev_001',
    revision_number: 1,
    name: 'Safe Skill',
    status: 'pending',
    risk_level: 'safe',
    risk_score: 10,
    fidelity_score: 0.92,
    equivalence_score: 0.91,
    author_name: 'alice',
    license_spdx: 'MIT',
    source_url: '',
    source_checksum: 'abc',
    source_type: 'github',
    version: '1.0.0',
    created_at: '2026-04-03T00:00:00Z',
    updated_at: '2026-04-03T00:00:00Z',
  },
  {
    skill_id: 'sk_002',
    current_revision_id: 'rev_002',
    revision_id: 'rev_002',
    revision_number: 1,
    name: 'Risky Skill',
    status: 'pending',
    risk_level: 'high',
    risk_score: 87,
    fidelity_score: 0.61,
    equivalence_score: 0.6,
    author_name: 'bob',
    license_spdx: 'Apache-2.0',
    source_url: '',
    source_checksum: 'def',
    source_type: 'github',
    version: '1.0.0',
    created_at: '2026-04-03T00:00:00Z',
    updated_at: '2026-04-03T00:00:00Z',
  },
];

vi.mock('@/api/reviews', () => ({
  usePendingReviews: () => ({
    data: pendingSkills,
    isLoading: false,
  }),
  useApproveSkill: () => ({
    mutate: mockApproveMutate,
    mutateAsync: mockApproveMutateAsync,
    isPending: false,
  }),
  useRejectSkill: () => ({
    mutate: mockRejectMutate,
    mutateAsync: mockRejectMutateAsync,
    isPending: false,
  }),
}));

vi.mock('@/api/skills', () => ({
  useEnqueueScanJob: () => ({
    mutateAsync: mockEnqueueScanMutateAsync,
    isPending: false,
  }),
  useEnqueueTestJob: () => ({
    mutateAsync: mockEnqueueTestMutateAsync,
    isPending: false,
  }),
  useRetryActionJobFailures: () => ({
    mutateAsync: mockRetryFailuresMutateAsync,
    isPending: false,
  }),
  useActionJob: () => ({ data: currentActionJob }),
  useActionJobItems: () => ({ data: currentActionJobItems }),
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ReviewQueue />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ReviewQueue async action jobs', () => {
  beforeEach(() => {
    mockApproveMutate.mockReset();
    mockApproveMutateAsync.mockReset();
    mockRejectMutate.mockReset();
    mockRejectMutateAsync.mockReset();
    mockEnqueueScanMutateAsync.mockReset();
    mockEnqueueTestMutateAsync.mockReset();
    mockRetryFailuresMutateAsync.mockReset();
    currentActionJob = undefined;
    currentActionJobItems = [];

    mockEnqueueScanMutateAsync.mockImplementation(async () => {
      currentActionJob = {
        job_id: 'job_scan_001',
        job_type: 'scan_batch',
        status: 'queued',
        requested_by: 'tester',
        selection_mode: 'explicit',
        queued_items: 2,
        max_attempts: 2,
        queued_at: '2026-04-03T00:00:00Z',
        started_at: null,
        completed_at: null,
        error_code: null,
        error_message: null,
        summary: {
          total: 2,
          queued: 2,
          running: 0,
          succeeded: 0,
          failed: 0,
          retrying: 0,
          skipped: 0,
        },
      };
      currentActionJobItems = [
        {
          item_id: 'job_scan_001_item_sk_001_01',
          job_id: 'job_scan_001',
          skill_id: 'sk_001',
          target_revision_id: 'rev_001',
          action_type: 'scan',
          status: 'queued',
          attempt_number: 1,
          max_attempts: 2,
          started_at: null,
          completed_at: null,
          result: null,
          error_code: null,
          error_message: null,
          retry_of_item_id: null,
        },
        {
          item_id: 'job_scan_001_item_sk_002_01',
          job_id: 'job_scan_001',
          skill_id: 'sk_002',
          target_revision_id: 'rev_002',
          action_type: 'scan',
          status: 'queued',
          attempt_number: 1,
          max_attempts: 2,
          started_at: null,
          completed_at: null,
          result: null,
          error_code: null,
          error_message: null,
          retry_of_item_id: null,
        },
      ];
      return { job_id: 'job_scan_001' };
    });

    mockEnqueueTestMutateAsync.mockResolvedValue({ job_id: 'job_test_001' });
    mockRetryFailuresMutateAsync.mockImplementation(async () => {
      currentActionJob = {
        job_id: 'job_scan_retry_001',
        job_type: 'scan_batch',
        status: 'queued',
        requested_by: 'tester',
        selection_mode: 'retry_failures',
        queued_items: 1,
        max_attempts: 2,
        queued_at: '2026-04-03T00:05:00Z',
        started_at: null,
        completed_at: null,
        error_code: null,
        error_message: null,
        summary: {
          total: 1,
          queued: 1,
          running: 0,
          succeeded: 0,
          failed: 0,
          retrying: 0,
          skipped: 0,
        },
      };
      currentActionJobItems = [
        {
          item_id: 'job_scan_retry_001_item_sk_002_02',
          job_id: 'job_scan_retry_001',
          skill_id: 'sk_002',
          target_revision_id: 'rev_002',
          action_type: 'scan',
          status: 'retrying',
          attempt_number: 2,
          max_attempts: 2,
          started_at: null,
          completed_at: null,
          result: null,
          error_code: null,
          error_message: null,
          retry_of_item_id: 'job_scan_001_item_sk_002_01',
        },
      ];
      return { job_id: 'job_scan_retry_001' };
    });
  });

  it('enqueues a batch scan job from the review queue', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Scan Pending (2)' }));

    expect(mockEnqueueScanMutateAsync).toHaveBeenCalledWith({
      skill_ids: ['sk_001', 'sk_002'],
    });
    expect(await screen.findByText('Scan job queued')).toBeInTheDocument();
  });

  it('shows queued batch job details when expanded', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Scan Pending (2)' }));
    await user.click(screen.getByRole('button', { name: 'Show details' }));

    expect(screen.getByText('job_scan_001')).toBeInTheDocument();
    expect(screen.getByText('sk_001')).toBeInTheDocument();
    expect(screen.getByText('Total:')).toBeInTheDocument();
    expect(screen.getByText('Succeeded:')).toBeInTheDocument();
  });

  it('retries retriable failed batch items from the review queue', async () => {
    mockEnqueueScanMutateAsync.mockImplementation(async () => {
      currentActionJob = {
        job_id: 'job_scan_001',
        job_type: 'scan_batch',
        status: 'failed',
        requested_by: 'tester',
        selection_mode: 'explicit',
        queued_items: 2,
        max_attempts: 2,
        queued_at: '2026-04-03T00:00:00Z',
        started_at: '2026-04-03T00:00:01Z',
        completed_at: '2026-04-03T00:00:02Z',
        error_code: null,
        error_message: 'scan batch failed',
        summary: {
          total: 2,
          queued: 0,
          running: 0,
          succeeded: 1,
          failed: 1,
          retrying: 0,
          skipped: 0,
        },
      };
      currentActionJobItems = [
        {
          item_id: 'job_scan_001_item_sk_001_01',
          job_id: 'job_scan_001',
          skill_id: 'sk_001',
          target_revision_id: 'rev_001',
          action_type: 'scan',
          status: 'succeeded',
          attempt_number: 1,
          max_attempts: 2,
          started_at: '2026-04-03T00:00:01Z',
          completed_at: '2026-04-03T00:00:02Z',
          result: { risk_level: 'safe', risk_score: 10 },
          error_code: null,
          error_message: null,
          retry_of_item_id: null,
        },
        {
          item_id: 'job_scan_001_item_sk_002_01',
          job_id: 'job_scan_001',
          skill_id: 'sk_002',
          target_revision_id: 'rev_002',
          action_type: 'scan',
          status: 'failed',
          attempt_number: 1,
          max_attempts: 2,
          started_at: '2026-04-03T00:00:01Z',
          completed_at: '2026-04-03T00:00:02Z',
          result: null,
          error_code: 'SCAN_RUNTIME_ERROR',
          error_message: 'scanner crash',
          retry_of_item_id: null,
        },
      ];
      return { job_id: 'job_scan_001' };
    });

    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Scan Pending (2)' }));
    await user.click(screen.getByRole('button', { name: 'Show details' }));
    await user.click(screen.getByRole('button', { name: 'Retry Failed Items (1)' }));

    expect(mockRetryFailuresMutateAsync).toHaveBeenCalledWith({ jobId: 'job_scan_001' });
    expect(await screen.findByText('Scan retry job queued')).toBeInTheDocument();
  });
});
