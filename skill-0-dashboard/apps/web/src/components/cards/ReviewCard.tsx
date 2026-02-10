<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Eye, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import type { SkillSummary } from '@/api/types';

const riskColors: Record<string, string> = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  medium: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900',
  blocked: 'bg-gray-100 text-gray-800',
};

interface Props {
  skill: SkillSummary;
  onApprove: (skillId: string, reason: string) => void;
  onReject: (skillId: string, reason: string) => void;
  isApproving?: boolean;
  isRejecting?: boolean;
}

export function ReviewCard({ skill, onApprove, onReject, isApproving, isRejecting }: Props) {
  const navigate = useNavigate();
  const [showDialog, setShowDialog] = useState<'approve' | 'reject' | null>(null);
  const [reason, setReason] = useState('');

  const handleSubmit = () => {
    if (showDialog === 'approve') {
      onApprove(skill.skill_id, reason || 'Approved');
    } else if (showDialog === 'reject') {
      onReject(skill.skill_id, reason || 'Rejected');
    }
    setShowDialog(null);
    setReason('');
  };

  const isHighRisk = ['high', 'critical'].includes(skill.risk_level);

  return (
    <Card className={isHighRisk ? 'border-red-200' : ''}>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-semibold text-lg">{skill.name}</h3>
              {isHighRisk && <AlertTriangle className="h-4 w-4 text-red-500" />}
            </div>
            <div className="flex flex-wrap gap-2 mb-3">
              <Badge className={riskColors[skill.risk_level]}>
                {skill.risk_level} ({skill.risk_score})
              </Badge>
              {skill.equivalence_score !== null && (
                <Badge variant="outline">
                  {Math.round(skill.equivalence_score * 100)}% equiv
                </Badge>
              )}
              <Badge variant="outline">{skill.license_spdx}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Author: {skill.author_name}
            </p>
          </div>
          
          <div className="flex gap-2">
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => navigate(`/skills/${skill.skill_id}`)}
            >
              <Eye className="h-4 w-4 mr-1" />
              View
            </Button>
            <Button
              variant="default"
              size="sm"
              className="bg-green-600 hover:bg-green-700"
              onClick={() => setShowDialog('approve')}
              disabled={isApproving || isRejecting}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Approve
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDialog('reject')}
              disabled={isApproving || isRejecting}
            >
              <XCircle className="h-4 w-4 mr-1" />
              Reject
            </Button>
          </div>
        </div>

        {/* Inline Dialog */}
        {showDialog && (
          <div className="mt-4 p-4 bg-slate-50 rounded-lg border">
            <h4 className="font-medium mb-2">
              {showDialog === 'approve' ? 'Approve' : 'Reject'} {skill.name}
            </h4>
            {isHighRisk && showDialog === 'approve' && (
              <p className="text-sm text-red-600 mb-2">
                ⚠️ This skill has a {skill.risk_level} risk level. Are you sure?
              </p>
            )}
            <Input
              placeholder="Reason (optional)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mb-3"
            />
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" size="sm" onClick={() => setShowDialog(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant={showDialog === 'approve' ? 'default' : 'destructive'}
                className={showDialog === 'approve' ? 'bg-green-600 hover:bg-green-700' : ''}
                onClick={handleSubmit}
                disabled={isApproving || isRejecting}
              >
                {isApproving || isRejecting ? 'Processing...' : `Confirm ${showDialog}`}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Eye, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import type { SkillSummary } from '@/api/types';

const riskColors: Record<string, string> = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  medium: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900',
  blocked: 'bg-gray-100 text-gray-800',
};

interface Props {
  skill: SkillSummary;
  onApprove: (skillId: string, reason: string) => void;
  onReject: (skillId: string, reason: string) => void;
  isApproving?: boolean;
  isRejecting?: boolean;
}

export function ReviewCard({ skill, onApprove, onReject, isApproving, isRejecting }: Props) {
  const navigate = useNavigate();
  const [showDialog, setShowDialog] = useState<'approve' | 'reject' | null>(null);
  const [reason, setReason] = useState('');

  const handleSubmit = () => {
    if (showDialog === 'approve') {
      onApprove(skill.skill_id, reason || 'Approved');
    } else if (showDialog === 'reject') {
      onReject(skill.skill_id, reason || 'Rejected');
    }
    setShowDialog(null);
    setReason('');
  };

  const isHighRisk = ['high', 'critical'].includes(skill.risk_level);

  return (
    <Card className={isHighRisk ? 'border-red-200' : ''}>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="font-semibold text-lg">{skill.name}</h3>
              {isHighRisk && <AlertTriangle className="h-4 w-4 text-red-500" />}
            </div>
            <div className="flex flex-wrap gap-2 mb-3">
              <Badge className={riskColors[skill.risk_level]}>
                {skill.risk_level} ({skill.risk_score})
              </Badge>
              {skill.equivalence_score !== null && (
                <Badge variant="outline">
                  {Math.round(skill.equivalence_score * 100)}% equiv
                </Badge>
              )}
              <Badge variant="outline">{skill.license_spdx}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Author: {skill.author_name}
            </p>
          </div>
          
          <div className="flex gap-2">
            <Button 
              variant="ghost" 
              size="sm"
              onClick={() => navigate(`/skills/${skill.skill_id}`)}
            >
              <Eye className="h-4 w-4 mr-1" />
              View
            </Button>
            <Button
              variant="default"
              size="sm"
              className="bg-green-600 hover:bg-green-700"
              onClick={() => setShowDialog('approve')}
              disabled={isApproving || isRejecting}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Approve
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowDialog('reject')}
              disabled={isApproving || isRejecting}
            >
              <XCircle className="h-4 w-4 mr-1" />
              Reject
            </Button>
          </div>
        </div>

        {/* Inline Dialog */}
        {showDialog && (
          <div className="mt-4 p-4 bg-slate-50 rounded-lg border">
            <h4 className="font-medium mb-2">
              {showDialog === 'approve' ? 'Approve' : 'Reject'} {skill.name}
            </h4>
            {isHighRisk && showDialog === 'approve' && (
              <p className="text-sm text-red-600 mb-2">
                ⚠️ This skill has a {skill.risk_level} risk level. Are you sure?
              </p>
            )}
            <Input
              placeholder="Reason (optional)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mb-3"
            />
            <div className="flex gap-2 justify-end">
              <Button variant="ghost" size="sm" onClick={() => setShowDialog(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant={showDialog === 'approve' ? 'default' : 'destructive'}
                className={showDialog === 'approve' ? 'bg-green-600 hover:bg-green-700' : ''}
                onClick={handleSubmit}
                disabled={isApproving || isRejecting}
              >
                {isApproving || isRejecting ? 'Processing...' : `Confirm ${showDialog}`}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
