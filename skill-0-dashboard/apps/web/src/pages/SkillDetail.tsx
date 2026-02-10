<<<<<<< Updated upstream
<<<<<<< Updated upstream
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { useSkill } from '@/api/skills';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArrowLeft, Shield, TestTube, FileText, CheckCircle, XCircle, ExternalLink, Scale, Lock, User, Clock, Package } from 'lucide-react';

const riskColors: Record<string, string> = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  medium: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900',
  blocked: 'bg-gray-100 text-gray-800',
};

const statusColors: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  blocked: 'bg-gray-100 text-gray-800',
};

const severityColors: Record<string, string> = {
  critical: 'text-red-600',
  high: 'text-orange-600',
  medium: 'text-yellow-600',
  low: 'text-green-600',
  info: 'text-blue-600',
};

export function SkillDetail() {
  const { skillId } = useParams<{ skillId: string }>();
  const navigate = useNavigate();
  const { data: skill, isLoading, error } = useSkill(skillId || '');

  if (isLoading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </PageLayout>
    );
  }

  if (error || !skill) {
    return (
      <PageLayout>
        <div className="text-center py-12">
          <p className="text-red-500 mb-4">Failed to load skill details</p>
          <Button onClick={() => navigate('/skills')}>Back to Skills</Button>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate('/skills')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      </div>

      {/* Title & Status */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">{skill.name}</h1>
          <div className="flex gap-2">
            <Badge className={statusColors[skill.status]}>
              {skill.status}
            </Badge>
            <Badge className={riskColors[skill.risk_level]}>
              {skill.risk_level} ({skill.risk_score})
            </Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">Re-scan</Button>
          <Button variant="outline" size="sm">Re-test</Button>
          {skill.status === 'pending' && (
            <>
              <Button variant="default" size="sm" className="bg-green-600 hover:bg-green-700">Approve</Button>
              <Button variant="destructive" size="sm">Reject</Button>
            </>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Metadata */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Metadata
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Author</span>
              <span>{skill.author_name}</span>
            </div>
            {skill.author_email && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Email</span>
                <a href={`mailto:${skill.author_email}`} className="text-blue-600 hover:text-blue-800">
                  {skill.author_email}
                </a>
              </div>
            )}
            {skill.author_org && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Organization</span>
                <span>{skill.author_org}</span>
              </div>
            )}
            {skill.author_url && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Author URL</span>
                <a href={skill.author_url} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
                  Link <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Source</span>
              {skill.source_url ? (
                <a
                  href={skill.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors"
                >
                  Original
                  <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <span>{skill.source_type}</span>
              )}
            </div>
            {skill.source_path && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Path</span>
                <span className="text-sm font-mono truncate max-w-[200px]" title={skill.source_path}>
                  {skill.source_path}
                </span>
              </div>
            )}
            {skill.source_commit && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Commit</span>
                <span className="text-sm font-mono">{skill.source_commit.slice(0, 8)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version</span>
              <span>{skill.version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span>{new Date(skill.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Updated</span>
              <span>{new Date(skill.updated_at).toLocaleDateString()}</span>
            </div>
          </CardContent>
        </Card>

        {/* Equivalence */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TestTube className="h-5 w-5" />
              Equivalence Testing
            </CardTitle>
          </CardHeader>
          <CardContent>
            {skill.equivalence_score !== null && skill.equivalence_score !== undefined && (
              <div className="flex justify-between items-center mb-3">
                <span className="text-muted-foreground">Equivalence Score</span>
                <span className="text-2xl font-bold">
                  {Math.round(skill.equivalence_score * 100)}%
                </span>
              </div>
            )}
            {skill.equivalence_passed !== null && skill.equivalence_passed !== undefined && (
              <div className="flex justify-between items-center mb-3">
                <span className="text-muted-foreground">Result</span>
                {skill.equivalence_passed ? (
                  <span className="flex items-center gap-1 text-green-600">
                    <CheckCircle className="h-4 w-4" /> Passed
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-red-600">
                    <XCircle className="h-4 w-4" /> Failed
                  </span>
                )}
              </div>
            )}
            {skill.test_history && skill.test_history.length > 0 ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Latest Score</span>
                  <span className="text-2xl font-bold">
                    {Math.round((skill.test_history[0].overall_score || 0) * 100)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Semantic</span>
                  <span>{Math.round((skill.test_history[0].semantic_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Structure</span>
                  <span>{Math.round((skill.test_history[0].structure_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Keywords</span>
                  <span>{Math.round((skill.test_history[0].keyword_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Status</span>
                  {skill.test_history[0].passed ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle className="h-4 w-4" /> Passed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-600">
                      <XCircle className="h-4 w-4" /> Failed
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No equivalence tests yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* License & Governance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* License */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scale className="h-5 w-5" />
              License & Rights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">License</span>
              <span className="font-medium">{skill.license_spdx}</span>
            </div>
            {skill.license_url && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">License URL</span>
                <a href={skill.license_url} target="_blank" rel="noopener noreferrer"
                   className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800">
                  View <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Attribution Required</span>
              <Badge className={skill.requires_attribution ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'}>
                {skill.requires_attribution ? 'Yes' : 'No'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Commercial Use</span>
              <Badge className={skill.commercial_allowed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                {skill.commercial_allowed ? 'Allowed' : 'Not Allowed'}
              </Badge>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Modification</span>
              <Badge className={skill.modification_allowed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                {skill.modification_allowed ? 'Allowed' : 'Not Allowed'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Governance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Governance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {skill.approved_by && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Approved By</span>
                <span className="flex items-center gap-1">
                  <User className="h-3 w-3" /> {skill.approved_by}
                </span>
              </div>
            )}
            {skill.approved_at && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Approved At</span>
                <span>{new Date(skill.approved_at).toLocaleString()}</span>
              </div>
            )}
            {skill.security_scanned_at && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Last Scan</span>
                <span>{new Date(skill.security_scanned_at).toLocaleString()}</span>
              </div>
            )}
            {skill.scanner_version && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Scanner Version</span>
                <span className="font-mono text-sm">{skill.scanner_version}</span>
              </div>
            )}
            {skill.installed_path && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Installed At</span>
                <span className="text-sm font-mono truncate max-w-[200px]" title={skill.installed_path}>
                  {skill.installed_path}
                </span>
              </div>
            )}
            {skill.installed_at && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Install Date</span>
                <span>{new Date(skill.installed_at).toLocaleString()}</span>
              </div>
            )}
            {!skill.approved_by && !skill.security_scanned_at && !skill.installed_path && (
              <p className="text-muted-foreground">No governance data recorded</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Security Findings */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security Findings ({skill.security_findings?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {skill.security_findings && skill.security_findings.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Context</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Content</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {skill.security_findings.map((finding, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <div className="font-medium">{finding.rule_id}</div>
                      <div className="text-sm text-muted-foreground">{finding.rule_name}</div>
                      {finding.detection_standard && (
                        <div className="text-xs text-muted-foreground mt-1">
                          {finding.standard_url ? (
                            <a href={finding.standard_url} target="_blank" rel="noopener noreferrer"
                               className="text-blue-600 hover:text-blue-800"
                               onClick={(e) => e.stopPropagation()}>
                              {finding.detection_standard}
                            </a>
                          ) : (
                            <span>{finding.detection_standard}</span>
                          )}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <span className={severityColors[finding.severity] || 'text-gray-600'}>
                        {finding.severity}
                      </span>
                      {finding.severity_changed && finding.original_severity && (
                        <div className="text-xs text-muted-foreground mt-1">
                          was: {finding.original_severity}
                          {finding.adjustment_reason && (
                            <span className="block">{finding.adjustment_reason}</span>
                          )}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      {finding.context_type && (
                        <Badge variant="outline" className="text-xs">
                          {finding.context_type}
                        </Badge>
                      )}
                      {finding.in_code_block && (
                        <Badge variant="outline" className="text-xs ml-1 bg-slate-50">
                          {finding.code_block_language || 'code'}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {finding.file_path && (
                        <span className="text-sm">
                          {finding.file_path}:{finding.line_number}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                        {finding.line_content?.slice(0, 50)}
                        {(finding.line_content?.length || 0) > 50 && '...'}
                      </code>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              No security findings
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scan History */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Scan History</CardTitle>
        </CardHeader>
        <CardContent>
          {skill.scan_history && skill.scan_history.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Findings</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {skill.scan_history.map((scan) => (
                  <TableRow key={scan.scan_id}>
                    <TableCell>{new Date(scan.scanned_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={riskColors[scan.risk_level]}>
                        {scan.risk_level}
                      </Badge>
                    </TableCell>
                    <TableCell>{scan.risk_score}</TableCell>
                    <TableCell>{scan.findings_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground">No scan history</p>
          )}
        </CardContent>
      </Card>

      {/* Audit Log */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {skill.audit_events && skill.audit_events.length > 0 ? (
            <div className="space-y-3">
              {skill.audit_events.slice(0, 10).map((event) => (
                <div key={event.event_id} className="flex items-start gap-3 text-sm">
                  <span className="text-muted-foreground whitespace-nowrap">
                    {new Date(event.timestamp).toLocaleString()}
                  </span>
                  <span className="font-medium uppercase text-xs bg-slate-100 px-2 py-1 rounded">
                    {event.event_type}
                  </span>
                  <span className="text-muted-foreground">by {event.actor}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No activity recorded</p>
          )}
        </CardContent>
      </Card>
    </PageLayout>
  );
}
=======
=======
>>>>>>> Stashed changes
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { useSkill } from '@/api/skills';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ArrowLeft, Shield, TestTube, FileText, CheckCircle, XCircle } from 'lucide-react';

const riskColors: Record<string, string> = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-yellow-100 text-yellow-800',
  medium: 'bg-orange-100 text-orange-800',
  high: 'bg-red-100 text-red-800',
  critical: 'bg-red-200 text-red-900',
  blocked: 'bg-gray-100 text-gray-800',
};

const statusColors: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-green-100 text-green-800',
  rejected: 'bg-red-100 text-red-800',
  blocked: 'bg-gray-100 text-gray-800',
};

const severityColors: Record<string, string> = {
  critical: 'text-red-600',
  high: 'text-orange-600',
  medium: 'text-yellow-600',
  low: 'text-green-600',
  info: 'text-blue-600',
};

export function SkillDetail() {
  const { skillId } = useParams<{ skillId: string }>();
  const navigate = useNavigate();
  const { data: skill, isLoading, error } = useSkill(skillId || '');

  if (isLoading) {
    return (
      <PageLayout>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-slate-900" />
        </div>
      </PageLayout>
    );
  }

  if (error || !skill) {
    return (
      <PageLayout>
        <div className="text-center py-12">
          <p className="text-red-500 mb-4">Failed to load skill details</p>
          <Button onClick={() => navigate('/skills')}>Back to Skills</Button>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="sm" onClick={() => navigate('/skills')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      </div>

      {/* Title & Status */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold mb-2">{skill.name}</h1>
          <div className="flex gap-2">
            <Badge className={statusColors[skill.status]}>
              {skill.status}
            </Badge>
            <Badge className={riskColors[skill.risk_level]}>
              {skill.risk_level} ({skill.risk_score})
            </Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">Re-scan</Button>
          <Button variant="outline" size="sm">Re-test</Button>
          {skill.status === 'pending' && (
            <>
              <Button variant="default" size="sm" className="bg-green-600 hover:bg-green-700">Approve</Button>
              <Button variant="destructive" size="sm">Reject</Button>
            </>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Metadata */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Metadata
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Author</span>
              <span>{skill.author_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">License</span>
              <span>{skill.license_spdx}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Source</span>
              <span>{skill.source_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Version</span>
              <span>{skill.version || '1.0.0'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Created</span>
              <span>{new Date(skill.created_at).toLocaleDateString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Updated</span>
              <span>{new Date(skill.updated_at).toLocaleDateString()}</span>
            </div>
          </CardContent>
        </Card>

        {/* Equivalence */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TestTube className="h-5 w-5" />
              Equivalence Testing
            </CardTitle>
          </CardHeader>
          <CardContent>
            {skill.test_history && skill.test_history.length > 0 ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Overall Score</span>
                  <span className="text-2xl font-bold">
                    {Math.round((skill.test_history[0].overall_score || 0) * 100)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Semantic</span>
                  <span>{Math.round((skill.test_history[0].semantic_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Structure</span>
                  <span>{Math.round((skill.test_history[0].structure_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Keywords</span>
                  <span>{Math.round((skill.test_history[0].keyword_similarity || 0) * 100)}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Status</span>
                  {skill.test_history[0].passed ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle className="h-4 w-4" /> Passed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-600">
                      <XCircle className="h-4 w-4" /> Failed
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">No equivalence tests yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Security Findings */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Security Findings ({skill.security_findings?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {skill.security_findings && skill.security_findings.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Location</TableHead>
                  <TableHead>Content</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {skill.security_findings.map((finding, idx) => (
                  <TableRow key={idx}>
                    <TableCell>
                      <div className="font-medium">{finding.rule_id}</div>
                      <div className="text-sm text-muted-foreground">{finding.rule_name}</div>
                    </TableCell>
                    <TableCell>
                      <span className={severityColors[finding.severity] || 'text-gray-600'}>
                        {finding.severity}
                      </span>
                    </TableCell>
                    <TableCell>
                      {finding.file_path && (
                        <span className="text-sm">
                          {finding.file_path}:{finding.line_number}
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-slate-100 px-2 py-1 rounded">
                        {finding.line_content?.slice(0, 50)}
                        {(finding.line_content?.length || 0) > 50 && '...'}
                      </code>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-5 w-5" />
              No security findings
            </div>
          )}
        </CardContent>
      </Card>

      {/* Scan History */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Scan History</CardTitle>
        </CardHeader>
        <CardContent>
          {skill.scan_history && skill.scan_history.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Risk Level</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Findings</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {skill.scan_history.map((scan) => (
                  <TableRow key={scan.scan_id}>
                    <TableCell>{new Date(scan.scanned_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Badge className={riskColors[scan.risk_level]}>
                        {scan.risk_level}
                      </Badge>
                    </TableCell>
                    <TableCell>{scan.risk_score}</TableCell>
                    <TableCell>{scan.findings_count}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <p className="text-muted-foreground">No scan history</p>
          )}
        </CardContent>
      </Card>

      {/* Audit Log */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {skill.audit_events && skill.audit_events.length > 0 ? (
            <div className="space-y-3">
              {skill.audit_events.slice(0, 10).map((event) => (
                <div key={event.event_id} className="flex items-start gap-3 text-sm">
                  <span className="text-muted-foreground whitespace-nowrap">
                    {new Date(event.timestamp).toLocaleString()}
                  </span>
                  <span className="font-medium uppercase text-xs bg-slate-100 px-2 py-1 rounded">
                    {event.event_type}
                  </span>
                  <span className="text-muted-foreground">by {event.actor}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground">No activity recorded</p>
          )}
        </CardContent>
      </Card>
    </PageLayout>
  );
}
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
