import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { RuntimeGovernance } from './RuntimeGovernance';

const mocks = vi.hoisted(() => ({
  items: [] as Array<Record<string, unknown>>,
  mutateAsync: vi.fn(),
  refetch: vi.fn(),
}));

vi.mock('@/api/runtime', () => ({
  useRuntimeHitlItems: () => ({
    data: mocks.items,
    isLoading: false,
    error: null,
    refetch: mocks.refetch,
  }),
  useDecideRuntimeHitl: () => ({
    mutateAsync: mocks.mutateAsync,
    isPending: false,
  }),
  useRuntimeEvidence: () => ({
    data: {
      run_ref: { run_id: 'run-1', status: 'awaiting_approval' },
      event_count: 4,
      last_event_type: 'approval_required',
      source_event_watermark: 4,
      confidence: 1,
      counts: {},
      known_failure_patterns: [],
      element_refs: ['a_010'],
      governance_ref: {
        revision_id: 'rev-1',
        revision_number: 2,
        approved_by: 'reviewer',
      },
    },
    isLoading: false,
    error: null,
  }),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <RuntimeGovernance />
    </MemoryRouter>
  );
}

const actionItem = {
  item_id: 'item-1',
  run_id: 'run-1',
  skill_id: 'claude__skill__runtime_fixture',
  action_id: 'a_010',
  kind: 'action_approval',
  status: 'pending',
  request_summary: {
    operation: 'delete_branch',
    risk_level: 'high',
  },
  expires_at: '2026-07-17T00:00:00Z',
  created_at: '2026-07-16T00:00:00Z',
  updated_at: '2026-07-16T00:00:00Z',
};

describe('RuntimeGovernance', () => {
  beforeEach(() => {
    mocks.items = [actionItem];
    mocks.mutateAsync.mockReset();
    mocks.mutateAsync.mockResolvedValue({ item: actionItem, runId: 'run-1' });
    mocks.refetch.mockReset();
  });

  it('records an action approval without actor or automatic resume', async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByText('delete_branch')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Approve' }));
    expect(screen.getByText('Confirm governance decision')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm Approve' }));

    expect(mocks.mutateAsync).toHaveBeenCalledWith({
      itemId: 'item-1',
      runId: 'run-1',
      decision: 'approve',
      reasonCode: 'RUNTIME_REVIEW_APPROVED',
    });
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Runtime execution remains a separate operator action.'
    );
  });

  it('uses confirm_recovered for recovery items and never shows Approve', () => {
    mocks.items = [
      {
        ...actionItem,
        item_id: 'recovery-1',
        kind: 'recovery_confirmation',
        request_summary: { strategy: 'manual_approval' },
      },
    ];
    renderPage();

    expect(
      screen.getByRole('button', { name: 'Confirm recovered' })
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
  });

  it('shows governance evidence on demand', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole('button', { name: 'Evidence' }));

    expect(screen.getByText('Run evidence')).toBeInTheDocument();
    expect(screen.getByText('rev-1')).toBeInTheDocument();
    expect(screen.getByText(/approved by reviewer/)).toBeInTheDocument();
  });

  it('surfaces authorization and replay errors', async () => {
    mocks.mutateAsync.mockRejectedValueOnce({
      response: { data: { detail: 'HITL item is no longer pending' } },
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole('button', { name: 'Reject' }));
    await user.click(screen.getByRole('button', { name: 'Confirm Reject' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'HITL item is no longer pending'
    );
  });
});
