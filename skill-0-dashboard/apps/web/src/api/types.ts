<<<<<<< Updated upstream
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

export interface FindingsByRule {
  rule_id: string;
  rule_name: string;
  severity: string;
  count: number;
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
  source_url: string;
  source_type: string | null;
  version: string;
  created_at: string | null;
  updated_at: string;
}

export interface SecurityFinding {
  rule_id: string;
  rule_name: string;
  severity: string;
  line_number: number;
  line_content: string;
  file_path: string;
  // Context-aware fields
  original_severity: string | null;
  adjusted_severity: string | null;
  severity_changed: boolean;
  context_type: string | null;
  in_code_block: boolean;
  code_block_language: string | null;
  adjustment_reason: string | null;
  // Detection standard reference
  detection_standard: string | null;
  standard_url: string | null;
}

export interface ScanSummary {
  scan_id: string;
  scanned_at: string;
  risk_level: string;
  risk_score: number;
  findings_count: number;
}

export interface ScanListItem extends ScanSummary {
  skill_id: string;
  skill_name: string;
  files_scanned: number;
  blocked: boolean;
  blocked_reason: string | null;
}

export interface ScanDetail extends ScanSummary {
  findings: SecurityFinding[];
  files_scanned: number;
  blocked: boolean;
  blocked_reason: string | null;
  original_risk_score: number | null;
  code_blocks_found: number;
  findings_in_code_blocks: number;
  severity_adjustments: number;
  scanner_version: string | null;
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
  skill_id: string | null;
  skill_name: string | null;
  details: Record<string, unknown> | null;
}

export interface SkillDetail extends SkillSummary {
  source_path: string;
  source_commit: string | null;
  original_format: string | null;
  fetched_at: string | null;
  author_email: string | null;
  author_url: string | null;
  author_org: string | null;
  license_url: string | null;
  requires_attribution: boolean;
  commercial_allowed: boolean;
  modification_allowed: boolean;
  converted_at: string | null;
  converter_version: string | null;
  target_format: string | null;
  security_scanned_at: string | null;
  scanner_version: string | null;
  approved_by: string | null;
  approved_at: string | null;
  equivalence_tested_at: string | null;
  equivalence_passed: boolean | null;
  installed_path: string | null;
  installed_at: string | null;
  security_findings: SecurityFinding[];
  scan_history: ScanSummary[];
  test_history: TestSummary[];
  audit_events: AuditEvent[];
}

export interface AuditListResponse {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
}
=======
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
>>>>>>> Stashed changes
