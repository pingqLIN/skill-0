import { useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { ReviewCard } from '@/components/cards/ReviewCard';
import { usePendingReviews, useApproveSkill, useRejectSkill } from '@/api/reviews';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle } from 'lucide-react';

type FilterType = 'all' | 'safe' | 'risky';

interface Feedback {
  message: string;
  type: 'success' | 'error';
}

export function ReviewQueue() {
  const [filter, setFilter] = useState<FilterType>('all');
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const { data: skills, isLoading } = usePendingReviews();
  const approveMutation = useApproveSkill();
  const rejectMutation = useRejectSkill();

  const filteredSkills = skills?.filter(skill => {
    if (filter === 'safe') return ['safe', 'low'].includes(skill.risk_level);
    if (filter === 'risky') return ['medium', 'high', 'critical'].includes(skill.risk_level);
    return true;
  }) || [];

  const safeCount = skills?.filter(s => ['safe', 'low'].includes(s.risk_level)).length || 0;
  const riskyCount = skills?.filter(s => ['medium', 'high', 'critical'].includes(s.risk_level)).length || 0;

  const extractErrorDetail = (err: unknown) =>
    (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;

  const handleApprove = (skillId: string, reason: string) => {
    approveMutation.mutate({ skillId, reason }, {
      onSuccess: (data) => setFeedback({ message: `Skill ${data.skill_id}: ${data.status}`, type: 'success' }),
      onError: (err: unknown) => {
        setFeedback({ message: extractErrorDetail(err) || 'Approve failed', type: 'error' });
      },
    });
  };

  const handleReject = (skillId: string, reason: string) => {
    rejectMutation.mutate({ skillId, reason }, {
      onSuccess: (data) => setFeedback({ message: `Skill ${data.skill_id}: ${data.status}`, type: 'success' }),
      onError: (err: unknown) => {
        setFeedback({ message: extractErrorDetail(err) || 'Reject failed', type: 'error' });
      },
    });
  };

  if (isLoading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Review Queue</h1>
        {safeCount > 0 && (
          <Button variant="outline" disabled>
            <CheckCircle className="h-4 w-4 mr-2" />
            Bulk Approve Safe ({safeCount})
          </Button>
        )}
      </div>

      {/* Backend response feedback */}
      {feedback && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm flex justify-between items-center ${feedback.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
          <span>{feedback.message}</span>
          <button onClick={() => setFeedback(null)} aria-label="Dismiss feedback message" className="ml-4 font-bold">×</button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6">
        <Button
          variant={filter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('all')}
        >
          All ({skills?.length || 0})
        </Button>
        <Button
          variant={filter === 'safe' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('safe')}
        >
          Safe Only ({safeCount})
        </Button>
        <Button
          variant={filter === 'risky' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setFilter('risky')}
          className={filter === 'risky' ? 'bg-red-600 hover:bg-red-700' : ''}
        >
          Needs Review ({riskyCount})
        </Button>
      </div>

      {/* Review Cards */}
      {filteredSkills.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">All caught up!</h3>
            <p className="text-muted-foreground">No skills pending review.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredSkills.map(skill => (
            <ReviewCard
              key={skill.skill_id}
              skill={skill}
              onApprove={handleApprove}
              onReject={handleReject}
              isApproving={approveMutation.isPending}
              isRejecting={rejectMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* Summary */}
      {skills && skills.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold">{skills.length}</p>
                <p className="text-sm text-muted-foreground">Total Pending</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">{safeCount}</p>
                <p className="text-sm text-muted-foreground">Safe to Approve</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">{riskyCount}</p>
                <p className="text-sm text-muted-foreground">Needs Review</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </PageLayout>
  );
}
