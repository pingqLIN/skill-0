export interface StatsOverview {
  total_skills: number;
  pending_count: number;
  approved_count: number;
  rejected_count: number;
  blocked_count: number;
  high_risk_count: number;
  avg_equivalence_score: number;
}

export interface RiskDistribution {
  safe: number;
  low: number;
  medium: number;
  high: number;
  critical: number;
  blocked: number;
}

export interface StatusDistribution {
  pending: number;
  approved: number;
  rejected: number;
  blocked: number;
}

export interface SkillSummary {
  skill_id: string;
  name: string;
  status: 'pending' | 'approved' | 'rejected' | 'blocked';
  risk_level: 'safe' | 'low' | 'medium' | 'high' | 'critical' | 'blocked';
  risk_score: number;
  equivalence_score: number | null;
  author_name: string;
  license_spdx: string;
  updated_at: string;
}

export interface SecurityFinding {
  rule_id: string;
  rule_name: string;
  severity: string;
  line_number: number;
  line_content: string;
  file_path: string;
}

export interface ScanSummary {
  scan_id: string;
  scanned_at: string;
  risk_level: string;
  risk_score: number;
  findings_count: number;
}

export interface TestSummary {
  test_id: string;
  tested_at: string;
  overall_score: number;
  passed: boolean;
  semantic_similarity: number | null;
  structure_similarity: number | null;
  keyword_similarity: number | null;
}

export interface AuditEvent {
  event_id: string;
  event_type: string;
  actor: string;
  timestamp: string;
  details: string;
}

export interface SkillDetail extends SkillSummary {
  version: string;
  source_type: string;
  source_path: string;
  source_url: string;
  author_email: string | null;
  created_at: string;
  security_findings: SecurityFinding[];
  scan_history: ScanSummary[];
  test_history: TestSummary[];
  audit_events: AuditEvent[];
}
