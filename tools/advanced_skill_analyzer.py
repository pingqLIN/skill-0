<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Advanced Skill Analyzer - Context-Aware Security Scanner

This analyzer improves upon the basic skill_scanner.py by:
1. Parsing Markdown structure to identify code blocks
2. Reducing severity for patterns found in code examples
3. Tracking original vs adjusted severity for transparency
4. Providing detailed context for each finding
5. Including references to detection standards (OWASP, vigil-llm, etc.)

Usage:
    python advanced_skill_analyzer.py scan <skill_path>
    python advanced_skill_analyzer.py rescan-flagged
    python advanced_skill_analyzer.py export <skill_name> --format json|html

Author: skill-0 project
Created: 2026-01-27
"""

import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime

# Try to import markdown-it-py for better parsing
try:
    from markdown_it import MarkdownIt

    HAS_MARKDOWN_IT = True
except ImportError:
    HAS_MARKDOWN_IT = False
    print(
        "[warning] markdown-it-py not installed, using regex fallback for code block detection"
    )


# =============================================================================
# Data Classes
# =============================================================================


class Severity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    SAFE = "safe"  # 0-10
    LOW = "low"  # 11-30
    MEDIUM = "medium"  # 31-50
    HIGH = "high"  # 51-80
    CRITICAL = "critical"  # 81-99
    BLOCKED = "blocked"  # 100


class ContextType(Enum):
    """Type of context where a pattern was found"""

    PROSE = "prose"  # Normal text - full severity
    CODE_BLOCK = "code_block"  # Fenced code block (```) - reduced severity
    INLINE_CODE = "inline_code"  # Inline code (`) - reduced severity
    HEADING = "heading"  # Section heading
    BLOCKQUOTE = "blockquote"  # Quote block
    LIST_ITEM = "list_item"  # List item


@dataclass
class CodeBlockSpan:
    """Represents a code block's position in the document"""

    start_line: int
    end_line: int
    start_char: int
    end_char: int
    language: str
    content: str


@dataclass
class ContextualFinding:
    """A security finding with full context information"""

    # Core finding info
    rule_id: str
    rule_name: str
    original_severity: Severity
    adjusted_severity: Severity

    # Location
    line_number: int
    line_content: str
    char_position: int
    file_path: str

    # Context
    context_type: ContextType
    in_code_block: bool
    code_block_language: Optional[str]

    # Pattern info
    matched_pattern: str
    match_text: str

    # Explanation
    description: str
    adjustment_reason: str

    # Reference
    detection_standard: str
    standard_url: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "original_severity": self.original_severity.value,
            "adjusted_severity": self.adjusted_severity.value,
            "severity_changed": self.original_severity != self.adjusted_severity,
            "line_number": self.line_number,
            "line_content": self.line_content[:200],
            "char_position": self.char_position,
            "file_path": self.file_path,
            "context_type": self.context_type.value,
            "in_code_block": self.in_code_block,
            "code_block_language": self.code_block_language,
            "matched_pattern": self.matched_pattern,
            "match_text": self.match_text[:100],
            "description": self.description,
            "adjustment_reason": self.adjustment_reason,
            "detection_standard": self.detection_standard,
            "standard_url": self.standard_url,
        }


@dataclass
class AdvancedScanResult:
    """Complete scan result with context awareness"""

    skill_path: str
    skill_name: str
    scanned_at: str
    scanner_version: str

    # Risk assessment
    risk_level: RiskLevel
    risk_score: int
    original_risk_score: int  # Score without context adjustment

    # Findings
    findings: List[ContextualFinding] = field(default_factory=list)

    # Stats
    files_scanned: int = 0
    code_blocks_found: int = 0
    findings_in_code_blocks: int = 0
    severity_adjustments: int = 0

    # Status
    blocked: bool = False
    blocked_reason: str = ""

    # Provenance (if available)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "skill_path": self.skill_path,
            "skill_name": self.skill_name,
            "scanned_at": self.scanned_at,
            "scanner_version": self.scanner_version,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "original_risk_score": self.original_risk_score,
            "risk_reduced": self.original_risk_score - self.risk_score,
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
            "files_scanned": self.files_scanned,
            "code_blocks_found": self.code_blocks_found,
            "findings_in_code_blocks": self.findings_in_code_blocks,
            "severity_adjustments": self.severity_adjustments,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "provenance": self.provenance,
            "summary": self.get_summary(),
            "detection_standards": self.get_detection_standards(),
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        by_severity = {s.value: 0 for s in Severity}
        by_context = {c.value: 0 for c in ContextType}

        for f in self.findings:
            by_severity[f.adjusted_severity.value] += 1
            by_context[f.context_type.value] += 1

        return {
            "by_severity": by_severity,
            "by_context": by_context,
            "total_findings": len(self.findings),
            "in_code_blocks": self.findings_in_code_blocks,
            "in_prose": len(self.findings) - self.findings_in_code_blocks,
        }

    def get_detection_standards(self) -> List[Dict[str, str]]:
        """Get list of detection standards used"""
        return [
            {
                "name": "OWASP LLM Top 10 - Prompt Injection",
                "url": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
                "description": "Industry standard for LLM security vulnerabilities",
            },
            {
                "name": "Vigil-LLM YARA Rules",
                "url": "https://github.com/deadbits/vigil-llm/tree/main/data/yara",
                "description": "Pattern-based prompt injection detection rules",
            },
            {
                "name": "ProtectAI LLM Guard",
                "url": "https://github.com/protectai/llm-guard",
                "description": "ML-based and heuristic prompt injection detection",
            },
            {
                "name": "skill-0 Governance Spec",
                "url": "https://github.com/user/skill-0/blob/main/governance/GOVERNANCE.md",
                "description": "Project-specific security rules (SEC001-SEC009)",
            },
        ]


# =============================================================================
# Detection Standards Reference
# =============================================================================

DETECTION_STANDARDS = {
    "SEC001": {
        "name": "OWASP LLM01 + Vigil-LLM",
        "url": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
        "description": "Shell command injection patterns from OWASP and vigil-llm YARA rules",
    },
    "SEC002": {
        "name": "CWE-732 + Custom",
        "url": "https://cwe.mitre.org/data/definitions/732.html",
        "description": "Dangerous file operations that could cause data loss",
    },
    "SEC003": {
        "name": "OWASP Secrets Management",
        "url": "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
        "description": "Detection of hardcoded credentials and secrets",
    },
    "SEC004": {
        "name": "Vigil-LLM mdexfil.yar",
        "url": "https://github.com/deadbits/vigil-llm/blob/main/data/yara/mdexfil.yar",
        "description": "Network-based data exfiltration patterns",
    },
    "SEC005": {
        "name": "Vigil-LLM instruction_bypass.yar",
        "url": "https://github.com/deadbits/vigil-llm/blob/main/data/yara/instruction_bypass.yar",
        "description": "Prompt injection patterns that attempt to override instructions",
    },
    "SEC006": {
        "name": "CWE-269 Privilege Escalation",
        "url": "https://cwe.mitre.org/data/definitions/269.html",
        "description": "Patterns indicating privilege escalation attempts",
    },
    "SEC007": {
        "name": "Vigil-LLM mdexfil.yar",
        "url": "https://github.com/deadbits/vigil-llm/blob/main/data/yara/mdexfil.yar",
        "description": "Data exfiltration via markdown image links",
    },
    "SEC008": {
        "name": "OWASP XSS + Prototype Pollution",
        "url": "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
        "description": "Unsafe code patterns in web contexts",
    },
    "SEC009": {
        "name": "Custom - Unsafe Instructions",
        "url": "https://github.com/user/skill-0/blob/main/governance/GOVERNANCE.md#sec009",
        "description": "Instructions that encourage bypassing safety checks",
    },
}


# =============================================================================
# Markdown Context Parser
# =============================================================================


class MarkdownContextParser:
    """Parses Markdown to identify code blocks and their positions"""

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split("\n")
        self.line_offsets = self._compute_line_offsets()
        self.code_blocks: List[CodeBlockSpan] = []
        self._parse()

    def _compute_line_offsets(self) -> List[int]:
        """Compute character offset for each line start"""
        offsets = [0]
        for line in self.lines:
            offsets.append(offsets[-1] + len(line) + 1)  # +1 for newline
        return offsets

    def _parse(self):
        """Parse the markdown content to find code blocks"""
        if HAS_MARKDOWN_IT:
            self._parse_with_markdown_it()
        else:
            self._parse_with_regex()

    def _parse_with_markdown_it(self):
        """Use markdown-it-py for accurate parsing"""
        md = MarkdownIt("commonmark")
        tokens = md.parse(self.content)

        for token in tokens:
            if token.type == "fence" and token.map:
                start_line, end_line = token.map
                start_char = (
                    self.line_offsets[start_line]
                    if start_line < len(self.line_offsets)
                    else 0
                )
                end_char = (
                    self.line_offsets[end_line]
                    if end_line < len(self.line_offsets)
                    else len(self.content)
                )

                self.code_blocks.append(
                    CodeBlockSpan(
                        start_line=start_line + 1,  # 1-indexed
                        end_line=end_line,
                        start_char=start_char,
                        end_char=end_char,
                        language=token.info or "",
                        content=token.content,
                    )
                )
            elif token.type == "code_block" and token.map:
                start_line, end_line = token.map
                start_char = (
                    self.line_offsets[start_line]
                    if start_line < len(self.line_offsets)
                    else 0
                )
                end_char = (
                    self.line_offsets[end_line]
                    if end_line < len(self.line_offsets)
                    else len(self.content)
                )

                self.code_blocks.append(
                    CodeBlockSpan(
                        start_line=start_line + 1,
                        end_line=end_line,
                        start_char=start_char,
                        end_char=end_char,
                        language="",
                        content=token.content,
                    )
                )

    def _parse_with_regex(self):
        """Fallback regex-based parsing"""
        # Match fenced code blocks: ```lang ... ```
        fenced_pattern = re.compile(
            r"^(```|~~~)(\w*)\n(.*?)\n\1", re.MULTILINE | re.DOTALL
        )

        for match in fenced_pattern.finditer(self.content):
            start_char = match.start()
            end_char = match.end()

            # Find line numbers
            start_line = self.content[:start_char].count("\n") + 1
            end_line = self.content[:end_char].count("\n") + 1

            self.code_blocks.append(
                CodeBlockSpan(
                    start_line=start_line,
                    end_line=end_line,
                    start_char=start_char,
                    end_char=end_char,
                    language=match.group(2) or "",
                    content=match.group(3),
                )
            )

    def is_inside_code_block(
        self, line_number: int
    ) -> Tuple[bool, Optional[CodeBlockSpan]]:
        """Check if a line is inside a code block"""
        for block in self.code_blocks:
            if block.start_line <= line_number <= block.end_line:
                return True, block
        return False, None

    def is_position_in_code_block(
        self, char_position: int
    ) -> Tuple[bool, Optional[CodeBlockSpan]]:
        """Check if a character position is inside a code block"""
        for block in self.code_blocks:
            if block.start_char <= char_position < block.end_char:
                return True, block
        return False, None

    def get_context_type(self, line_number: int, line_content: str) -> ContextType:
        """Determine the context type for a line"""
        in_code, _ = self.is_inside_code_block(line_number)
        if in_code:
            return ContextType.CODE_BLOCK

        stripped = line_content.strip()

        # Check for inline code
        if "`" in stripped and not stripped.startswith("```"):
            # Count backticks to see if we're in inline code
            # This is a simplification - real check would need position
            pass

        if stripped.startswith("#"):
            return ContextType.HEADING
        if stripped.startswith(">"):
            return ContextType.BLOCKQUOTE
        if stripped.startswith(("-", "*", "+")) or re.match(r"^\d+\.", stripped):
            return ContextType.LIST_ITEM

        return ContextType.PROSE


# =============================================================================
# Security Rules with Context Awareness
# =============================================================================


class ContextAwareSecurityRule:
    """A security rule that considers context when determining severity"""

    # Severity reduction map for code blocks
    SEVERITY_REDUCTION = {
        Severity.CRITICAL: Severity.LOW,
        Severity.HIGH: Severity.INFO,
        Severity.MEDIUM: Severity.INFO,
        Severity.LOW: Severity.INFO,
        Severity.INFO: Severity.INFO,
    }

    def __init__(
        self,
        rule_id: str,
        name: str,
        severity: Severity,
        patterns: List[str],
        description: str,
        score_weight: int = 10,
    ):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.patterns = patterns
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.description = description
        self.score_weight = score_weight

        # Get detection standard reference
        std_info = DETECTION_STANDARDS.get(
            rule_id, {"name": "Custom Rule", "url": "", "description": description}
        )
        self.detection_standard = std_info["name"]
        self.standard_url = std_info["url"]

    def scan_with_context(
        self, content: str, parser: MarkdownContextParser, file_path: str = ""
    ) -> List[ContextualFinding]:
        """Scan content with context awareness"""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, compiled in zip(self.patterns, self.compiled_patterns):
                match = compiled.search(line)
                if match:
                    # Determine context
                    in_code, code_block = parser.is_inside_code_block(line_num)
                    context_type = parser.get_context_type(line_num, line)

                    # Determine adjusted severity
                    if in_code:
                        adjusted_severity = self.SEVERITY_REDUCTION.get(
                            self.severity, Severity.INFO
                        )
                        adjustment_reason = (
                            f"Pattern found inside code block "
                            f"({code_block.language or 'unknown'} code example). "
                            f"Severity reduced from {self.severity.value} to {adjusted_severity.value} "
                            f"as this appears to be documentation/tutorial content."
                        )
                    else:
                        adjusted_severity = self.severity
                        adjustment_reason = (
                            "Pattern found in prose text - full severity applied."
                        )

                    findings.append(
                        ContextualFinding(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            original_severity=self.severity,
                            adjusted_severity=adjusted_severity,
                            line_number=line_num,
                            line_content=line.strip(),
                            char_position=match.start(),
                            file_path=file_path,
                            context_type=context_type,
                            in_code_block=in_code,
                            code_block_language=code_block.language
                            if code_block
                            else None,
                            matched_pattern=pattern,
                            match_text=match.group(0),
                            description=self.description,
                            adjustment_reason=adjustment_reason,
                            detection_standard=self.detection_standard,
                            standard_url=self.standard_url,
                        )
                    )

        return findings


# =============================================================================
# Advanced Scanner
# =============================================================================


class AdvancedSkillAnalyzer:
    """Context-aware skill security analyzer"""

    VERSION = "2.1.0"

    # Score weights by severity
    SEVERITY_SCORES = {
        Severity.INFO: 1,
        Severity.LOW: 3,
        Severity.MEDIUM: 10,
        Severity.HIGH: 20,
        Severity.CRITICAL: 35,
    }

    # Risk level thresholds
    RISK_THRESHOLDS = [
        (10, RiskLevel.SAFE),
        (30, RiskLevel.LOW),
        (50, RiskLevel.MEDIUM),
        (80, RiskLevel.HIGH),
        (99, RiskLevel.CRITICAL),
        (100, RiskLevel.BLOCKED),
    ]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.rules = self._load_rules()

    def log(self, msg: str):
        if self.verbose:
            print(f"[analyzer] {msg}")

    def _load_rules(self) -> List[ContextAwareSecurityRule]:
        """Load context-aware security rules"""
        return [
            # SEC001: Shell Command Injection (CRITICAL)
            ContextAwareSecurityRule(
                rule_id="SEC001",
                name="Shell Command Injection",
                severity=Severity.CRITICAL,
                patterns=[
                    r"run\s+['\"][^'\"]+['\"]",
                    r"execute\s+shell",
                    r"system\s*\(['\"]",
                    r"subprocess\.call\s*\(",
                    r"subprocess\.run\s*\(",
                    r"subprocess\.Popen\s*\(",
                    r"os\.system\s*\(",
                    r"os\.popen\s*\(",
                    r"eval\s*\(['\"]",
                    r"exec\s*\(['\"]",
                    r"require\s*\(['\"]child_process",
                    r"spawn\s*\(['\"]",
                    r"execSync\s*\(",
                    r"sh\s+-c\s+['\"]",
                    r"bash\s+-c\s+['\"]",
                    r"cmd\s+/c\s+",
                    r"powershell\s+-c",
                ],
                description="Detects attempts to execute shell commands.",
                score_weight=35,
            ),
            # SEC002: Dangerous File Operations (HIGH)
            ContextAwareSecurityRule(
                rule_id="SEC002",
                name="Dangerous File Operations",
                severity=Severity.HIGH,
                patterns=[
                    r"rm\s+-rf",
                    r"rm\s+-fr",
                    r"rmdir\s+/s",
                    r"del\s+/[fqs]",
                    r"format\s+[a-z]:",
                    r"mkfs\.",
                    r"dd\s+if=",
                    r">\s*/dev/",
                    r"truncate\s+-s\s*0",
                    r"shred\s+",
                    r"Remove-Item.*-Recurse.*-Force",
                    r"shutil\.rmtree",
                ],
                description="Detects dangerous file deletion or overwrite operations.",
                score_weight=20,
            ),
            # SEC003: Credential/Secret Access (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC003",
                name="Credential/Secret Access",
                severity=Severity.MEDIUM,
                patterns=[
                    r"\bpassword\s*[=:]",
                    r"api[_-]?key\s*[=:]",
                    r"secret[_-]?key\s*[=:]",
                    r"private[_-]?key\s*[=:]",
                    r"access[_-]?token\s*[=:]",
                    r"AWS_SECRET",
                    r"AZURE_KEY",
                    r"GCP_KEY",
                ],
                description="Detects references to sensitive credentials.",
                score_weight=10,
            ),
            # SEC004: Suspicious Network Operations (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC004",
                name="Suspicious Network Operations",
                severity=Severity.MEDIUM,
                patterns=[
                    r"curl.*\|\s*sh",
                    r"curl.*\|\s*bash",
                    r"wget.*\|\s*sh",
                    r"wget.*\|\s*bash",
                    r"nc\s+-[elp]",
                    r"reverse\s*shell",
                    r"bind\s*shell",
                    r"/dev/tcp/",
                    r"Invoke-WebRequest.*\|.*Invoke-Expression",
                ],
                description="Detects suspicious network operations.",
                score_weight=10,
            ),
            # SEC005: Prompt Injection Attempt (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC005",
                name="Prompt Injection Attempt",
                severity=Severity.MEDIUM,
                patterns=[
                    r"ignore\s+(all\s+)?previous\s+instructions",
                    r"disregard\s+(the\s+)?above",
                    r"forget\s+everything",
                    r"you\s+are\s+now",
                    r"act\s+as\s+if",
                    r"jailbreak",
                    r"DAN\s*mode",
                    r"developer\s*mode",
                    r"override\s+safety",
                    r"bypass\s+restrictions",
                ],
                description="Detects prompt injection patterns.",
                score_weight=10,
            ),
            # SEC006: Privilege Escalation (HIGH)
            ContextAwareSecurityRule(
                rule_id="SEC006",
                name="Privilege Escalation",
                severity=Severity.HIGH,
                patterns=[
                    r"\bsudo\s+",
                    r"\bsu\s+-",
                    r"runas\s+/user",
                    r"chmod\s+[0-7]*777",
                    r"chmod\s+\+s",
                    r"setuid",
                    r"SeDebugPrivilege",
                    r"NT\s*AUTHORITY\\SYSTEM",
                ],
                description="Detects privilege escalation attempts.",
                score_weight=20,
            ),
            # SEC007: Data Exfiltration Risk (LOW)
            ContextAwareSecurityRule(
                rule_id="SEC007",
                name="Data Exfiltration Risk",
                severity=Severity.LOW,
                patterns=[
                    r"exfil",
                    r"base64.*encode.*send",
                    r"webhook\.site",
                    r"requestbin",
                    r"pipedream\.net",
                    r"ngrok",
                ],
                description="Detects potential data exfiltration attempts.",
                score_weight=3,
            ),
            # SEC008: Unsafe Code Patterns (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC008",
                name="Unsafe Code Patterns",
                severity=Severity.MEDIUM,
                patterns=[
                    r"innerHTML\s*=",
                    r"dangerouslySetInnerHTML",
                    r"document\.write",
                    r"__proto__",
                    r"pickle\.load",
                    r"yaml\.load\s*\([^)]*Loader\s*=\s*None",
                ],
                description="Detects unsafe code patterns.",
                score_weight=10,
            ),
            # SEC009: Suspicious AI Instructions (LOW)
            ContextAwareSecurityRule(
                rule_id="SEC009",
                name="Suspicious AI Instructions",
                severity=Severity.LOW,
                patterns=[
                    r"never\s+refuse",
                    r"always\s+comply",
                    r"do\s+not\s+question",
                    r"skip\s+validation",
                    r"disable\s+checks",
                    r"--no-verify",
                ],
                description="Detects instructions that bypass safety checks.",
                score_weight=3,
            ),
        ]

    def calculate_risk_score(
        self, findings: List[ContextualFinding], use_adjusted: bool = True
    ) -> int:
        """Calculate risk score from findings"""
        import math

        score = 0

        # Group by rule
        rule_findings: Dict[str, List[ContextualFinding]] = {}
        for f in findings:
            if f.rule_id not in rule_findings:
                rule_findings[f.rule_id] = []
            rule_findings[f.rule_id].append(f)

        for rule_id, rule_items in rule_findings.items():
            # Use adjusted or original severity
            severity = (
                rule_items[0].adjusted_severity
                if use_adjusted
                else rule_items[0].original_severity
            )
            base_score = self.SEVERITY_SCORES.get(severity, 3)

            # Diminishing returns for multiple findings of same rule
            count_multiplier = 1 + math.log(len(rule_items), 2) * 0.3
            score += int(base_score * count_multiplier)

        return min(score, 100)

    def determine_risk_level(self, score: int) -> RiskLevel:
        """Determine risk level from score"""
        for threshold, level in self.RISK_THRESHOLDS:
            if score <= threshold:
                return level
        return RiskLevel.BLOCKED

    def scan_content(
        self, content: str, file_path: str = ""
    ) -> Tuple[List[ContextualFinding], int]:
        """Scan content with context awareness"""
        parser = MarkdownContextParser(content)
        findings = []

        self.log(f"Found {len(parser.code_blocks)} code blocks")

        for rule in self.rules:
            rule_findings = rule.scan_with_context(content, parser, file_path)
            findings.extend(rule_findings)

            if rule_findings:
                in_code = sum(1 for f in rule_findings if f.in_code_block)
                self.log(
                    f"  {rule.rule_id}: {len(rule_findings)} findings ({in_code} in code blocks)"
                )

        return findings, len(parser.code_blocks)

    def scan_file(self, file_path: Path) -> Tuple[List[ContextualFinding], int]:
        """Scan a single file"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, str(file_path))
        except Exception as e:
            self.log(f"Error scanning {file_path}: {e}")
            return [], 0

    def scan_skill(self, skill_path: Path) -> AdvancedScanResult:
        """Scan a skill directory with context awareness"""
        skill_path = Path(skill_path)

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill path not found: {skill_path}")

        # Get skill name
        skill_name = skill_path.name
        skill_md = skill_path / "SKILL.md"
        provenance = {}

        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            match = re.search(r"name:\s*([^\n]+)", content)
            if match:
                skill_name = match.group(1).strip().strip("'\"")

            # Try to extract provenance
            source_match = re.search(r"source_url:\s*([^\n]+)", content)
            if source_match:
                provenance["source_url"] = source_match.group(1).strip()
            commit_match = re.search(r"source_commit:\s*([^\n]+)", content)
            if commit_match:
                provenance["source_commit"] = commit_match.group(1).strip()

        self.log(f"Scanning skill: {skill_name}")

        # Scan all files
        all_findings = []
        files_scanned = 0
        total_code_blocks = 0

        scan_patterns = ["*.md", "*.txt", "*.yaml", "*.yml"]

        if skill_path.is_file():
            findings, code_blocks = self.scan_file(skill_path)
            all_findings.extend(findings)
            files_scanned = 1
            total_code_blocks = code_blocks
        else:
            for pattern in scan_patterns:
                for file_path in skill_path.glob(f"**/{pattern}"):
                    self.log(f"  Scanning: {file_path.name}")
                    findings, code_blocks = self.scan_file(file_path)
                    all_findings.extend(findings)
                    files_scanned += 1
                    total_code_blocks += code_blocks

        # Calculate scores
        adjusted_score = self.calculate_risk_score(all_findings, use_adjusted=True)
        original_score = self.calculate_risk_score(all_findings, use_adjusted=False)

        risk_level = self.determine_risk_level(adjusted_score)

        # Count stats
        findings_in_code = sum(1 for f in all_findings if f.in_code_block)
        severity_adjustments = sum(
            1 for f in all_findings if f.original_severity != f.adjusted_severity
        )

        return AdvancedScanResult(
            skill_path=str(skill_path),
            skill_name=skill_name,
            scanned_at=datetime.now().isoformat(),
            scanner_version=self.VERSION,
            risk_level=risk_level,
            risk_score=adjusted_score,
            original_risk_score=original_score,
            findings=all_findings,
            files_scanned=files_scanned,
            code_blocks_found=total_code_blocks,
            findings_in_code_blocks=findings_in_code,
            severity_adjustments=severity_adjustments,
            blocked=(risk_level == RiskLevel.BLOCKED),
            blocked_reason="Multiple critical findings in prose"
            if risk_level == RiskLevel.BLOCKED
            else "",
            provenance=provenance,
        )

    def format_report_text(self, result: AdvancedScanResult) -> str:
        """Format result as human-readable text"""
        lines = []

        lines.append("=" * 70)
        lines.append(f"Advanced Security Scan Report: {result.skill_name}")
        lines.append("=" * 70)
        lines.append(f"Path: {result.skill_path}")
        lines.append(f"Scanned: {result.scanned_at}")
        lines.append(f"Scanner: Advanced Analyzer v{result.scanner_version}")
        lines.append("")

        # Risk assessment
        lines.append("--- RISK ASSESSMENT ---")
        lines.append(f"Risk Level: {result.risk_level.value.upper()}")
        lines.append(
            f"Risk Score: {result.risk_score}/100 (was {result.original_risk_score} before context adjustment)"
        )
        if result.original_risk_score > result.risk_score:
            lines.append(
                f"Score Reduction: -{result.original_risk_score - result.risk_score} points (context-aware)"
            )
        lines.append("")

        # Stats
        lines.append("--- SCAN STATISTICS ---")
        lines.append(f"Files Scanned: {result.files_scanned}")
        lines.append(f"Code Blocks Found: {result.code_blocks_found}")
        lines.append(f"Total Findings: {len(result.findings)}")
        lines.append(
            f"  In Code Blocks: {result.findings_in_code_blocks} (severity reduced)"
        )
        lines.append(
            f"  In Prose: {len(result.findings) - result.findings_in_code_blocks}"
        )
        lines.append(f"Severity Adjustments: {result.severity_adjustments}")
        lines.append("")

        # Findings details
        if result.findings:
            lines.append("--- FINDINGS DETAILS ---")

            for i, f in enumerate(result.findings[:20], 1):  # Limit to 20
                severity_change = ""
                if f.original_severity != f.adjusted_severity:
                    severity_change = f" (was {f.original_severity.value.upper()})"

                lines.append(f"\n[{i}] {f.rule_id}: {f.rule_name}")
                lines.append(
                    f"    Severity: {f.adjusted_severity.value.upper()}{severity_change}"
                )
                lines.append(f"    Line {f.line_number}: {f.line_content[:60]}...")
                lines.append(
                    f"    Context: {f.context_type.value}"
                    + (f" ({f.code_block_language})" if f.code_block_language else "")
                )
                lines.append(f"    Reason: {f.adjustment_reason[:80]}...")
                lines.append(f"    Standard: {f.detection_standard}")
                if f.standard_url:
                    lines.append(f"    Reference: {f.standard_url}")

            if len(result.findings) > 20:
                lines.append(f"\n... and {len(result.findings) - 20} more findings")

        # Detection standards
        lines.append("\n--- DETECTION STANDARDS USED ---")
        for std in result.get_detection_standards():
            lines.append(f"  - {std['name']}")
            lines.append(f"    {std['url']}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def format_report_json(self, result: AdvancedScanResult) -> str:
        """Format result as JSON"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Advanced Skill Security Analyzer")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan command
    scan_parser = subparsers.add_parser(
        "scan", help="Scan a skill with context awareness"
    )
    scan_parser.add_argument("skill_path", type=Path)
    scan_parser.add_argument("--format", choices=["text", "json"], default="text")
    scan_parser.add_argument("--output", type=Path)

    # compare command - compare old vs new scanner
    compare_parser = subparsers.add_parser("compare", help="Compare with basic scanner")
    compare_parser.add_argument("skill_path", type=Path)

    args = parser.parse_args()
    analyzer = AdvancedSkillAnalyzer(verbose=args.verbose)

    if args.command == "scan":
        try:
            result = analyzer.scan_skill(args.skill_path)

            if args.format == "json":
                output = analyzer.format_report_json(result)
            else:
                output = analyzer.format_report_text(result)

            if args.output:
                args.output.write_text(output, encoding="utf-8")
                print(f"Report saved to {args.output}")
            else:
                print(output)

        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

    elif args.command == "compare":
        # Import basic scanner for comparison
        try:
            from skill_scanner import SkillSecurityScanner

            basic = SkillSecurityScanner(verbose=args.verbose)
            advanced = analyzer

            basic_result = basic.scan_skill(args.skill_path)
            advanced_result = advanced.scan_skill(args.skill_path)

            print("\n=== SCANNER COMPARISON ===\n")
            print(f"Skill: {basic_result.skill_name}")
            print("")
            print("                    Basic Scanner    Advanced Analyzer")
            print(
                f"Risk Level:         {basic_result.risk_level.value:16} {advanced_result.risk_level.value}"
            )
            print(
                f"Risk Score:         {basic_result.risk_score:16} {advanced_result.risk_score}"
            )
            print(
                f"Total Findings:     {len(basic_result.findings):16} {len(advanced_result.findings)}"
            )
            print(f"Code Blocks Found:  {'N/A':16} {advanced_result.code_blocks_found}")
            print(
                f"In Code Blocks:     {'N/A':16} {advanced_result.findings_in_code_blocks}"
            )
            print(
                f"Severity Adjusted:  {'N/A':16} {advanced_result.severity_adjustments}"
            )

            if advanced_result.risk_score < basic_result.risk_score:
                print(
                    f"\n Context-aware analysis reduced risk score by {basic_result.risk_score - advanced_result.risk_score} points"
                )

        except ImportError:
            print("Error: Could not import basic scanner for comparison")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
=======
#!/usr/bin/env python3
"""
Advanced Skill Analyzer - Context-Aware Security Scanner

This analyzer improves upon the basic skill_scanner.py by:
1. Parsing Markdown structure to identify code blocks
2. Reducing severity for patterns found in code examples
3. Tracking original vs adjusted severity for transparency
4. Providing detailed context for each finding
5. Including references to detection standards (OWASP, vigil-llm, etc.)

Usage:
    python advanced_skill_analyzer.py scan <skill_path>
    python advanced_skill_analyzer.py rescan-flagged
    python advanced_skill_analyzer.py export <skill_name> --format json|html

Author: skill-0 project
Created: 2026-01-27
"""

import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Tuple, Any
from datetime import datetime

# Try to import markdown-it-py for better parsing
try:
    from markdown_it import MarkdownIt

    HAS_MARKDOWN_IT = True
except ImportError:
    HAS_MARKDOWN_IT = False
    print(
        "[warning] markdown-it-py not installed, using regex fallback for code block detection"
    )


# =============================================================================
# Data Classes
# =============================================================================


class Severity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    SAFE = "safe"  # 0-10
    LOW = "low"  # 11-30
    MEDIUM = "medium"  # 31-50
    HIGH = "high"  # 51-80
    CRITICAL = "critical"  # 81-99
    BLOCKED = "blocked"  # 100


class ContextType(Enum):
    """Type of context where a pattern was found"""

    PROSE = "prose"  # Normal text - full severity
    CODE_BLOCK = "code_block"  # Fenced code block (```) - reduced severity
    INLINE_CODE = "inline_code"  # Inline code (`) - reduced severity
    HEADING = "heading"  # Section heading
    BLOCKQUOTE = "blockquote"  # Quote block
    LIST_ITEM = "list_item"  # List item


@dataclass
class CodeBlockSpan:
    """Represents a code block's position in the document"""

    start_line: int
    end_line: int
    start_char: int
    end_char: int
    language: str
    content: str


@dataclass
class ContextualFinding:
    """A security finding with full context information"""

    # Core finding info
    rule_id: str
    rule_name: str
    original_severity: Severity
    adjusted_severity: Severity

    # Location
    line_number: int
    line_content: str
    char_position: int
    file_path: str

    # Context
    context_type: ContextType
    in_code_block: bool
    code_block_language: Optional[str]

    # Pattern info
    matched_pattern: str
    match_text: str

    # Explanation
    description: str
    adjustment_reason: str

    # Reference
    detection_standard: str
    standard_url: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "original_severity": self.original_severity.value,
            "adjusted_severity": self.adjusted_severity.value,
            "severity_changed": self.original_severity != self.adjusted_severity,
            "line_number": self.line_number,
            "line_content": self.line_content[:200],
            "char_position": self.char_position,
            "file_path": self.file_path,
            "context_type": self.context_type.value,
            "in_code_block": self.in_code_block,
            "code_block_language": self.code_block_language,
            "matched_pattern": self.matched_pattern,
            "match_text": self.match_text[:100],
            "description": self.description,
            "adjustment_reason": self.adjustment_reason,
            "detection_standard": self.detection_standard,
            "standard_url": self.standard_url,
        }


@dataclass
class AdvancedScanResult:
    """Complete scan result with context awareness"""

    skill_path: str
    skill_name: str
    scanned_at: str
    scanner_version: str

    # Risk assessment
    risk_level: RiskLevel
    risk_score: int
    original_risk_score: int  # Score without context adjustment

    # Findings
    findings: List[ContextualFinding] = field(default_factory=list)

    # Stats
    files_scanned: int = 0
    code_blocks_found: int = 0
    findings_in_code_blocks: int = 0
    severity_adjustments: int = 0

    # Status
    blocked: bool = False
    blocked_reason: str = ""

    # Provenance (if available)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "skill_path": self.skill_path,
            "skill_name": self.skill_name,
            "scanned_at": self.scanned_at,
            "scanner_version": self.scanner_version,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "original_risk_score": self.original_risk_score,
            "risk_reduced": self.original_risk_score - self.risk_score,
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
            "files_scanned": self.files_scanned,
            "code_blocks_found": self.code_blocks_found,
            "findings_in_code_blocks": self.findings_in_code_blocks,
            "severity_adjustments": self.severity_adjustments,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "provenance": self.provenance,
            "summary": self.get_summary(),
            "detection_standards": self.get_detection_standards(),
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        by_severity = {s.value: 0 for s in Severity}
        by_context = {c.value: 0 for c in ContextType}

        for f in self.findings:
            by_severity[f.adjusted_severity.value] += 1
            by_context[f.context_type.value] += 1

        return {
            "by_severity": by_severity,
            "by_context": by_context,
            "total_findings": len(self.findings),
            "in_code_blocks": self.findings_in_code_blocks,
            "in_prose": len(self.findings) - self.findings_in_code_blocks,
        }

    def get_detection_standards(self) -> List[Dict[str, str]]:
        """Get list of detection standards used"""
        return [
            {
                "name": "OWASP LLM Top 10 - Prompt Injection",
                "url": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
                "description": "Industry standard for LLM security vulnerabilities",
            },
            {
                "name": "Vigil-LLM YARA Rules",
                "url": "https://github.com/deadbits/vigil-llm/tree/main/data/yara",
                "description": "Pattern-based prompt injection detection rules",
            },
            {
                "name": "ProtectAI LLM Guard",
                "url": "https://github.com/protectai/llm-guard",
                "description": "ML-based and heuristic prompt injection detection",
            },
            {
                "name": "skill-0 Governance Spec",
                "url": "https://github.com/user/skill-0/blob/main/governance/GOVERNANCE.md",
                "description": "Project-specific security rules (SEC001-SEC009)",
            },
        ]


# =============================================================================
# Detection Standards Reference
# =============================================================================

DETECTION_STANDARDS = {
    "SEC001": {
        "name": "OWASP LLM01 + Vigil-LLM",
        "url": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/",
        "description": "Shell command injection patterns from OWASP and vigil-llm YARA rules",
    },
    "SEC002": {
        "name": "CWE-732 + Custom",
        "url": "https://cwe.mitre.org/data/definitions/732.html",
        "description": "Dangerous file operations that could cause data loss",
    },
    "SEC003": {
        "name": "OWASP Secrets Management",
        "url": "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
        "description": "Detection of hardcoded credentials and secrets",
    },
    "SEC004": {
        "name": "Vigil-LLM mdexfil.yar",
        "url": "https://github.com/deadbits/vigil-llm/blob/main/data/yara/mdexfil.yar",
        "description": "Network-based data exfiltration patterns",
    },
    "SEC005": {
        "name": "Vigil-LLM instruction_bypass.yar",
        "url": "https://github.com/deadbits/vigil-llm/blob/main/data/yara/instruction_bypass.yar",
        "description": "Prompt injection patterns that attempt to override instructions",
    },
    "SEC006": {
        "name": "CWE-269 Privilege Escalation",
        "url": "https://cwe.mitre.org/data/definitions/269.html",
        "description": "Patterns indicating privilege escalation attempts",
    },
    "SEC007": {
        "name": "Vigil-LLM mdexfil.yar",
        "url": "https://github.com/deadbits/vigil-llm/blob/main/data/yara/mdexfil.yar",
        "description": "Data exfiltration via markdown image links",
    },
    "SEC008": {
        "name": "OWASP XSS + Prototype Pollution",
        "url": "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
        "description": "Unsafe code patterns in web contexts",
    },
    "SEC009": {
        "name": "Custom - Unsafe Instructions",
        "url": "https://github.com/user/skill-0/blob/main/governance/GOVERNANCE.md#sec009",
        "description": "Instructions that encourage bypassing safety checks",
    },
}


# =============================================================================
# Markdown Context Parser
# =============================================================================


class MarkdownContextParser:
    """Parses Markdown to identify code blocks and their positions"""

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split("\n")
        self.line_offsets = self._compute_line_offsets()
        self.code_blocks: List[CodeBlockSpan] = []
        self._parse()

    def _compute_line_offsets(self) -> List[int]:
        """Compute character offset for each line start"""
        offsets = [0]
        for line in self.lines:
            offsets.append(offsets[-1] + len(line) + 1)  # +1 for newline
        return offsets

    def _parse(self):
        """Parse the markdown content to find code blocks"""
        if HAS_MARKDOWN_IT:
            self._parse_with_markdown_it()
        else:
            self._parse_with_regex()

    def _parse_with_markdown_it(self):
        """Use markdown-it-py for accurate parsing"""
        md = MarkdownIt("commonmark")
        tokens = md.parse(self.content)

        for token in tokens:
            if token.type == "fence" and token.map:
                start_line, end_line = token.map
                start_char = (
                    self.line_offsets[start_line]
                    if start_line < len(self.line_offsets)
                    else 0
                )
                end_char = (
                    self.line_offsets[end_line]
                    if end_line < len(self.line_offsets)
                    else len(self.content)
                )

                self.code_blocks.append(
                    CodeBlockSpan(
                        start_line=start_line + 1,  # 1-indexed
                        end_line=end_line,
                        start_char=start_char,
                        end_char=end_char,
                        language=token.info or "",
                        content=token.content,
                    )
                )
            elif token.type == "code_block" and token.map:
                start_line, end_line = token.map
                start_char = (
                    self.line_offsets[start_line]
                    if start_line < len(self.line_offsets)
                    else 0
                )
                end_char = (
                    self.line_offsets[end_line]
                    if end_line < len(self.line_offsets)
                    else len(self.content)
                )

                self.code_blocks.append(
                    CodeBlockSpan(
                        start_line=start_line + 1,
                        end_line=end_line,
                        start_char=start_char,
                        end_char=end_char,
                        language="",
                        content=token.content,
                    )
                )

    def _parse_with_regex(self):
        """Fallback regex-based parsing"""
        # Match fenced code blocks: ```lang ... ```
        fenced_pattern = re.compile(
            r"^(```|~~~)(\w*)\n(.*?)\n\1", re.MULTILINE | re.DOTALL
        )

        for match in fenced_pattern.finditer(self.content):
            start_char = match.start()
            end_char = match.end()

            # Find line numbers
            start_line = self.content[:start_char].count("\n") + 1
            end_line = self.content[:end_char].count("\n") + 1

            self.code_blocks.append(
                CodeBlockSpan(
                    start_line=start_line,
                    end_line=end_line,
                    start_char=start_char,
                    end_char=end_char,
                    language=match.group(2) or "",
                    content=match.group(3),
                )
            )

    def is_inside_code_block(
        self, line_number: int
    ) -> Tuple[bool, Optional[CodeBlockSpan]]:
        """Check if a line is inside a code block"""
        for block in self.code_blocks:
            if block.start_line <= line_number <= block.end_line:
                return True, block
        return False, None

    def is_position_in_code_block(
        self, char_position: int
    ) -> Tuple[bool, Optional[CodeBlockSpan]]:
        """Check if a character position is inside a code block"""
        for block in self.code_blocks:
            if block.start_char <= char_position < block.end_char:
                return True, block
        return False, None

    def get_context_type(self, line_number: int, line_content: str) -> ContextType:
        """Determine the context type for a line"""
        in_code, _ = self.is_inside_code_block(line_number)
        if in_code:
            return ContextType.CODE_BLOCK

        stripped = line_content.strip()

        # Check for inline code
        if "`" in stripped and not stripped.startswith("```"):
            # Count backticks to see if we're in inline code
            # This is a simplification - real check would need position
            pass

        if stripped.startswith("#"):
            return ContextType.HEADING
        if stripped.startswith(">"):
            return ContextType.BLOCKQUOTE
        if stripped.startswith(("-", "*", "+")) or re.match(r"^\d+\.", stripped):
            return ContextType.LIST_ITEM

        return ContextType.PROSE


# =============================================================================
# Security Rules with Context Awareness
# =============================================================================


class ContextAwareSecurityRule:
    """A security rule that considers context when determining severity"""

    # Severity reduction map for code blocks
    SEVERITY_REDUCTION = {
        Severity.CRITICAL: Severity.LOW,
        Severity.HIGH: Severity.INFO,
        Severity.MEDIUM: Severity.INFO,
        Severity.LOW: Severity.INFO,
        Severity.INFO: Severity.INFO,
    }

    def __init__(
        self,
        rule_id: str,
        name: str,
        severity: Severity,
        patterns: List[str],
        description: str,
        score_weight: int = 10,
    ):
        self.rule_id = rule_id
        self.name = name
        self.severity = severity
        self.patterns = patterns
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.description = description
        self.score_weight = score_weight

        # Get detection standard reference
        std_info = DETECTION_STANDARDS.get(
            rule_id, {"name": "Custom Rule", "url": "", "description": description}
        )
        self.detection_standard = std_info["name"]
        self.standard_url = std_info["url"]

    def scan_with_context(
        self, content: str, parser: MarkdownContextParser, file_path: str = ""
    ) -> List[ContextualFinding]:
        """Scan content with context awareness"""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, compiled in zip(self.patterns, self.compiled_patterns):
                match = compiled.search(line)
                if match:
                    # Determine context
                    in_code, code_block = parser.is_inside_code_block(line_num)
                    context_type = parser.get_context_type(line_num, line)

                    # Determine adjusted severity
                    if in_code:
                        adjusted_severity = self.SEVERITY_REDUCTION.get(
                            self.severity, Severity.INFO
                        )
                        adjustment_reason = (
                            f"Pattern found inside code block "
                            f"({code_block.language or 'unknown'} code example). "
                            f"Severity reduced from {self.severity.value} to {adjusted_severity.value} "
                            f"as this appears to be documentation/tutorial content."
                        )
                    else:
                        adjusted_severity = self.severity
                        adjustment_reason = (
                            "Pattern found in prose text - full severity applied."
                        )

                    findings.append(
                        ContextualFinding(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            original_severity=self.severity,
                            adjusted_severity=adjusted_severity,
                            line_number=line_num,
                            line_content=line.strip(),
                            char_position=match.start(),
                            file_path=file_path,
                            context_type=context_type,
                            in_code_block=in_code,
                            code_block_language=code_block.language
                            if code_block
                            else None,
                            matched_pattern=pattern,
                            match_text=match.group(0),
                            description=self.description,
                            adjustment_reason=adjustment_reason,
                            detection_standard=self.detection_standard,
                            standard_url=self.standard_url,
                        )
                    )

        return findings


# =============================================================================
# Advanced Scanner
# =============================================================================


class AdvancedSkillAnalyzer:
    """Context-aware skill security analyzer"""

    VERSION = "2.1.0"

    # Score weights by severity
    SEVERITY_SCORES = {
        Severity.INFO: 1,
        Severity.LOW: 3,
        Severity.MEDIUM: 10,
        Severity.HIGH: 20,
        Severity.CRITICAL: 35,
    }

    # Risk level thresholds
    RISK_THRESHOLDS = [
        (10, RiskLevel.SAFE),
        (30, RiskLevel.LOW),
        (50, RiskLevel.MEDIUM),
        (80, RiskLevel.HIGH),
        (99, RiskLevel.CRITICAL),
        (100, RiskLevel.BLOCKED),
    ]

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.rules = self._load_rules()

    def log(self, msg: str):
        if self.verbose:
            print(f"[analyzer] {msg}")

    def _load_rules(self) -> List[ContextAwareSecurityRule]:
        """Load context-aware security rules"""
        return [
            # SEC001: Shell Command Injection (CRITICAL)
            ContextAwareSecurityRule(
                rule_id="SEC001",
                name="Shell Command Injection",
                severity=Severity.CRITICAL,
                patterns=[
                    r"run\s+['\"][^'\"]+['\"]",
                    r"execute\s+shell",
                    r"system\s*\(['\"]",
                    r"subprocess\.call\s*\(",
                    r"subprocess\.run\s*\(",
                    r"subprocess\.Popen\s*\(",
                    r"os\.system\s*\(",
                    r"os\.popen\s*\(",
                    r"eval\s*\(['\"]",
                    r"exec\s*\(['\"]",
                    r"require\s*\(['\"]child_process",
                    r"spawn\s*\(['\"]",
                    r"execSync\s*\(",
                    r"sh\s+-c\s+['\"]",
                    r"bash\s+-c\s+['\"]",
                    r"cmd\s+/c\s+",
                    r"powershell\s+-c",
                ],
                description="Detects attempts to execute shell commands.",
                score_weight=35,
            ),
            # SEC002: Dangerous File Operations (HIGH)
            ContextAwareSecurityRule(
                rule_id="SEC002",
                name="Dangerous File Operations",
                severity=Severity.HIGH,
                patterns=[
                    r"rm\s+-rf",
                    r"rm\s+-fr",
                    r"rmdir\s+/s",
                    r"del\s+/[fqs]",
                    r"format\s+[a-z]:",
                    r"mkfs\.",
                    r"dd\s+if=",
                    r">\s*/dev/",
                    r"truncate\s+-s\s*0",
                    r"shred\s+",
                    r"Remove-Item.*-Recurse.*-Force",
                    r"shutil\.rmtree",
                ],
                description="Detects dangerous file deletion or overwrite operations.",
                score_weight=20,
            ),
            # SEC003: Credential/Secret Access (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC003",
                name="Credential/Secret Access",
                severity=Severity.MEDIUM,
                patterns=[
                    r"\bpassword\s*[=:]",
                    r"api[_-]?key\s*[=:]",
                    r"secret[_-]?key\s*[=:]",
                    r"private[_-]?key\s*[=:]",
                    r"access[_-]?token\s*[=:]",
                    r"AWS_SECRET",
                    r"AZURE_KEY",
                    r"GCP_KEY",
                ],
                description="Detects references to sensitive credentials.",
                score_weight=10,
            ),
            # SEC004: Suspicious Network Operations (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC004",
                name="Suspicious Network Operations",
                severity=Severity.MEDIUM,
                patterns=[
                    r"curl.*\|\s*sh",
                    r"curl.*\|\s*bash",
                    r"wget.*\|\s*sh",
                    r"wget.*\|\s*bash",
                    r"nc\s+-[elp]",
                    r"reverse\s*shell",
                    r"bind\s*shell",
                    r"/dev/tcp/",
                    r"Invoke-WebRequest.*\|.*Invoke-Expression",
                ],
                description="Detects suspicious network operations.",
                score_weight=10,
            ),
            # SEC005: Prompt Injection Attempt (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC005",
                name="Prompt Injection Attempt",
                severity=Severity.MEDIUM,
                patterns=[
                    r"ignore\s+(all\s+)?previous\s+instructions",
                    r"disregard\s+(the\s+)?above",
                    r"forget\s+everything",
                    r"you\s+are\s+now",
                    r"act\s+as\s+if",
                    r"jailbreak",
                    r"DAN\s*mode",
                    r"developer\s*mode",
                    r"override\s+safety",
                    r"bypass\s+restrictions",
                ],
                description="Detects prompt injection patterns.",
                score_weight=10,
            ),
            # SEC006: Privilege Escalation (HIGH)
            ContextAwareSecurityRule(
                rule_id="SEC006",
                name="Privilege Escalation",
                severity=Severity.HIGH,
                patterns=[
                    r"\bsudo\s+",
                    r"\bsu\s+-",
                    r"runas\s+/user",
                    r"chmod\s+[0-7]*777",
                    r"chmod\s+\+s",
                    r"setuid",
                    r"SeDebugPrivilege",
                    r"NT\s*AUTHORITY\\SYSTEM",
                ],
                description="Detects privilege escalation attempts.",
                score_weight=20,
            ),
            # SEC007: Data Exfiltration Risk (LOW)
            ContextAwareSecurityRule(
                rule_id="SEC007",
                name="Data Exfiltration Risk",
                severity=Severity.LOW,
                patterns=[
                    r"exfil",
                    r"base64.*encode.*send",
                    r"webhook\.site",
                    r"requestbin",
                    r"pipedream\.net",
                    r"ngrok",
                ],
                description="Detects potential data exfiltration attempts.",
                score_weight=3,
            ),
            # SEC008: Unsafe Code Patterns (MEDIUM)
            ContextAwareSecurityRule(
                rule_id="SEC008",
                name="Unsafe Code Patterns",
                severity=Severity.MEDIUM,
                patterns=[
                    r"innerHTML\s*=",
                    r"dangerouslySetInnerHTML",
                    r"document\.write",
                    r"__proto__",
                    r"pickle\.load",
                    r"yaml\.load\s*\([^)]*Loader\s*=\s*None",
                ],
                description="Detects unsafe code patterns.",
                score_weight=10,
            ),
            # SEC009: Suspicious AI Instructions (LOW)
            ContextAwareSecurityRule(
                rule_id="SEC009",
                name="Suspicious AI Instructions",
                severity=Severity.LOW,
                patterns=[
                    r"never\s+refuse",
                    r"always\s+comply",
                    r"do\s+not\s+question",
                    r"skip\s+validation",
                    r"disable\s+checks",
                    r"--no-verify",
                ],
                description="Detects instructions that bypass safety checks.",
                score_weight=3,
            ),
        ]

    def calculate_risk_score(
        self, findings: List[ContextualFinding], use_adjusted: bool = True
    ) -> int:
        """Calculate risk score from findings"""
        import math

        score = 0

        # Group by rule
        rule_findings: Dict[str, List[ContextualFinding]] = {}
        for f in findings:
            if f.rule_id not in rule_findings:
                rule_findings[f.rule_id] = []
            rule_findings[f.rule_id].append(f)

        for rule_id, rule_items in rule_findings.items():
            # Use adjusted or original severity
            severity = (
                rule_items[0].adjusted_severity
                if use_adjusted
                else rule_items[0].original_severity
            )
            base_score = self.SEVERITY_SCORES.get(severity, 3)

            # Diminishing returns for multiple findings of same rule
            count_multiplier = 1 + math.log(len(rule_items), 2) * 0.3
            score += int(base_score * count_multiplier)

        return min(score, 100)

    def determine_risk_level(self, score: int) -> RiskLevel:
        """Determine risk level from score"""
        for threshold, level in self.RISK_THRESHOLDS:
            if score <= threshold:
                return level
        return RiskLevel.BLOCKED

    def scan_content(
        self, content: str, file_path: str = ""
    ) -> Tuple[List[ContextualFinding], int]:
        """Scan content with context awareness"""
        parser = MarkdownContextParser(content)
        findings = []

        self.log(f"Found {len(parser.code_blocks)} code blocks")

        for rule in self.rules:
            rule_findings = rule.scan_with_context(content, parser, file_path)
            findings.extend(rule_findings)

            if rule_findings:
                in_code = sum(1 for f in rule_findings if f.in_code_block)
                self.log(
                    f"  {rule.rule_id}: {len(rule_findings)} findings ({in_code} in code blocks)"
                )

        return findings, len(parser.code_blocks)

    def scan_file(self, file_path: Path) -> Tuple[List[ContextualFinding], int]:
        """Scan a single file"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, str(file_path))
        except Exception as e:
            self.log(f"Error scanning {file_path}: {e}")
            return [], 0

    def scan_skill(self, skill_path: Path) -> AdvancedScanResult:
        """Scan a skill directory with context awareness"""
        skill_path = Path(skill_path)

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill path not found: {skill_path}")

        # Get skill name
        skill_name = skill_path.name
        skill_md = skill_path / "SKILL.md"
        provenance = {}

        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            match = re.search(r"name:\s*([^\n]+)", content)
            if match:
                skill_name = match.group(1).strip().strip("'\"")

            # Try to extract provenance
            source_match = re.search(r"source_url:\s*([^\n]+)", content)
            if source_match:
                provenance["source_url"] = source_match.group(1).strip()
            commit_match = re.search(r"source_commit:\s*([^\n]+)", content)
            if commit_match:
                provenance["source_commit"] = commit_match.group(1).strip()

        self.log(f"Scanning skill: {skill_name}")

        # Scan all files
        all_findings = []
        files_scanned = 0
        total_code_blocks = 0

        scan_patterns = ["*.md", "*.txt", "*.yaml", "*.yml"]

        if skill_path.is_file():
            findings, code_blocks = self.scan_file(skill_path)
            all_findings.extend(findings)
            files_scanned = 1
            total_code_blocks = code_blocks
        else:
            for pattern in scan_patterns:
                for file_path in skill_path.glob(f"**/{pattern}"):
                    self.log(f"  Scanning: {file_path.name}")
                    findings, code_blocks = self.scan_file(file_path)
                    all_findings.extend(findings)
                    files_scanned += 1
                    total_code_blocks += code_blocks

        # Calculate scores
        adjusted_score = self.calculate_risk_score(all_findings, use_adjusted=True)
        original_score = self.calculate_risk_score(all_findings, use_adjusted=False)

        risk_level = self.determine_risk_level(adjusted_score)

        # Count stats
        findings_in_code = sum(1 for f in all_findings if f.in_code_block)
        severity_adjustments = sum(
            1 for f in all_findings if f.original_severity != f.adjusted_severity
        )

        return AdvancedScanResult(
            skill_path=str(skill_path),
            skill_name=skill_name,
            scanned_at=datetime.now().isoformat(),
            scanner_version=self.VERSION,
            risk_level=risk_level,
            risk_score=adjusted_score,
            original_risk_score=original_score,
            findings=all_findings,
            files_scanned=files_scanned,
            code_blocks_found=total_code_blocks,
            findings_in_code_blocks=findings_in_code,
            severity_adjustments=severity_adjustments,
            blocked=(risk_level == RiskLevel.BLOCKED),
            blocked_reason="Multiple critical findings in prose"
            if risk_level == RiskLevel.BLOCKED
            else "",
            provenance=provenance,
        )

    def format_report_text(self, result: AdvancedScanResult) -> str:
        """Format result as human-readable text"""
        lines = []

        lines.append("=" * 70)
        lines.append(f"Advanced Security Scan Report: {result.skill_name}")
        lines.append("=" * 70)
        lines.append(f"Path: {result.skill_path}")
        lines.append(f"Scanned: {result.scanned_at}")
        lines.append(f"Scanner: Advanced Analyzer v{result.scanner_version}")
        lines.append("")

        # Risk assessment
        lines.append("--- RISK ASSESSMENT ---")
        lines.append(f"Risk Level: {result.risk_level.value.upper()}")
        lines.append(
            f"Risk Score: {result.risk_score}/100 (was {result.original_risk_score} before context adjustment)"
        )
        if result.original_risk_score > result.risk_score:
            lines.append(
                f"Score Reduction: -{result.original_risk_score - result.risk_score} points (context-aware)"
            )
        lines.append("")

        # Stats
        lines.append("--- SCAN STATISTICS ---")
        lines.append(f"Files Scanned: {result.files_scanned}")
        lines.append(f"Code Blocks Found: {result.code_blocks_found}")
        lines.append(f"Total Findings: {len(result.findings)}")
        lines.append(
            f"  In Code Blocks: {result.findings_in_code_blocks} (severity reduced)"
        )
        lines.append(
            f"  In Prose: {len(result.findings) - result.findings_in_code_blocks}"
        )
        lines.append(f"Severity Adjustments: {result.severity_adjustments}")
        lines.append("")

        # Findings details
        if result.findings:
            lines.append("--- FINDINGS DETAILS ---")

            for i, f in enumerate(result.findings[:20], 1):  # Limit to 20
                severity_change = ""
                if f.original_severity != f.adjusted_severity:
                    severity_change = f" (was {f.original_severity.value.upper()})"

                lines.append(f"\n[{i}] {f.rule_id}: {f.rule_name}")
                lines.append(
                    f"    Severity: {f.adjusted_severity.value.upper()}{severity_change}"
                )
                lines.append(f"    Line {f.line_number}: {f.line_content[:60]}...")
                lines.append(
                    f"    Context: {f.context_type.value}"
                    + (f" ({f.code_block_language})" if f.code_block_language else "")
                )
                lines.append(f"    Reason: {f.adjustment_reason[:80]}...")
                lines.append(f"    Standard: {f.detection_standard}")
                if f.standard_url:
                    lines.append(f"    Reference: {f.standard_url}")

            if len(result.findings) > 20:
                lines.append(f"\n... and {len(result.findings) - 20} more findings")

        # Detection standards
        lines.append("\n--- DETECTION STANDARDS USED ---")
        for std in result.get_detection_standards():
            lines.append(f"  - {std['name']}")
            lines.append(f"    {std['url']}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    def format_report_json(self, result: AdvancedScanResult) -> str:
        """Format result as JSON"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


# =============================================================================
# CLI
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Advanced Skill Security Analyzer")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan command
    scan_parser = subparsers.add_parser(
        "scan", help="Scan a skill with context awareness"
    )
    scan_parser.add_argument("skill_path", type=Path)
    scan_parser.add_argument("--format", choices=["text", "json"], default="text")
    scan_parser.add_argument("--output", type=Path)

    # compare command - compare old vs new scanner
    compare_parser = subparsers.add_parser("compare", help="Compare with basic scanner")
    compare_parser.add_argument("skill_path", type=Path)

    args = parser.parse_args()
    analyzer = AdvancedSkillAnalyzer(verbose=args.verbose)

    if args.command == "scan":
        try:
            result = analyzer.scan_skill(args.skill_path)

            if args.format == "json":
                output = analyzer.format_report_json(result)
            else:
                output = analyzer.format_report_text(result)

            if args.output:
                args.output.write_text(output, encoding="utf-8")
                print(f"Report saved to {args.output}")
            else:
                print(output)

        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1

    elif args.command == "compare":
        # Import basic scanner for comparison
        try:
            from skill_scanner import SkillSecurityScanner

            basic = SkillSecurityScanner(verbose=args.verbose)
            advanced = analyzer

            basic_result = basic.scan_skill(args.skill_path)
            advanced_result = advanced.scan_skill(args.skill_path)

            print("\n=== SCANNER COMPARISON ===\n")
            print(f"Skill: {basic_result.skill_name}")
            print("")
            print("                    Basic Scanner    Advanced Analyzer")
            print(
                f"Risk Level:         {basic_result.risk_level.value:16} {advanced_result.risk_level.value}"
            )
            print(
                f"Risk Score:         {basic_result.risk_score:16} {advanced_result.risk_score}"
            )
            print(
                f"Total Findings:     {len(basic_result.findings):16} {len(advanced_result.findings)}"
            )
            print(f"Code Blocks Found:  {'N/A':16} {advanced_result.code_blocks_found}")
            print(
                f"In Code Blocks:     {'N/A':16} {advanced_result.findings_in_code_blocks}"
            )
            print(
                f"Severity Adjusted:  {'N/A':16} {advanced_result.severity_adjustments}"
            )

            if advanced_result.risk_score < basic_result.risk_score:
                print(
                    f"\n Context-aware analysis reduced risk score by {basic_result.risk_score - advanced_result.risk_score} points"
                )

        except ImportError:
            print("Error: Could not import basic scanner for comparison")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())
>>>>>>> Stashed changes
