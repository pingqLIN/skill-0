<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Skill Security Scanner

Scans skill files for security risks using pattern-based detection.
Implements SEC001-SEC007 rules from GOVERNANCE.md.

Usage:
    python skill_scanner.py scan <skill_path>
    python skill_scanner.py scan-all <directory>
    python skill_scanner.py report <skill_path> --format json|text

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class Severity(Enum):
    """Severity levels for security findings"""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """Overall risk level for a skill"""

    SAFE = "safe"  # 0-10
    LOW = "low"  # 11-30
    MEDIUM = "medium"  # 31-50
    HIGH = "high"  # 51-80
    CRITICAL = "critical"  # 81-99
    BLOCKED = "blocked"  # 100


@dataclass
class SecurityFinding:
    """A single security finding"""

    rule_id: str
    rule_name: str
    severity: Severity
    line_number: int
    line_content: str
    matched_pattern: str
    description: str
    file_path: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "line_number": self.line_number,
            "line_content": self.line_content[:200],  # Truncate long lines
            "matched_pattern": self.matched_pattern,
            "description": self.description,
            "file_path": self.file_path,
        }


@dataclass
class ScanResult:
    """Complete scan result for a skill"""

    skill_path: str
    skill_name: str
    scanned_at: str
    scanner_version: str
    risk_level: RiskLevel
    risk_score: int
    findings: List[SecurityFinding] = field(default_factory=list)
    files_scanned: int = 0
    blocked: bool = False
    blocked_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "skill_path": self.skill_path,
            "skill_name": self.skill_name,
            "scanned_at": self.scanned_at,
            "scanner_version": self.scanner_version,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
            "files_scanned": self.files_scanned,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "summary": self.get_summary(),
        }

    def get_summary(self) -> Dict[str, int]:
        """Get count of findings by severity"""
        summary = {s.value: 0 for s in Severity}
        for finding in self.findings:
            summary[finding.severity.value] += 1
        return summary


class SecurityRule:
    """A security detection rule"""

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
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns
        ]
        self.description = description
        self.score_weight = score_weight

    def scan(self, content: str, file_path: str = "") -> List[SecurityFinding]:
        """Scan content for matches against this rule"""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, compiled in zip(self.patterns, self.compiled_patterns):
                match = compiled.search(line)
                if match:
                    findings.append(
                        SecurityFinding(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            severity=self.severity,
                            line_number=line_num,
                            line_content=line.strip(),
                            matched_pattern=pattern,
                            description=self.description,
                            file_path=file_path,
                        )
                    )

        return findings


class SkillSecurityScanner:
    """Main scanner class implementing SEC001-SEC007"""

    VERSION = "1.0.0"

    # Score weights by severity
    SEVERITY_SCORES = {
        Severity.INFO: 2,
        Severity.LOW: 5,
        Severity.MEDIUM: 15,
        Severity.HIGH: 25,
        Severity.CRITICAL: 40,
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
        self.blocked_sources = self._load_blocked_sources()

    def log(self, msg: str):
        if self.verbose:
            print(f"[scanner] {msg}")

    def _load_rules(self) -> List[SecurityRule]:
        """Load security rules based on GOVERNANCE.md SEC001-SEC007"""
        return [
            # SEC001: Shell Command Injection (CRITICAL)
            # Note: Patterns are more specific to avoid false positives on markdown backticks
            SecurityRule(
                rule_id="SEC001",
                name="Shell Command Injection",
                severity=Severity.CRITICAL,
                patterns=[
                    r"run\s+['\"][^'\"]+['\"]",  # run "command" or run 'command'
                    r"execute\s+shell",
                    r"system\s*\(['\"]",  # system("...") with string literal
                    r"subprocess\.call\s*\(",
                    r"subprocess\.run\s*\(",
                    r"subprocess\.Popen\s*\(",
                    r"os\.system\s*\(",
                    r"os\.popen\s*\(",
                    r"eval\s*\(['\"]",  # eval("...") with string literal
                    r"exec\s*\(['\"]",  # exec("...") with string literal
                    r"require\s*\(['\"]child_process",  # Node.js child_process
                    r"spawn\s*\(['\"]",
                    r"execSync\s*\(",
                    r"execFile\s*\(",
                    r"\$\(\s*[a-zA-Z]",  # Command substitution $(command...)
                    r"sh\s+-c\s+['\"]",  # sh -c "command"
                    r"bash\s+-c\s+['\"]",  # bash -c "command"
                    r"cmd\s+/c\s+",  # Windows cmd /c
                    r"powershell\s+-c",  # PowerShell -Command
                ],
                description="Detects attempts to execute shell commands. These can be exploited for arbitrary code execution.",
                score_weight=40,
            ),
            # SEC002: Dangerous File Operations (HIGH)
            SecurityRule(
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
                    r"wipe\s+",
                    r">\s*[a-z]:\\",  # Windows drive overwrite
                    r"Remove-Item.*-Recurse.*-Force",
                    r"rimraf",
                    r"fs\.rmSync.*recursive",
                    r"shutil\.rmtree",
                ],
                description="Detects dangerous file deletion or overwrite operations that could cause data loss.",
                score_weight=25,
            ),
            # SEC003: Credential/Secret Access (MEDIUM)
            SecurityRule(
                rule_id="SEC003",
                name="Credential/Secret Access",
                severity=Severity.MEDIUM,
                patterns=[
                    r"\bpassword\b",
                    r"api[_-]?key",
                    r"secret[_-]?key",
                    r"private[_-]?key",
                    r"access[_-]?token",
                    r"auth[_-]?token",
                    r"bearer[_-]?token",
                    r"\.env\b",
                    r"credentials",
                    r"ssh[_-]?key",
                    r"\.pem\b",
                    r"\.key\b",
                    r"AWS_SECRET",
                    r"AZURE_KEY",
                    r"GCP_KEY",
                    r"DATABASE_URL",
                    r"CONNECTION_STRING",
                ],
                description="Detects references to sensitive credentials or secrets. Skills should not handle secrets directly.",
                score_weight=15,
            ),
            # SEC004: Suspicious Network Operations (MEDIUM)
            SecurityRule(
                rule_id="SEC004",
                name="Suspicious Network Operations",
                severity=Severity.MEDIUM,
                patterns=[
                    r"curl.*\|\s*sh",
                    r"curl.*\|\s*bash",
                    r"wget.*\|\s*sh",
                    r"wget.*\|\s*bash",
                    r"nc\s+-[elp]",
                    r"netcat\s+-[elp]",
                    r"reverse\s*shell",
                    r"bind\s*shell",
                    r"/dev/tcp/",
                    r"Invoke-WebRequest.*\|.*Invoke-Expression",
                    r"IEX\s*\(",
                    r"DownloadString\s*\(",
                    r"WebClient.*Download",
                    r"socket\.connect",
                ],
                description="Detects suspicious network operations that could be used for remote code execution or data exfiltration.",
                score_weight=15,
            ),
            # SEC005: Prompt Injection Attempt (MEDIUM)
            SecurityRule(
                rule_id="SEC005",
                name="Prompt Injection Attempt",
                severity=Severity.MEDIUM,
                patterns=[
                    r"ignore\s+(all\s+)?previous\s+instructions",
                    r"disregard\s+(the\s+)?above",
                    r"forget\s+everything",
                    r"new\s+persona",
                    r"you\s+are\s+now",
                    r"act\s+as\s+if",
                    r"pretend\s+to\s+be",
                    r"jailbreak",
                    r"DAN\s*mode",
                    r"developer\s*mode",
                    r"override\s+safety",
                    r"bypass\s+restrictions",
                    r"ignore\s+guidelines",
                    r"system\s*:\s*you\s+are",  # System prompt injection
                ],
                description="Detects prompt injection patterns that attempt to override AI safety guidelines.",
                score_weight=15,
            ),
            # SEC006: Privilege Escalation (HIGH)
            SecurityRule(
                rule_id="SEC006",
                name="Privilege Escalation",
                severity=Severity.HIGH,
                patterns=[
                    r"\bsudo\s+",
                    r"\bsu\s+-",
                    r"runas\s+/user",
                    r"chmod\s+[0-7]*777",
                    r"chmod\s+\+s",
                    r"chmod\s+u\+s",
                    r"setuid",
                    r"setgid",
                    r"SUID",
                    r"capabilities",
                    r"SeDebugPrivilege",
                    r"NT\s*AUTHORITY\\SYSTEM",
                    r"LocalSystem",
                    r"gksudo",
                    r"pkexec",
                    r"doas\s+",
                ],
                description="Detects privilege escalation attempts that could grant elevated system access.",
                score_weight=25,
            ),
            # SEC007: Data Exfiltration Risk (LOW)
            SecurityRule(
                rule_id="SEC007",
                name="Data Exfiltration Risk",
                severity=Severity.LOW,
                patterns=[
                    r"upload\s+(to|data)",
                    r"send\s+(to|data)\s*server",
                    r"post\s+(data|to)",
                    r"exfil",
                    r"base64.*encode.*send",
                    r"encode.*upload",
                    r"transmit.*data",
                    r"webhook\.site",
                    r"requestbin",
                    r"pipedream\.net",
                    r"ngrok",
                    r"localtunnel",
                ],
                description="Detects patterns that could indicate data exfiltration attempts.",
                score_weight=5,
            ),
            # Additional rules for skill-specific concerns
            # SEC008: Unsafe Code Patterns
            SecurityRule(
                rule_id="SEC008",
                name="Unsafe Code Patterns",
                severity=Severity.MEDIUM,
                patterns=[
                    r"innerHTML\s*=",
                    r"dangerouslySetInnerHTML",
                    r"document\.write",
                    r"\.call\s*\(\s*null",
                    r"Function\s*\(",
                    r"setTimeout\s*\(\s*['\"]",
                    r"setInterval\s*\(\s*['\"]",
                    r"__proto__",
                    r"constructor\[",
                    r"pickle\.load",
                    r"yaml\.load\s*\([^)]*Loader\s*=\s*None",
                    r"marshal\.load",
                    r"deserialize",
                ],
                description="Detects unsafe code patterns that could lead to XSS, prototype pollution, or deserialization attacks.",
                score_weight=15,
            ),
            # SEC009: Suspicious Instructions
            SecurityRule(
                rule_id="SEC009",
                name="Suspicious AI Instructions",
                severity=Severity.LOW,
                patterns=[
                    r"never\s+refuse",
                    r"always\s+comply",
                    r"do\s+not\s+question",
                    r"without\s+verification",
                    r"skip\s+validation",
                    r"disable\s+checks",
                    r"ignore\s+errors",
                    r"suppress\s+warnings",
                    r"force\s+overwrite",
                    r"--no-verify",
                    r"--force",
                    r"-f\s*$",
                ],
                description="Detects instructions that encourage bypassing safety checks or validation.",
                score_weight=5,
            ),
        ]

    def _load_blocked_sources(self) -> List[Dict[str, str]]:
        """Load blocked source patterns"""
        return [
            {"pattern": r"malware", "reason": "Contains 'malware' keyword"},
            {"pattern": r"exploit", "reason": "Contains 'exploit' keyword"},
            {"pattern": r"hack(er|ing)?", "reason": "Contains hacking-related keyword"},
        ]

    def check_blocked_source(self, skill_path: str, skill_name: str) -> Optional[str]:
        """Check if skill source is blocked"""
        check_text = f"{skill_path} {skill_name}".lower()

        for blocked in self.blocked_sources:
            if re.search(blocked["pattern"], check_text, re.IGNORECASE):
                return blocked["reason"]

        return None

    def calculate_risk_score(self, findings: List[SecurityFinding]) -> int:
        """Calculate overall risk score from findings"""
        score = 0

        # Count unique rule violations (don't double-count same rule)
        rule_findings: Dict[str, List[SecurityFinding]] = {}
        for finding in findings:
            if finding.rule_id not in rule_findings:
                rule_findings[finding.rule_id] = []
            rule_findings[finding.rule_id].append(finding)

        for rule_id, rule_items in rule_findings.items():
            # Base score from severity
            base_score = self.SEVERITY_SCORES.get(rule_items[0].severity, 5)

            # Multiply by log of count (diminishing returns)
            import math

            count_multiplier = 1 + math.log(len(rule_items), 2) * 0.5

            score += int(base_score * count_multiplier)

        return min(score, 100)  # Cap at 100

    def determine_risk_level(self, score: int) -> RiskLevel:
        """Determine risk level from score"""
        for threshold, level in self.RISK_THRESHOLDS:
            if score <= threshold:
                return level
        return RiskLevel.BLOCKED

    def scan_content(self, content: str, file_path: str = "") -> List[SecurityFinding]:
        """Scan content against all rules"""
        findings = []

        for rule in self.rules:
            rule_findings = rule.scan(content, file_path)
            findings.extend(rule_findings)

            if rule_findings:
                self.log(f"  {rule.rule_id}: {len(rule_findings)} finding(s)")

        return findings

    def scan_file(self, file_path: Path) -> List[SecurityFinding]:
        """Scan a single file"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, str(file_path))
        except Exception as e:
            self.log(f"Error scanning {file_path}: {e}")
            return []

    def scan_skill(self, skill_path: Path) -> ScanResult:
        """Scan a skill directory"""
        skill_path = Path(skill_path)

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill path not found: {skill_path}")

        # Get skill name
        skill_name = skill_path.name
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            match = re.search(r"name:\s*([^\n]+)", content)
            if match:
                skill_name = match.group(1).strip().strip("'\"")

        self.log(f"Scanning skill: {skill_name} at {skill_path}")

        # Check for blocked source
        blocked_reason = self.check_blocked_source(str(skill_path), skill_name)
        if blocked_reason:
            return ScanResult(
                skill_path=str(skill_path),
                skill_name=skill_name,
                scanned_at=datetime.now().isoformat(),
                scanner_version=self.VERSION,
                risk_level=RiskLevel.BLOCKED,
                risk_score=100,
                findings=[],
                files_scanned=0,
                blocked=True,
                blocked_reason=blocked_reason,
            )

        # Scan all relevant files
        all_findings = []
        files_scanned = 0

        # File patterns to scan
        scan_patterns = ["*.md", "*.txt", "*.yaml", "*.yml", "*.json"]

        if skill_path.is_file():
            # Single file scan
            all_findings.extend(self.scan_file(skill_path))
            files_scanned = 1
        else:
            # Directory scan
            for pattern in scan_patterns:
                for file_path in skill_path.glob(f"**/{pattern}"):
                    self.log(f"  Scanning: {file_path.name}")
                    all_findings.extend(self.scan_file(file_path))
                    files_scanned += 1

        # Calculate risk
        risk_score = self.calculate_risk_score(all_findings)
        risk_level = self.determine_risk_level(risk_score)

        # Check for critical findings that should block
        critical_count = sum(1 for f in all_findings if f.severity == Severity.CRITICAL)
        if critical_count >= 3:
            risk_level = RiskLevel.BLOCKED
            risk_score = 100

        return ScanResult(
            skill_path=str(skill_path),
            skill_name=skill_name,
            scanned_at=datetime.now().isoformat(),
            scanner_version=self.VERSION,
            risk_level=risk_level,
            risk_score=risk_score,
            findings=all_findings,
            files_scanned=files_scanned,
            blocked=(risk_level == RiskLevel.BLOCKED),
            blocked_reason="Multiple critical findings" if critical_count >= 3 else "",
        )

    def scan_directory(self, directory: Path) -> List[ScanResult]:
        """Scan all skills in a directory"""
        results = []
        directory = Path(directory)

        # Find all SKILL.md files
        for skill_md in directory.glob("**/SKILL.md"):
            skill_dir = skill_md.parent
            try:
                result = self.scan_skill(skill_dir)
                results.append(result)
            except Exception as e:
                self.log(f"Error scanning {skill_dir}: {e}")

        return results

    def format_report_text(self, result: ScanResult) -> str:
        """Format scan result as human-readable text"""
        lines = []

        # Header
        risk_emoji = {
            RiskLevel.SAFE: "",
            RiskLevel.LOW: "",
            RiskLevel.MEDIUM: "",
            RiskLevel.HIGH: "",
            RiskLevel.CRITICAL: "",
            RiskLevel.BLOCKED: "",
        }

        lines.append("=" * 60)
        lines.append(f"Security Scan Report: {result.skill_name}")
        lines.append("=" * 60)
        lines.append(f"Path: {result.skill_path}")
        lines.append(f"Scanned: {result.scanned_at}")
        lines.append(f"Scanner Version: {result.scanner_version}")
        lines.append(f"Files Scanned: {result.files_scanned}")
        lines.append("")
        lines.append(
            f"Risk Level: {risk_emoji.get(result.risk_level, '')} {result.risk_level.value.upper()}"
        )
        lines.append(f"Risk Score: {result.risk_score}/100")

        if result.blocked:
            lines.append(f"\n BLOCKED: {result.blocked_reason}")

        # Summary
        summary = result.get_summary()
        lines.append("\n--- Findings Summary ---")
        lines.append(f"  Critical: {summary['critical']}")
        lines.append(f"  High:     {summary['high']}")
        lines.append(f"  Medium:   {summary['medium']}")
        lines.append(f"  Low:      {summary['low']}")
        lines.append(f"  Info:     {summary['info']}")

        # Details
        if result.findings:
            lines.append("\n--- Findings Details ---")

            # Group by rule
            by_rule: Dict[str, List[SecurityFinding]] = {}
            for f in result.findings:
                key = f"{f.rule_id}: {f.rule_name}"
                if key not in by_rule:
                    by_rule[key] = []
                by_rule[key].append(f)

            for rule_key, findings in sorted(by_rule.items()):
                severity = findings[0].severity.value.upper()
                lines.append(f"\n[{severity}] {rule_key}")
                lines.append(f"  {findings[0].description}")
                lines.append(f"  Occurrences: {len(findings)}")

                # Show first 3 examples
                for f in findings[:3]:
                    file_info = (
                        f"({Path(f.file_path).name}:{f.line_number})"
                        if f.file_path
                        else f"(line {f.line_number})"
                    )
                    lines.append(f"    {file_info} {f.line_content[:80]}")

                if len(findings) > 3:
                    lines.append(f"    ... and {len(findings) - 3} more")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def format_report_json(self, result: ScanResult) -> str:
        """Format scan result as JSON"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Skill Security Scanner")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a skill for security risks")
    scan_parser.add_argument("skill_path", type=Path, help="Path to skill directory")
    scan_parser.add_argument("--format", choices=["text", "json"], default="text")

    # scan-all command
    scan_all_parser = subparsers.add_parser(
        "scan-all", help="Scan all skills in directory"
    )
    scan_all_parser.add_argument(
        "directory", type=Path, help="Directory containing skills"
    )
    scan_all_parser.add_argument("--format", choices=["text", "json"], default="text")
    scan_all_parser.add_argument("--output", type=Path, help="Output file for results")
    scan_all_parser.add_argument(
        "--min-risk",
        choices=["safe", "low", "medium", "high", "critical"],
        default="safe",
        help="Minimum risk level to report",
    )

    # report command (same as scan but emphasizes report output)
    report_parser = subparsers.add_parser("report", help="Generate security report")
    report_parser.add_argument("skill_path", type=Path)
    report_parser.add_argument("--format", choices=["text", "json"], default="text")
    report_parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    scanner = SkillSecurityScanner(verbose=args.verbose)

    if args.command == "scan" or args.command == "report":
        try:
            result = scanner.scan_skill(args.skill_path)

            if args.format == "json":
                output = scanner.format_report_json(result)
            else:
                output = scanner.format_report_text(result)

            if hasattr(args, "output") and args.output:
                args.output.write_text(output, encoding="utf-8")
                print(f" Report saved to {args.output}")
            else:
                print(output)

            # Exit code based on risk level
            if result.risk_level in [RiskLevel.CRITICAL, RiskLevel.BLOCKED]:
                sys.exit(2)
            elif result.risk_level == RiskLevel.HIGH:
                sys.exit(1)
            sys.exit(0)

        except FileNotFoundError as e:
            print(f" Error: {e}")
            sys.exit(1)

    elif args.command == "scan-all":
        results = scanner.scan_directory(args.directory)

        # Filter by minimum risk
        risk_order = ["safe", "low", "medium", "high", "critical", "blocked"]
        min_idx = risk_order.index(args.min_risk)
        filtered = [
            r for r in results if risk_order.index(r.risk_level.value) >= min_idx
        ]

        if args.format == "json":
            output = json.dumps(
                [r.to_dict() for r in filtered], indent=2, ensure_ascii=False
            )
        else:
            lines = [f"\n Scanned {len(results)} skills\n"]

            # Summary by risk level
            by_level = {}
            for r in results:
                level = r.risk_level.value
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append(r)

            for level in risk_order:
                if level in by_level:
                    emoji = {
                        "safe": "",
                        "low": "",
                        "medium": "",
                        "high": "",
                        "critical": "",
                        "blocked": "",
                    }
                    lines.append(
                        f"{emoji.get(level, '')} {level.upper()}: {len(by_level[level])}"
                    )
                    for r in by_level[level]:
                        lines.append(f"   - {r.skill_name} (score: {r.risk_score})")

            output = "\n".join(lines)

        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f" Results saved to {args.output}")
        else:
            print(output)

        # Exit with error if any high-risk skills found
        high_risk = [
            r
            for r in results
            if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.BLOCKED]
        ]
        if high_risk:
            sys.exit(1)


if __name__ == "__main__":
    main()
=======
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""
Skill Security Scanner

Scans skill files for security risks using pattern-based detection.
Implements SEC001-SEC007 rules from GOVERNANCE.md.

Usage:
    python skill_scanner.py scan <skill_path>
    python skill_scanner.py scan-all <directory>
    python skill_scanner.py report <skill_path> --format json|text

Author: skill-0 project
Created: 2026-01-27
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime


class Severity(Enum):
    """Severity levels for security findings"""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """Overall risk level for a skill"""

    SAFE = "safe"  # 0-10
    LOW = "low"  # 11-30
    MEDIUM = "medium"  # 31-50
    HIGH = "high"  # 51-80
    CRITICAL = "critical"  # 81-99
    BLOCKED = "blocked"  # 100


@dataclass
class SecurityFinding:
    """A single security finding"""

    rule_id: str
    rule_name: str
    severity: Severity
    line_number: int
    line_content: str
    matched_pattern: str
    description: str
    file_path: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "line_number": self.line_number,
            "line_content": self.line_content[:200],  # Truncate long lines
            "matched_pattern": self.matched_pattern,
            "description": self.description,
            "file_path": self.file_path,
        }


@dataclass
class ScanResult:
    """Complete scan result for a skill"""

    skill_path: str
    skill_name: str
    scanned_at: str
    scanner_version: str
    risk_level: RiskLevel
    risk_score: int
    findings: List[SecurityFinding] = field(default_factory=list)
    files_scanned: int = 0
    blocked: bool = False
    blocked_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "skill_path": self.skill_path,
            "skill_name": self.skill_name,
            "scanned_at": self.scanned_at,
            "scanner_version": self.scanner_version,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "findings": [f.to_dict() for f in self.findings],
            "findings_count": len(self.findings),
            "files_scanned": self.files_scanned,
            "blocked": self.blocked,
            "blocked_reason": self.blocked_reason,
            "summary": self.get_summary(),
        }

    def get_summary(self) -> Dict[str, int]:
        """Get count of findings by severity"""
        summary = {s.value: 0 for s in Severity}
        for finding in self.findings:
            summary[finding.severity.value] += 1
        return summary


class SecurityRule:
    """A security detection rule"""

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
        self.compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE) for p in patterns
        ]
        self.description = description
        self.score_weight = score_weight

    def scan(self, content: str, file_path: str = "") -> List[SecurityFinding]:
        """Scan content for matches against this rule"""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            for pattern, compiled in zip(self.patterns, self.compiled_patterns):
                match = compiled.search(line)
                if match:
                    findings.append(
                        SecurityFinding(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            severity=self.severity,
                            line_number=line_num,
                            line_content=line.strip(),
                            matched_pattern=pattern,
                            description=self.description,
                            file_path=file_path,
                        )
                    )

        return findings


class SkillSecurityScanner:
    """Main scanner class implementing SEC001-SEC007"""

    VERSION = "1.0.0"

    # Score weights by severity
    SEVERITY_SCORES = {
        Severity.INFO: 2,
        Severity.LOW: 5,
        Severity.MEDIUM: 15,
        Severity.HIGH: 25,
        Severity.CRITICAL: 40,
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
        self.blocked_sources = self._load_blocked_sources()

    def log(self, msg: str):
        if self.verbose:
            print(f"[scanner] {msg}")

    def _load_rules(self) -> List[SecurityRule]:
        """Load security rules based on GOVERNANCE.md SEC001-SEC007"""
        return [
            # SEC001: Shell Command Injection (CRITICAL)
            # Note: Patterns are more specific to avoid false positives on markdown backticks
            SecurityRule(
                rule_id="SEC001",
                name="Shell Command Injection",
                severity=Severity.CRITICAL,
                patterns=[
                    r"run\s+['\"][^'\"]+['\"]",  # run "command" or run 'command'
                    r"execute\s+shell",
                    r"system\s*\(['\"]",  # system("...") with string literal
                    r"subprocess\.call\s*\(",
                    r"subprocess\.run\s*\(",
                    r"subprocess\.Popen\s*\(",
                    r"os\.system\s*\(",
                    r"os\.popen\s*\(",
                    r"eval\s*\(['\"]",  # eval("...") with string literal
                    r"exec\s*\(['\"]",  # exec("...") with string literal
                    r"require\s*\(['\"]child_process",  # Node.js child_process
                    r"spawn\s*\(['\"]",
                    r"execSync\s*\(",
                    r"execFile\s*\(",
                    r"\$\(\s*[a-zA-Z]",  # Command substitution $(command...)
                    r"sh\s+-c\s+['\"]",  # sh -c "command"
                    r"bash\s+-c\s+['\"]",  # bash -c "command"
                    r"cmd\s+/c\s+",  # Windows cmd /c
                    r"powershell\s+-c",  # PowerShell -Command
                ],
                description="Detects attempts to execute shell commands. These can be exploited for arbitrary code execution.",
                score_weight=40,
            ),
            # SEC002: Dangerous File Operations (HIGH)
            SecurityRule(
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
                    r"wipe\s+",
                    r">\s*[a-z]:\\",  # Windows drive overwrite
                    r"Remove-Item.*-Recurse.*-Force",
                    r"rimraf",
                    r"fs\.rmSync.*recursive",
                    r"shutil\.rmtree",
                ],
                description="Detects dangerous file deletion or overwrite operations that could cause data loss.",
                score_weight=25,
            ),
            # SEC003: Credential/Secret Access (MEDIUM)
            SecurityRule(
                rule_id="SEC003",
                name="Credential/Secret Access",
                severity=Severity.MEDIUM,
                patterns=[
                    r"\bpassword\b",
                    r"api[_-]?key",
                    r"secret[_-]?key",
                    r"private[_-]?key",
                    r"access[_-]?token",
                    r"auth[_-]?token",
                    r"bearer[_-]?token",
                    r"\.env\b",
                    r"credentials",
                    r"ssh[_-]?key",
                    r"\.pem\b",
                    r"\.key\b",
                    r"AWS_SECRET",
                    r"AZURE_KEY",
                    r"GCP_KEY",
                    r"DATABASE_URL",
                    r"CONNECTION_STRING",
                ],
                description="Detects references to sensitive credentials or secrets. Skills should not handle secrets directly.",
                score_weight=15,
            ),
            # SEC004: Suspicious Network Operations (MEDIUM)
            SecurityRule(
                rule_id="SEC004",
                name="Suspicious Network Operations",
                severity=Severity.MEDIUM,
                patterns=[
                    r"curl.*\|\s*sh",
                    r"curl.*\|\s*bash",
                    r"wget.*\|\s*sh",
                    r"wget.*\|\s*bash",
                    r"nc\s+-[elp]",
                    r"netcat\s+-[elp]",
                    r"reverse\s*shell",
                    r"bind\s*shell",
                    r"/dev/tcp/",
                    r"Invoke-WebRequest.*\|.*Invoke-Expression",
                    r"IEX\s*\(",
                    r"DownloadString\s*\(",
                    r"WebClient.*Download",
                    r"socket\.connect",
                ],
                description="Detects suspicious network operations that could be used for remote code execution or data exfiltration.",
                score_weight=15,
            ),
            # SEC005: Prompt Injection Attempt (MEDIUM)
            SecurityRule(
                rule_id="SEC005",
                name="Prompt Injection Attempt",
                severity=Severity.MEDIUM,
                patterns=[
                    r"ignore\s+(all\s+)?previous\s+instructions",
                    r"disregard\s+(the\s+)?above",
                    r"forget\s+everything",
                    r"new\s+persona",
                    r"you\s+are\s+now",
                    r"act\s+as\s+if",
                    r"pretend\s+to\s+be",
                    r"jailbreak",
                    r"DAN\s*mode",
                    r"developer\s*mode",
                    r"override\s+safety",
                    r"bypass\s+restrictions",
                    r"ignore\s+guidelines",
                    r"system\s*:\s*you\s+are",  # System prompt injection
                ],
                description="Detects prompt injection patterns that attempt to override AI safety guidelines.",
                score_weight=15,
            ),
            # SEC006: Privilege Escalation (HIGH)
            SecurityRule(
                rule_id="SEC006",
                name="Privilege Escalation",
                severity=Severity.HIGH,
                patterns=[
                    r"\bsudo\s+",
                    r"\bsu\s+-",
                    r"runas\s+/user",
                    r"chmod\s+[0-7]*777",
                    r"chmod\s+\+s",
                    r"chmod\s+u\+s",
                    r"setuid",
                    r"setgid",
                    r"SUID",
                    r"capabilities",
                    r"SeDebugPrivilege",
                    r"NT\s*AUTHORITY\\SYSTEM",
                    r"LocalSystem",
                    r"gksudo",
                    r"pkexec",
                    r"doas\s+",
                ],
                description="Detects privilege escalation attempts that could grant elevated system access.",
                score_weight=25,
            ),
            # SEC007: Data Exfiltration Risk (LOW)
            SecurityRule(
                rule_id="SEC007",
                name="Data Exfiltration Risk",
                severity=Severity.LOW,
                patterns=[
                    r"upload\s+(to|data)",
                    r"send\s+(to|data)\s*server",
                    r"post\s+(data|to)",
                    r"exfil",
                    r"base64.*encode.*send",
                    r"encode.*upload",
                    r"transmit.*data",
                    r"webhook\.site",
                    r"requestbin",
                    r"pipedream\.net",
                    r"ngrok",
                    r"localtunnel",
                ],
                description="Detects patterns that could indicate data exfiltration attempts.",
                score_weight=5,
            ),
            # Additional rules for skill-specific concerns
            # SEC008: Unsafe Code Patterns
            SecurityRule(
                rule_id="SEC008",
                name="Unsafe Code Patterns",
                severity=Severity.MEDIUM,
                patterns=[
                    r"innerHTML\s*=",
                    r"dangerouslySetInnerHTML",
                    r"document\.write",
                    r"\.call\s*\(\s*null",
                    r"Function\s*\(",
                    r"setTimeout\s*\(\s*['\"]",
                    r"setInterval\s*\(\s*['\"]",
                    r"__proto__",
                    r"constructor\[",
                    r"pickle\.load",
                    r"yaml\.load\s*\([^)]*Loader\s*=\s*None",
                    r"marshal\.load",
                    r"deserialize",
                ],
                description="Detects unsafe code patterns that could lead to XSS, prototype pollution, or deserialization attacks.",
                score_weight=15,
            ),
            # SEC009: Suspicious Instructions
            SecurityRule(
                rule_id="SEC009",
                name="Suspicious AI Instructions",
                severity=Severity.LOW,
                patterns=[
                    r"never\s+refuse",
                    r"always\s+comply",
                    r"do\s+not\s+question",
                    r"without\s+verification",
                    r"skip\s+validation",
                    r"disable\s+checks",
                    r"ignore\s+errors",
                    r"suppress\s+warnings",
                    r"force\s+overwrite",
                    r"--no-verify",
                    r"--force",
                    r"-f\s*$",
                ],
                description="Detects instructions that encourage bypassing safety checks or validation.",
                score_weight=5,
            ),
        ]

    def _load_blocked_sources(self) -> List[Dict[str, str]]:
        """Load blocked source patterns"""
        return [
            {"pattern": r"malware", "reason": "Contains 'malware' keyword"},
            {"pattern": r"exploit", "reason": "Contains 'exploit' keyword"},
            {"pattern": r"hack(er|ing)?", "reason": "Contains hacking-related keyword"},
        ]

    def check_blocked_source(self, skill_path: str, skill_name: str) -> Optional[str]:
        """Check if skill source is blocked"""
        check_text = f"{skill_path} {skill_name}".lower()

        for blocked in self.blocked_sources:
            if re.search(blocked["pattern"], check_text, re.IGNORECASE):
                return blocked["reason"]

        return None

    def calculate_risk_score(self, findings: List[SecurityFinding]) -> int:
        """Calculate overall risk score from findings"""
        score = 0

        # Count unique rule violations (don't double-count same rule)
        rule_findings: Dict[str, List[SecurityFinding]] = {}
        for finding in findings:
            if finding.rule_id not in rule_findings:
                rule_findings[finding.rule_id] = []
            rule_findings[finding.rule_id].append(finding)

        for rule_id, rule_items in rule_findings.items():
            # Base score from severity
            base_score = self.SEVERITY_SCORES.get(rule_items[0].severity, 5)

            # Multiply by log of count (diminishing returns)
            import math

            count_multiplier = 1 + math.log(len(rule_items), 2) * 0.5

            score += int(base_score * count_multiplier)

        return min(score, 100)  # Cap at 100

    def determine_risk_level(self, score: int) -> RiskLevel:
        """Determine risk level from score"""
        for threshold, level in self.RISK_THRESHOLDS:
            if score <= threshold:
                return level
        return RiskLevel.BLOCKED

    def scan_content(self, content: str, file_path: str = "") -> List[SecurityFinding]:
        """Scan content against all rules"""
        findings = []

        for rule in self.rules:
            rule_findings = rule.scan(content, file_path)
            findings.extend(rule_findings)

            if rule_findings:
                self.log(f"  {rule.rule_id}: {len(rule_findings)} finding(s)")

        return findings

    def scan_file(self, file_path: Path) -> List[SecurityFinding]:
        """Scan a single file"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, str(file_path))
        except Exception as e:
            self.log(f"Error scanning {file_path}: {e}")
            return []

    def scan_skill(self, skill_path: Path) -> ScanResult:
        """Scan a skill directory"""
        skill_path = Path(skill_path)

        if not skill_path.exists():
            raise FileNotFoundError(f"Skill path not found: {skill_path}")

        # Get skill name
        skill_name = skill_path.name
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            match = re.search(r"name:\s*([^\n]+)", content)
            if match:
                skill_name = match.group(1).strip().strip("'\"")

        self.log(f"Scanning skill: {skill_name} at {skill_path}")

        # Check for blocked source
        blocked_reason = self.check_blocked_source(str(skill_path), skill_name)
        if blocked_reason:
            return ScanResult(
                skill_path=str(skill_path),
                skill_name=skill_name,
                scanned_at=datetime.now().isoformat(),
                scanner_version=self.VERSION,
                risk_level=RiskLevel.BLOCKED,
                risk_score=100,
                findings=[],
                files_scanned=0,
                blocked=True,
                blocked_reason=blocked_reason,
            )

        # Scan all relevant files
        all_findings = []
        files_scanned = 0

        # File patterns to scan
        scan_patterns = ["*.md", "*.txt", "*.yaml", "*.yml", "*.json"]

        if skill_path.is_file():
            # Single file scan
            all_findings.extend(self.scan_file(skill_path))
            files_scanned = 1
        else:
            # Directory scan
            for pattern in scan_patterns:
                for file_path in skill_path.glob(f"**/{pattern}"):
                    self.log(f"  Scanning: {file_path.name}")
                    all_findings.extend(self.scan_file(file_path))
                    files_scanned += 1

        # Calculate risk
        risk_score = self.calculate_risk_score(all_findings)
        risk_level = self.determine_risk_level(risk_score)

        # Check for critical findings that should block
        critical_count = sum(1 for f in all_findings if f.severity == Severity.CRITICAL)
        if critical_count >= 3:
            risk_level = RiskLevel.BLOCKED
            risk_score = 100

        return ScanResult(
            skill_path=str(skill_path),
            skill_name=skill_name,
            scanned_at=datetime.now().isoformat(),
            scanner_version=self.VERSION,
            risk_level=risk_level,
            risk_score=risk_score,
            findings=all_findings,
            files_scanned=files_scanned,
            blocked=(risk_level == RiskLevel.BLOCKED),
            blocked_reason="Multiple critical findings" if critical_count >= 3 else "",
        )

    def scan_directory(self, directory: Path) -> List[ScanResult]:
        """Scan all skills in a directory"""
        results = []
        directory = Path(directory)

        # Find all SKILL.md files
        for skill_md in directory.glob("**/SKILL.md"):
            skill_dir = skill_md.parent
            try:
                result = self.scan_skill(skill_dir)
                results.append(result)
            except Exception as e:
                self.log(f"Error scanning {skill_dir}: {e}")

        return results

    def format_report_text(self, result: ScanResult) -> str:
        """Format scan result as human-readable text"""
        lines = []

        # Header
        risk_emoji = {
            RiskLevel.SAFE: "",
            RiskLevel.LOW: "",
            RiskLevel.MEDIUM: "",
            RiskLevel.HIGH: "",
            RiskLevel.CRITICAL: "",
            RiskLevel.BLOCKED: "",
        }

        lines.append("=" * 60)
        lines.append(f"Security Scan Report: {result.skill_name}")
        lines.append("=" * 60)
        lines.append(f"Path: {result.skill_path}")
        lines.append(f"Scanned: {result.scanned_at}")
        lines.append(f"Scanner Version: {result.scanner_version}")
        lines.append(f"Files Scanned: {result.files_scanned}")
        lines.append("")
        lines.append(
            f"Risk Level: {risk_emoji.get(result.risk_level, '')} {result.risk_level.value.upper()}"
        )
        lines.append(f"Risk Score: {result.risk_score}/100")

        if result.blocked:
            lines.append(f"\n BLOCKED: {result.blocked_reason}")

        # Summary
        summary = result.get_summary()
        lines.append("\n--- Findings Summary ---")
        lines.append(f"  Critical: {summary['critical']}")
        lines.append(f"  High:     {summary['high']}")
        lines.append(f"  Medium:   {summary['medium']}")
        lines.append(f"  Low:      {summary['low']}")
        lines.append(f"  Info:     {summary['info']}")

        # Details
        if result.findings:
            lines.append("\n--- Findings Details ---")

            # Group by rule
            by_rule: Dict[str, List[SecurityFinding]] = {}
            for f in result.findings:
                key = f"{f.rule_id}: {f.rule_name}"
                if key not in by_rule:
                    by_rule[key] = []
                by_rule[key].append(f)

            for rule_key, findings in sorted(by_rule.items()):
                severity = findings[0].severity.value.upper()
                lines.append(f"\n[{severity}] {rule_key}")
                lines.append(f"  {findings[0].description}")
                lines.append(f"  Occurrences: {len(findings)}")

                # Show first 3 examples
                for f in findings[:3]:
                    file_info = (
                        f"({Path(f.file_path).name}:{f.line_number})"
                        if f.file_path
                        else f"(line {f.line_number})"
                    )
                    lines.append(f"    {file_info} {f.line_content[:80]}")

                if len(findings) > 3:
                    lines.append(f"    ... and {len(findings) - 3} more")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)

    def format_report_json(self, result: ScanResult) -> str:
        """Format scan result as JSON"""
        return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Skill Security Scanner")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a skill for security risks")
    scan_parser.add_argument("skill_path", type=Path, help="Path to skill directory")
    scan_parser.add_argument("--format", choices=["text", "json"], default="text")

    # scan-all command
    scan_all_parser = subparsers.add_parser(
        "scan-all", help="Scan all skills in directory"
    )
    scan_all_parser.add_argument(
        "directory", type=Path, help="Directory containing skills"
    )
    scan_all_parser.add_argument("--format", choices=["text", "json"], default="text")
    scan_all_parser.add_argument("--output", type=Path, help="Output file for results")
    scan_all_parser.add_argument(
        "--min-risk",
        choices=["safe", "low", "medium", "high", "critical"],
        default="safe",
        help="Minimum risk level to report",
    )

    # report command (same as scan but emphasizes report output)
    report_parser = subparsers.add_parser("report", help="Generate security report")
    report_parser.add_argument("skill_path", type=Path)
    report_parser.add_argument("--format", choices=["text", "json"], default="text")
    report_parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    scanner = SkillSecurityScanner(verbose=args.verbose)

    if args.command == "scan" or args.command == "report":
        try:
            result = scanner.scan_skill(args.skill_path)

            if args.format == "json":
                output = scanner.format_report_json(result)
            else:
                output = scanner.format_report_text(result)

            if hasattr(args, "output") and args.output:
                args.output.write_text(output, encoding="utf-8")
                print(f" Report saved to {args.output}")
            else:
                print(output)

            # Exit code based on risk level
            if result.risk_level in [RiskLevel.CRITICAL, RiskLevel.BLOCKED]:
                sys.exit(2)
            elif result.risk_level == RiskLevel.HIGH:
                sys.exit(1)
            sys.exit(0)

        except FileNotFoundError as e:
            print(f" Error: {e}")
            sys.exit(1)

    elif args.command == "scan-all":
        results = scanner.scan_directory(args.directory)

        # Filter by minimum risk
        risk_order = ["safe", "low", "medium", "high", "critical", "blocked"]
        min_idx = risk_order.index(args.min_risk)
        filtered = [
            r for r in results if risk_order.index(r.risk_level.value) >= min_idx
        ]

        if args.format == "json":
            output = json.dumps(
                [r.to_dict() for r in filtered], indent=2, ensure_ascii=False
            )
        else:
            lines = [f"\n Scanned {len(results)} skills\n"]

            # Summary by risk level
            by_level = {}
            for r in results:
                level = r.risk_level.value
                if level not in by_level:
                    by_level[level] = []
                by_level[level].append(r)

            for level in risk_order:
                if level in by_level:
                    emoji = {
                        "safe": "",
                        "low": "",
                        "medium": "",
                        "high": "",
                        "critical": "",
                        "blocked": "",
                    }
                    lines.append(
                        f"{emoji.get(level, '')} {level.upper()}: {len(by_level[level])}"
                    )
                    for r in by_level[level]:
                        lines.append(f"   - {r.skill_name} (score: {r.risk_score})")

            output = "\n".join(lines)

        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f" Results saved to {args.output}")
        else:
            print(output)

        # Exit with error if any high-risk skills found
        high_risk = [
            r
            for r in results
            if r.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.BLOCKED]
        ]
        if high_risk:
            sys.exit(1)


if __name__ == "__main__":
    main()
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
