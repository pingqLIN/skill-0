import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { SkillDetail } from './SkillDetail';

const mockNavigate = vi.fn();
const mockEnqueueScanMutateAsync = vi.fn();
const mockEnqueueTestMutateAsync = vi.fn();
const mockCancelJobMutateAsync = vi.fn();
const mockRetryActionJobItemMutateAsync = vi.fn();
let currentActionJob: Record<string, unknown> | undefined;
let currentActionJobItems: Array<Record<string, unknown>> = [];

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ skillId: 'sk_001' }),
    useNavigate: () => mockNavigate,
  };
});

vi.mock('@/api/skills', () => ({
  useSkill: () => ({
    data: {
      skill_id: 'sk_001',
      current_revision_id: 'rev_001',
      revision_id: 'rev_001',
      revision_number: 1,
      name: 'Test Skill',
      status: 'approved',
      risk_level: 'low',
      risk_score: 10,
      fidelity_score: 0.9,
      equivalence_score: 0.9,
      author_name: 'test',
      license_spdx: 'MIT',
      source_url: '',
      source_checksum: 'abc',
      source_type: 'github',
      version: '1.0.0',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      source_path: '/tmp/source.md',
      source_commit: null,
      original_format: null,
      fetched_at: null,
      author_email: null,
      author_url: null,
      author_org: null,
      license_url: null,
      requires_attribution: false,
      commercial_allowed: true,
      modification_allowed: true,
      converted_at: null,
      converter_version: null,
      target_format: null,
      fidelity_tested_at: null,
      security_scanned_at: null,
      scanner_version: null,
      approved_by: null,
      approved_at: null,
      fidelity_passed: null,
      equivalence_tested_at: null,
      equivalence_passed: null,
      installed_path: '/tmp/installed.md',
      installed_at: null,
      security_findings: [],
      scan_history: [],
      test_history: [],
      audit_events: [],
      revision_history: [],
    },
    isLoading: false,
    error: null,
  }),
  useSkillRevisions: () => ({ data: [] }),
  useActionReadiness: () => ({
    data: {
      skill_id: 'sk_001',
      revision_id: 'rev_001',
      can_scan: true,
      can_test: true,
      source_path_exists: true,
      installed_path_exists: true,
      reasons: [],
    },
  }),
  useEnqueueScanJob: () => ({
    mutateAsync: mockEnqueueScanMutateAsync,
    isPending: false,
  }),
  useEnqueueTestJob: () => ({
    mutateAsync: mockEnqueueTestMutateAsync,
    isPending: false,
  }),
  useCancelActionJob: () => ({
    mutateAsync: mockCancelJobMutateAsync,
    isPending: false,
  }),
  useRetryActionJobItem: () => ({
    mutateAsync: mockRetryActionJobItemMutateAsync,
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
        <SkillDetail />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SkillDetail async action jobs', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockEnqueueScanMutateAsync.mockReset();
    mockEnqueueTestMutateAsync.mockReset();
    mockCancelJobMutateAsync.mockReset();
    mockRetryActionJobItemMutateAsync.mockReset();
    currentActionJob = undefined;
    currentActionJobItems = [];
    mockEnqueueScanMutateAsync.mockImplementation(async () => {
      currentActionJob = {
        job_id: 'job_scan_001',
        job_type: 'scan_batch',
        status: 'queued',
        requested_by: 'testuser',
        selection_mode: 'explicit',
        queued_items: 1,
        max_attempts: 2,
        queued_at: '2026-04-02T12:00:00Z',
        started_at: null,
        completed_at: null,
        cancelled_at: null,
        cancelled_by: null,
        error_code: null,
        error_message: null,
        active_workers: [],
        active_lease_expires_at: null,
        last_item_started_at: null,
        last_item_completed_at: null,
        summary: {
          total: 1,
          queued: 1,
          running: 0,
          succeeded: 0,
          failed: 0,
          retrying: 0,
          skipped: 0,
          cancelled: 0,
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
          claimed_by: null,
          lease_expires_at: null,
          result: null,
          error_code: null,
          error_message: null,
          retry_of_item_id: null,
        },
      ];
      return { job_id: 'job_scan_001' };
    });
    mockEnqueueTestMutateAsync.mockResolvedValue({ job_id: 'job_test_001' });
    mockCancelJobMutateAsync.mockImplementation(async ({ jobId }: { jobId: string }) => {
      currentActionJob = {
        ...(currentActionJob ?? {}),
        job_id: jobId,
        job_type: 'scan_batch',
        status: 'cancelled',
        requested_by: 'testuser',
        selection_mode: 'explicit',
        queued_items: 1,
        max_attempts: 2,
        queued_at: '2026-04-02T12:00:00Z',
        started_at: '2026-04-02T12:00:01Z',
        completed_at: '2026-04-02T12:00:05Z',
        cancelled_at: '2026-04-02T12:00:05Z',
        cancelled_by: 'testuser',
        error_code: 'JOB_CANCELLED',
        error_message: 'Action job cancelled by testuser',
        active_workers: [],
        active_lease_expires_at: null,
        last_item_started_at: '2026-04-02T12:00:01Z',
        last_item_completed_at: '2026-04-02T12:00:05Z',
        summary: {
          total: 1,
          queued: 0,
          running: 0,
          succeeded: 0,
          failed: 0,
          retrying: 0,
          skipped: 0,
          cancelled: 1,
        },
      };
      currentActionJobItems = currentActionJobItems.map((item) => ({
        ...item,
        status: 'cancelled',
        error_code: 'JOB_CANCELLED',
        error_message: 'Action job cancelled by testuser',
      }));
      return currentActionJob;
    });
    mockRetryActionJobItemMutateAsync.mockImplementation(async () => {
      currentActionJob = {
        job_id: 'job_scan_retry_001',
        job_type: 'scan_batch',
        status: 'queued',
        requested_by: 'testuser',
        selection_mode: 'retry_item',
        queued_items: 1,
        max_attempts: 2,
        queued_at: '2026-04-02T12:05:00Z',
        started_at: null,
        completed_at: null,
        cancelled_at: null,
        cancelled_by: null,
        error_code: null,
        error_message: null,
        active_workers: [],
        active_lease_expires_at: null,
        last_item_started_at: null,
        last_item_completed_at: null,
        summary: {
          total: 1,
          queued: 1,
          running: 0,
          succeeded: 0,
          failed: 0,
          retrying: 0,
          skipped: 0,
          cancelled: 0,
        },
      };
      currentActionJobItems = [
        {
          item_id: 'job_scan_retry_001_item_sk_001_02',
          job_id: 'job_scan_retry_001',
          skill_id: 'sk_001',
          target_revision_id: 'rev_001',
          action_type: 'scan',
          status: 'queued',
          attempt_number: 2,
          max_attempts: 2,
          started_at: null,
          completed_at: null,
          claimed_by: null,
          lease_expires_at: null,
          result: null,
          error_code: null,
          error_message: null,
          retry_of_item_id: 'job_scan_001_item_sk_001_01',
        },
      ];
      return { job_id: 'job_scan_retry_001' };
    });
  });

  it('enqueues a scan job from the detail page', async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Re-scan' }));

    expect(mockEnqueueScanMutateAsync).toHaveBeenCalledWith({ skill_ids: ['sk_001'] });
    expect(await screen.findByText('Scan job queued')).toBeInTheDocument();
  });

  it('shows queued job details when expanded', async () => {
    currentActionJob = {
      job_id: 'job_scan_001',
      job_type: 'scan_batch',
      status: 'running',
      requested_by: 'testuser',
      selection_mode: 'explicit',
      queued_items: 1,
      max_attempts: 2,
      queued_at: '2026-04-02T12:00:00Z',
      started_at: '2026-04-02T12:00:01Z',
      completed_at: null,
      cancelled_at: null,
      cancelled_by: null,
      error_code: null,
      error_message: null,
      active_workers: ['worker-skill-detail'],
      active_lease_expires_at: '2026-04-02T12:05:01Z',
      last_item_started_at: '2026-04-02T12:00:01Z',
      last_item_completed_at: null,
      summary: {
        total: 1,
        queued: 0,
        running: 1,
        succeeded: 0,
        failed: 0,
        retrying: 0,
        skipped: 0,
        cancelled: 0,
      },
    };
    currentActionJobItems = [
      {
        item_id: 'job_scan_001_item_sk_001_01',
        job_id: 'job_scan_001',
        skill_id: 'sk_001',
        target_revision_id: 'rev_001',
        action_type: 'scan',
        status: 'running',
        attempt_number: 1,
        max_attempts: 2,
        started_at: '2026-04-02T12:00:01Z',
        completed_at: null,
        claimed_by: 'worker-skill-detail',
        lease_expires_at: '2026-04-02T12:05:01Z',
        result: null,
        error_code: null,
        error_message: null,
        retry_of_item_id: null,
      },
    ];

    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Show details' }));

    expect(screen.getByText('job_scan_001')).toBeInTheDocument();
    expect(screen.getAllByText('running')).toHaveLength(2);
    expect(screen.getByText('1/2')).toBeInTheDocument();
    expect(screen.getAllByText('worker-skill-detail')).toHaveLength(2);
    expect(screen.getAllByText('2026-04-02T12:05:01Z')).toHaveLength(2);
    expect(screen.getByText(/Active workers:/)).toBeInTheDocument();
    expect(screen.getByText(/Lease horizon:/)).toBeInTheDocument();
  });

  it('retries a retriable failed item from the detail page', async () => {
    currentActionJob = {
      job_id: 'job_scan_001',
      job_type: 'scan_batch',
      status: 'failed',
      requested_by: 'testuser',
      selection_mode: 'explicit',
      queued_items: 1,
      max_attempts: 2,
      queued_at: '2026-04-02T12:00:00Z',
      started_at: '2026-04-02T12:00:01Z',
      completed_at: '2026-04-02T12:00:02Z',
      cancelled_at: null,
      cancelled_by: null,
      error_code: null,
      error_message: null,
      active_workers: [],
      active_lease_expires_at: null,
      last_item_started_at: '2026-04-02T12:00:01Z',
      last_item_completed_at: '2026-04-02T12:00:02Z',
      summary: {
        total: 1,
        queued: 0,
        running: 0,
        succeeded: 0,
        failed: 1,
        retrying: 0,
        skipped: 0,
        cancelled: 0,
      },
    };
    currentActionJobItems = [
      {
        item_id: 'job_scan_001_item_sk_001_01',
        job_id: 'job_scan_001',
        skill_id: 'sk_001',
        target_revision_id: 'rev_001',
        action_type: 'scan',
        status: 'failed',
        attempt_number: 1,
        max_attempts: 2,
        started_at: '2026-04-02T12:00:01Z',
        completed_at: '2026-04-02T12:00:02Z',
        claimed_by: null,
        lease_expires_at: null,
        result: null,
        error_code: 'SCAN_RUNTIME_ERROR',
        error_message: 'scanner crash',
        retry_of_item_id: null,
      },
    ];

    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Show details' }));
    await user.click(screen.getByRole('button', { name: 'Retry failed item' }));

    expect(mockRetryActionJobItemMutateAsync).toHaveBeenCalledWith({
      jobId: 'job_scan_001',
      itemId: 'job_scan_001_item_sk_001_01',
    });
    expect(await screen.findByText('Scan retry job queued')).toBeInTheDocument();
  });

  it('cancels an active job from the detail page', async () => {
    currentActionJob = {
      job_id: 'job_scan_001',
      job_type: 'scan_batch',
      status: 'running',
      requested_by: 'testuser',
      selection_mode: 'explicit',
      queued_items: 1,
      max_attempts: 2,
      queued_at: '2026-04-02T12:00:00Z',
      started_at: '2026-04-02T12:00:01Z',
      completed_at: null,
      cancelled_at: null,
      cancelled_by: null,
      error_code: null,
      error_message: null,
      active_workers: ['worker-skill-detail'],
      active_lease_expires_at: '2026-04-02T12:05:01Z',
      last_item_started_at: '2026-04-02T12:00:01Z',
      last_item_completed_at: null,
      summary: {
        total: 1,
        queued: 0,
        running: 1,
        succeeded: 0,
        failed: 0,
        retrying: 0,
        skipped: 0,
        cancelled: 0,
      },
    };
    currentActionJobItems = [
      {
        item_id: 'job_scan_001_item_sk_001_01',
        job_id: 'job_scan_001',
        skill_id: 'sk_001',
        target_revision_id: 'rev_001',
        action_type: 'scan',
        status: 'running',
        attempt_number: 1,
        max_attempts: 2,
        started_at: '2026-04-02T12:00:01Z',
        completed_at: null,
        claimed_by: 'worker-skill-detail',
        lease_expires_at: '2026-04-02T12:05:01Z',
        result: null,
        error_code: null,
        error_message: null,
        retry_of_item_id: null,
      },
    ];

    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole('button', { name: 'Cancel job' }));

    expect(mockCancelJobMutateAsync).toHaveBeenCalledWith({ jobId: 'job_scan_001' });
    expect(await screen.findByText('Scan job cancelled')).toBeInTheDocument();
  });
});
