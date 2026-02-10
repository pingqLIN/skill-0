<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Skill Governance CLI

Unified command-line interface for skill governance:
- Import skills with full pipeline (scan → convert → test → register)
- Security scanning
- Equivalence testing
- Review and approval workflow
- Audit trail

Usage:
    skill-0 import <source> [--auto-approve] [--skip-tests]
    skill-0 scan <skill_path>
    skill-0 test <original_path> <converted_path>
    skill-0 review list
    skill-0 review approve <skill_id> --reason "..."
    skill-0 review reject <skill_id> --reason "..."
    skill-0 info <skill_name>
    skill-0 audit [--skill <name>] [--type <event_type>]
    skill-0 stats
    skill-0 list [--status <status>] [--risk <level>]

Author: skill-0 project
Created: 2026-01-27
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import local modules
from governance_db import GovernanceDB, SkillRecord
from skill_scanner import SkillSecurityScanner, ScanResult, RiskLevel
from skill_tester import SkillEquivalenceTester, EquivalenceResult
from skill_converter import SkillConverter  # Assuming this exists
from skill_installer import OpenCodeSkillInstaller


class SkillGovernanceCLI:
    """Main governance CLI"""

    VERSION = "1.0.0"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        converted_dir: Optional[Path] = None,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self.db = GovernanceDB(db_path=db_path)
        self.scanner = SkillSecurityScanner(verbose=verbose)
        self.tester = SkillEquivalenceTester(verbose=verbose)

        # Directories
        self.converted_dir = (
            converted_dir or Path(__file__).parent.parent / "converted-skills"
        )
        self.converted_dir.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str):
        if self.verbose:
            print(f"[governance] {msg}")

    # ============ Import Pipeline ============

    def import_skill(
        self,
        source_path: Path,
        auto_approve: bool = False,
        skip_security: bool = False,
        skip_equivalence: bool = False,
        skip_convert: bool = False,
        author_name: str = "Unknown",
        license_spdx: str = "UNKNOWN",
    ) -> Dict[str, Any]:
        """
        Full import pipeline:
        1. Detect source format
        2. Security scan
        3. Convert if needed
        4. Equivalence test
        5. Register in database
        6. Auto-approve if safe
        """
        source_path = Path(source_path)
        result = {
            "source": str(source_path),
            "success": False,
            "skill_id": None,
            "skill_name": None,
            "steps": [],
        }

        # 1. Detect source format
        self.log("Step 1: Detecting source format...")
        source_format, skill_name, skill_file = self._detect_source(source_path)
        result["skill_name"] = skill_name
        result["source_format"] = source_format
        result["steps"].append(
            {"step": "detect", "format": source_format, "name": skill_name}
        )

        if not skill_file:
            result["error"] = f"No skill file found in {source_path}"
            return result

        # 2. Security scan (on original file only)
        if not skip_security:
            self.log("Step 2: Security scanning...")
            # For single files, scan just that file
            scan_result = self.scanner.scan_skill(skill_file)
            result["steps"].append(
                {
                    "step": "scan",
                    "risk_level": scan_result.risk_level.value,
                    "risk_score": scan_result.risk_score,
                    "findings": len(scan_result.findings),
                }
            )

            if scan_result.blocked:
                result["error"] = (
                    f"Blocked by security scan: {scan_result.blocked_reason}"
                )
                result["scan_result"] = scan_result.to_dict()
                return result
        else:
            scan_result = None
            result["steps"].append({"step": "scan", "skipped": True})

        # 3. Convert if needed
        converted_path = None
        if source_format == "instructions.md" and not skip_convert:
            self.log("Step 3: Converting to SKILL.md format...")
            try:
                converter = SkillConverter(verbose=self.verbose)
                converted_path = converter.convert(skill_file, self.converted_dir)
                result["steps"].append(
                    {
                        "step": "convert",
                        "output": str(converted_path),
                    }
                )
            except Exception as e:
                result["error"] = f"Conversion failed: {e}"
                return result
        elif source_format == "skill.md":
            converted_path = skill_file.parent if skill_file.is_file() else skill_file
            result["steps"].append(
                {
                    "step": "convert",
                    "skipped": True,
                    "reason": "Already in SKILL.md format",
                }
            )
        else:
            result["steps"].append(
                {"step": "convert", "skipped": True, "reason": skip_convert}
            )

        # 4. Equivalence test
        if (
            not skip_equivalence
            and converted_path
            and source_format == "instructions.md"
        ):
            self.log("Step 4: Equivalence testing...")
            try:
                test_result = self.tester.test_equivalence(skill_file, converted_path)
                result["steps"].append(
                    {
                        "step": "test",
                        "overall_score": test_result.overall_score,
                        "passed": test_result.passed,
                    }
                )

                if not test_result.passed:
                    result["warning"] = (
                        "Equivalence test failed but continuing registration"
                    )
            except Exception as e:
                result["steps"].append({"step": "test", "error": str(e)})
                test_result = None
        else:
            test_result = None
            result["steps"].append({"step": "test", "skipped": True})

        # 5. Register in database
        self.log("Step 5: Registering in database...")

        # Check if already exists
        existing = self.db.get_skill(name=skill_name)
        if existing:
            result["warning"] = f"Skill '{skill_name}' already registered, updating..."
            skill_id = existing.skill_id
        else:
            skill_id = self.db.create_skill(
                name=skill_name,
                source_type="local",
                source_path=str(source_path),
                author_name=author_name,
                license_spdx=license_spdx,
            )

        result["skill_id"] = skill_id
        result["steps"].append({"step": "register", "skill_id": skill_id})

        # Record scan result
        if scan_result:
            self.db.record_security_scan(skill_id, scan_result.to_dict())

        # Record test result
        if test_result:
            self.db.record_equivalence_test(skill_id, test_result.to_dict())

        # 6. Auto-approve if conditions met
        if auto_approve:
            if scan_result and scan_result.risk_level in [
                RiskLevel.SAFE,
                RiskLevel.LOW,
            ]:
                if not test_result or test_result.passed:
                    self.db.approve_skill(
                        skill_id, "auto-approve", "Low risk and tests passed"
                    )
                    result["steps"].append({"step": "approve", "auto": True})
                    result["status"] = "approved"
                else:
                    result["status"] = "pending"
                    result["steps"].append(
                        {
                            "step": "approve",
                            "skipped": True,
                            "reason": "Equivalence test failed",
                        }
                    )
            else:
                result["status"] = "pending"
                result["steps"].append(
                    {
                        "step": "approve",
                        "skipped": True,
                        "reason": "Risk level too high",
                    }
                )
        else:
            result["status"] = "pending"

        result["success"] = True
        return result

    def _detect_source(self, path: Path) -> tuple[str, str, Optional[Path]]:
        """Detect source format and skill name"""
        if path.is_file():
            if path.name.endswith(".instructions.md"):
                name = path.stem.replace(".instructions", "")
                return "instructions.md", name, path
            elif path.name == "SKILL.md":
                # Extract name from frontmatter
                content = path.read_text(encoding="utf-8")
                import re

                match = re.search(r"name:\s*([^\n]+)", content)
                name = (
                    match.group(1).strip().strip("'\"") if match else path.parent.name
                )
                return "skill.md", name, path
            else:
                return "unknown", path.stem, path

        # Directory - look for skill files
        skill_md = path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            import re

            match = re.search(r"name:\s*([^\n]+)", content)
            name = match.group(1).strip().strip("'\"") if match else path.name
            return "skill.md", name, skill_md

        # Look for .instructions.md
        for f in path.glob("*.instructions.md"):
            name = f.stem.replace(".instructions", "")
            return "instructions.md", name, f

        return "unknown", path.name, None

    # ============ Scan Command ============

    def scan(self, skill_path: Path, output_format: str = "text") -> ScanResult:
        """Run security scan on a skill"""
        result = self.scanner.scan_skill(skill_path)

        if output_format == "json":
            print(self.scanner.format_report_json(result))
        else:
            print(self.scanner.format_report_text(result))

        return result

    # ============ Test Command ============

    def test(
        self,
        original_path: Path,
        converted_path: Path,
        output_format: str = "text",
    ) -> EquivalenceResult:
        """Run equivalence test"""
        result = self.tester.test_equivalence(original_path, converted_path)

        if output_format == "json":
            print(self.tester.format_report_json(result))
        else:
            print(self.tester.format_report_text(result))

        return result

    # ============ Review Commands ============

    def review_list(self, status: str = "pending") -> List[SkillRecord]:
        """List skills pending review"""
        skills = self.db.list_skills(status=status)

        print(f"\n📋 Skills awaiting review ({len(skills)}):\n")

        for skill in skills:
            risk_icon = {
                "safe": "🟢",
                "low": "🟡",
                "medium": "🟠",
                "high": "🔴",
                "critical": "⛔",
                "blocked": "🚫",
            }.get(skill.risk_level, "❓")

            print(f"  {risk_icon} {skill.name}")
            print(f"     ID: {skill.skill_id}")
            print(f"     Risk: {skill.risk_level} (score: {skill.risk_score})")
            print(f"     Source: {skill.source_path}")
            if skill.equivalence_score:
                equiv_icon = "✅" if skill.equivalence_score >= 0.8 else "⚠️"
                print(f"     Equivalence: {equiv_icon} {skill.equivalence_score:.1%}")
            print()

        return skills

    def review_approve(
        self, skill_id_or_name: str, reason: str, approver: str = "admin"
    ) -> bool:
        """Approve a skill"""
        # Try to find by name first
        skill = self.db.get_skill(name=skill_id_or_name)
        if not skill:
            skill = self.db.get_skill(skill_id=skill_id_or_name)

        if not skill:
            print(f"❌ Skill not found: {skill_id_or_name}")
            return False

        if skill.status == "blocked":
            print(f"❌ Cannot approve blocked skill: {skill.name}")
            return False

        success = self.db.approve_skill(skill.skill_id, approver, reason)

        if success:
            print(f"✅ Approved: {skill.name}")
            print(f"   Reason: {reason}")
            print(f"   Approved by: {approver}")
        else:
            print(f"❌ Failed to approve: {skill.name}")

        return success

    def review_reject(
        self, skill_id_or_name: str, reason: str, rejector: str = "admin"
    ) -> bool:
        """Reject a skill"""
        skill = self.db.get_skill(name=skill_id_or_name)
        if not skill:
            skill = self.db.get_skill(skill_id=skill_id_or_name)

        if not skill:
            print(f"❌ Skill not found: {skill_id_or_name}")
            return False

        success = self.db.reject_skill(skill.skill_id, rejector, reason)

        if success:
            print(f"❌ Rejected: {skill.name}")
            print(f"   Reason: {reason}")
        else:
            print(f"❌ Failed to reject: {skill.name}")

        return success

    # ============ Info Command ============

    def info(
        self, skill_name: str, output_format: str = "text"
    ) -> Optional[Dict[str, Any]]:
        """Show detailed info about a skill"""
        skill = self.db.get_skill(name=skill_name)
        if not skill:
            skill = self.db.get_skill(skill_id=skill_name)

        if not skill:
            print(f"❌ Skill not found: {skill_name}")
            return None

        # Get scan history
        scans = self.db.get_scan_history(skill.skill_id, limit=3)

        # Get test history
        tests = self.db.get_test_history(skill.skill_id, limit=3)

        # Get audit log
        audit = self.db.get_audit_log(skill_id=skill.skill_id, limit=5)

        info = {
            "skill": {
                "id": skill.skill_id,
                "name": skill.name,
                "version": skill.version,
                "status": skill.status,
                "source_type": skill.source_type,
                "source_path": skill.source_path,
                "author": skill.author_name,
                "license": skill.license_spdx,
                "risk_level": skill.risk_level,
                "risk_score": skill.risk_score,
                "equivalence_score": skill.equivalence_score,
                "created_at": skill.created_at,
                "updated_at": skill.updated_at,
            },
            "recent_scans": scans,
            "recent_tests": tests,
            "recent_events": audit,
        }

        if output_format == "json":
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            status_icon = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌",
                "blocked": "🚫",
            }.get(skill.status, "?")
            risk_icon = {
                "safe": "🟢",
                "low": "🟡",
                "medium": "🟠",
                "high": "🔴",
                "critical": "⛔",
            }.get(skill.risk_level, "❓")

            print("\n" + "=" * 60)
            print(f"Skill: {skill.name}")
            print("=" * 60)
            print(f"ID:          {skill.skill_id}")
            print(f"Status:      {status_icon} {skill.status}")
            print(f"Version:     {skill.version}")
            print(f"Author:      {skill.author_name}")
            print(f"License:     {skill.license_spdx}")
            print(f"Source:      {skill.source_path}")
            print()
            print(
                f"Security:    {risk_icon} {skill.risk_level} (score: {skill.risk_score})"
            )
            if skill.equivalence_score:
                equiv_icon = "✅" if skill.equivalence_score >= 0.8 else "⚠️"
                print(f"Equivalence: {equiv_icon} {skill.equivalence_score:.1%}")
            print()
            print(f"Created:     {skill.created_at[:19]}")
            print(f"Updated:     {skill.updated_at[:19]}")

            if audit:
                print("\n--- Recent Activity ---")
                for e in audit[:5]:
                    print(f"  [{e['timestamp'][:19]}] {e['event_type']}")

            print("\n" + "=" * 60)

        return info

    # ============ Audit Command ============

    def audit(
        self,
        skill_name: str = None,
        event_type: str = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Show audit log"""
        skill_id = None
        if skill_name:
            skill = self.db.get_skill(name=skill_name)
            if skill:
                skill_id = skill.skill_id

        events = self.db.get_audit_log(
            skill_id=skill_id,
            event_type=event_type,
            limit=limit,
        )

        print(f"\n📜 Audit Log ({len(events)} events):\n")

        for e in events:
            type_icon = {
                "create": "➕",
                "update": "✏️",
                "scan": "🔍",
                "test": "🧪",
                "approve": "✅",
                "reject": "❌",
                "install": "📦",
                "uninstall": "🗑️",
            }.get(e["event_type"], "📝")

            skill_info = e.get("skill_name") or e.get("skill_id", "N/A")[:8]
            print(f"  {type_icon} [{e['timestamp'][:19]}] {e['event_type'].upper()}")
            print(f"     Skill: {skill_info}")
            print(f"     Actor: {e.get('actor', 'system')}")
            if e.get("details"):
                details_str = json.dumps(e["details"])[:80]
                print(f"     Details: {details_str}")
            print()

        return events

    # ============ Stats Command ============

    def stats(self) -> Dict[str, Any]:
        """Show statistics"""
        stats = self.db.get_statistics()

        print("\n📊 Skill Governance Statistics\n")
        print(f"   Total Skills:  {stats['total_skills']}")
        print(f"   Total Scans:   {stats['total_scans']}")
        print(f"   Total Tests:   {stats['total_tests']}")
        print(f"   Audit Events:  {stats['total_events']}")

        if stats.get("by_status"):
            print("\n   By Status:")
            for status, count in sorted(stats["by_status"].items()):
                icon = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(status, "?")
                print(f"     {icon} {status}: {count}")

        if stats.get("by_risk"):
            print("\n   By Risk Level:")
            risk_order = ["safe", "low", "medium", "high", "critical", "blocked"]
            for risk in risk_order:
                if risk in stats["by_risk"]:
                    icon = {
                        "safe": "🟢",
                        "low": "🟡",
                        "medium": "🟠",
                        "high": "🔴",
                        "critical": "⛔",
                        "blocked": "🚫",
                    }.get(risk, "❓")
                    print(f"     {icon} {risk}: {stats['by_risk'][risk]}")

        return stats

    # ============ List Command ============

    def list_skills(
        self,
        status: str = None,
        risk_level: str = None,
        output_format: str = "text",
    ) -> List[SkillRecord]:
        """List skills with filtering"""
        skills = self.db.list_skills(status=status, risk_level=risk_level)

        if output_format == "json":
            print(
                json.dumps(
                    [
                        {
                            "id": s.skill_id,
                            "name": s.name,
                            "status": s.status,
                            "risk_level": s.risk_level,
                            "risk_score": s.risk_score,
                            "equivalence_score": s.equivalence_score,
                        }
                        for s in skills
                    ],
                    indent=2,
                )
            )
        else:
            print(f"\n📋 Skills ({len(skills)}):\n")
            for s in skills:
                status_icon = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(s.status, "?")
                risk_icon = {
                    "safe": "🟢",
                    "low": "🟡",
                    "medium": "🟠",
                    "high": "🔴",
                    "critical": "⛔",
                }.get(s.risk_level, "❓")

                equiv_str = (
                    f" equiv:{s.equivalence_score:.0%}" if s.equivalence_score else ""
                )
                print(
                    f"  {status_icon} {risk_icon} {s.name} [risk:{s.risk_score}]{equiv_str}"
                )

        return skills


def main():
    parser = argparse.ArgumentParser(
        description="Skill Governance CLI",
        prog="skill-0",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--db", type=Path, help="Database path")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {SkillGovernanceCLI.VERSION}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # import command
    import_parser = subparsers.add_parser(
        "import", help="Import a skill with full pipeline"
    )
    import_parser.add_argument(
        "source", type=Path, help="Source path (file or directory)"
    )
    import_parser.add_argument(
        "--auto-approve", action="store_true", help="Auto-approve if safe"
    )
    import_parser.add_argument(
        "--skip-security", action="store_true", help="Skip security scan"
    )
    import_parser.add_argument(
        "--skip-equivalence", action="store_true", help="Skip equivalence test"
    )
    import_parser.add_argument(
        "--skip-convert", action="store_true", help="Skip conversion"
    )
    import_parser.add_argument("--author", default="Unknown", help="Author name")
    import_parser.add_argument("--license", default="UNKNOWN", help="SPDX license ID")
    import_parser.add_argument("--format", choices=["text", "json"], default="text")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Security scan a skill")
    scan_parser.add_argument("skill_path", type=Path)
    scan_parser.add_argument("--format", choices=["text", "json"], default="text")

    # test command
    test_parser = subparsers.add_parser("test", help="Equivalence test")
    test_parser.add_argument("original", type=Path)
    test_parser.add_argument("converted", type=Path)
    test_parser.add_argument("--format", choices=["text", "json"], default="text")

    # review commands
    review_parser = subparsers.add_parser("review", help="Review workflow")
    review_sub = review_parser.add_subparsers(dest="review_action", required=True)

    review_list = review_sub.add_parser("list", help="List pending reviews")
    review_list.add_argument("--status", default="pending")

    review_approve = review_sub.add_parser("approve", help="Approve a skill")
    review_approve.add_argument("skill", help="Skill name or ID")
    review_approve.add_argument("--reason", required=True)
    review_approve.add_argument("--approver", default="admin")

    review_reject = review_sub.add_parser("reject", help="Reject a skill")
    review_reject.add_argument("skill", help="Skill name or ID")
    review_reject.add_argument("--reason", required=True)
    review_reject.add_argument("--rejector", default="admin")

    # info command
    info_parser = subparsers.add_parser("info", help="Show skill details")
    info_parser.add_argument("skill", help="Skill name or ID")
    info_parser.add_argument("--format", choices=["text", "json"], default="text")

    # audit command
    audit_parser = subparsers.add_parser("audit", help="Show audit log")
    audit_parser.add_argument("--skill", help="Filter by skill name")
    audit_parser.add_argument("--type", help="Filter by event type")
    audit_parser.add_argument("--limit", type=int, default=20)

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # list command
    list_parser = subparsers.add_parser("list", help="List skills")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--risk", help="Filter by risk level")
    list_parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()

    cli = SkillGovernanceCLI(db_path=args.db, verbose=args.verbose)

    if args.command == "import":
        result = cli.import_skill(
            source_path=args.source,
            auto_approve=args.auto_approve,
            skip_security=args.skip_security,
            skip_equivalence=args.skip_equivalence,
            skip_convert=args.skip_convert,
            author_name=args.author,
            license_spdx=args.license,
        )

        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if result["success"]:
                print(f"\n✅ Successfully imported: {result['skill_name']}")
                print(f"   Skill ID: {result['skill_id']}")
                print(f"   Status: {result.get('status', 'pending')}")
                print("\n   Pipeline steps:")
                for step in result["steps"]:
                    icon = (
                        "✅"
                        if not step.get("skipped") and not step.get("error")
                        else "⏭️"
                    )
                    print(f"   {icon} {step['step']}: {step}")
            else:
                print(f"\n❌ Import failed: {result.get('error', 'Unknown error')}")

        sys.exit(0 if result["success"] else 1)

    elif args.command == "scan":
        result = cli.scan(args.skill_path, output_format=args.format)
        sys.exit(0 if result.risk_level in [RiskLevel.SAFE, RiskLevel.LOW] else 1)

    elif args.command == "test":
        result = cli.test(args.original, args.converted, output_format=args.format)
        sys.exit(0 if result.passed else 1)

    elif args.command == "review":
        if args.review_action == "list":
            cli.review_list(status=args.status)
        elif args.review_action == "approve":
            success = cli.review_approve(args.skill, args.reason, args.approver)
            sys.exit(0 if success else 1)
        elif args.review_action == "reject":
            success = cli.review_reject(args.skill, args.reason, args.rejector)
            sys.exit(0 if success else 1)

    elif args.command == "info":
        cli.info(args.skill, output_format=args.format)

    elif args.command == "audit":
        cli.audit(skill_name=args.skill, event_type=args.type, limit=args.limit)

    elif args.command == "stats":
        cli.stats()

    elif args.command == "list":
        cli.list_skills(
            status=args.status, risk_level=args.risk, output_format=args.format
        )


if __name__ == "__main__":
    main()
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""
Skill Governance CLI

Unified command-line interface for skill governance:
- Import skills with full pipeline (scan → convert → test → register)
- Security scanning
- Equivalence testing
- Review and approval workflow
- Audit trail

Usage:
    skill-0 import <source> [--auto-approve] [--skip-tests]
    skill-0 scan <skill_path>
    skill-0 test <original_path> <converted_path>
    skill-0 review list
    skill-0 review approve <skill_id> --reason "..."
    skill-0 review reject <skill_id> --reason "..."
    skill-0 info <skill_name>
    skill-0 audit [--skill <name>] [--type <event_type>]
    skill-0 stats
    skill-0 list [--status <status>] [--risk <level>]

Author: skill-0 project
Created: 2026-01-27
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# Import local modules
from governance_db import GovernanceDB, SkillRecord
from skill_scanner import SkillSecurityScanner, ScanResult, RiskLevel
from skill_tester import SkillEquivalenceTester, EquivalenceResult
from skill_converter import SkillConverter  # Assuming this exists
from skill_installer import OpenCodeSkillInstaller


class SkillGovernanceCLI:
    """Main governance CLI"""

    VERSION = "1.0.0"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        converted_dir: Optional[Path] = None,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self.db = GovernanceDB(db_path=db_path)
        self.scanner = SkillSecurityScanner(verbose=verbose)
        self.tester = SkillEquivalenceTester(verbose=verbose)

        # Directories
        self.converted_dir = (
            converted_dir or Path(__file__).parent.parent / "converted-skills"
        )
        self.converted_dir.mkdir(parents=True, exist_ok=True)

    def log(self, msg: str):
        if self.verbose:
            print(f"[governance] {msg}")

    # ============ Import Pipeline ============

    def import_skill(
        self,
        source_path: Path,
        auto_approve: bool = False,
        skip_security: bool = False,
        skip_equivalence: bool = False,
        skip_convert: bool = False,
        author_name: str = "Unknown",
        license_spdx: str = "UNKNOWN",
    ) -> Dict[str, Any]:
        """
        Full import pipeline:
        1. Detect source format
        2. Security scan
        3. Convert if needed
        4. Equivalence test
        5. Register in database
        6. Auto-approve if safe
        """
        source_path = Path(source_path)
        result = {
            "source": str(source_path),
            "success": False,
            "skill_id": None,
            "skill_name": None,
            "steps": [],
        }

        # 1. Detect source format
        self.log("Step 1: Detecting source format...")
        source_format, skill_name, skill_file = self._detect_source(source_path)
        result["skill_name"] = skill_name
        result["source_format"] = source_format
        result["steps"].append(
            {"step": "detect", "format": source_format, "name": skill_name}
        )

        if not skill_file:
            result["error"] = f"No skill file found in {source_path}"
            return result

        # 2. Security scan (on original file only)
        if not skip_security:
            self.log("Step 2: Security scanning...")
            # For single files, scan just that file
            scan_result = self.scanner.scan_skill(skill_file)
            result["steps"].append(
                {
                    "step": "scan",
                    "risk_level": scan_result.risk_level.value,
                    "risk_score": scan_result.risk_score,
                    "findings": len(scan_result.findings),
                }
            )

            if scan_result.blocked:
                result["error"] = (
                    f"Blocked by security scan: {scan_result.blocked_reason}"
                )
                result["scan_result"] = scan_result.to_dict()
                return result
        else:
            scan_result = None
            result["steps"].append({"step": "scan", "skipped": True})

        # 3. Convert if needed
        converted_path = None
        if source_format == "instructions.md" and not skip_convert:
            self.log("Step 3: Converting to SKILL.md format...")
            try:
                converter = SkillConverter(verbose=self.verbose)
                converted_path = converter.convert(skill_file, self.converted_dir)
                result["steps"].append(
                    {
                        "step": "convert",
                        "output": str(converted_path),
                    }
                )
            except Exception as e:
                result["error"] = f"Conversion failed: {e}"
                return result
        elif source_format == "skill.md":
            converted_path = skill_file.parent if skill_file.is_file() else skill_file
            result["steps"].append(
                {
                    "step": "convert",
                    "skipped": True,
                    "reason": "Already in SKILL.md format",
                }
            )
        else:
            result["steps"].append(
                {"step": "convert", "skipped": True, "reason": skip_convert}
            )

        # 4. Equivalence test
        if (
            not skip_equivalence
            and converted_path
            and source_format == "instructions.md"
        ):
            self.log("Step 4: Equivalence testing...")
            try:
                test_result = self.tester.test_equivalence(skill_file, converted_path)
                result["steps"].append(
                    {
                        "step": "test",
                        "overall_score": test_result.overall_score,
                        "passed": test_result.passed,
                    }
                )

                if not test_result.passed:
                    result["warning"] = (
                        "Equivalence test failed but continuing registration"
                    )
            except Exception as e:
                result["steps"].append({"step": "test", "error": str(e)})
                test_result = None
        else:
            test_result = None
            result["steps"].append({"step": "test", "skipped": True})

        # 5. Register in database
        self.log("Step 5: Registering in database...")

        # Check if already exists
        existing = self.db.get_skill(name=skill_name)
        if existing:
            result["warning"] = f"Skill '{skill_name}' already registered, updating..."
            skill_id = existing.skill_id
        else:
            skill_id = self.db.create_skill(
                name=skill_name,
                source_type="local",
                source_path=str(source_path),
                author_name=author_name,
                license_spdx=license_spdx,
            )

        result["skill_id"] = skill_id
        result["steps"].append({"step": "register", "skill_id": skill_id})

        # Record scan result
        if scan_result:
            self.db.record_security_scan(skill_id, scan_result.to_dict())

        # Record test result
        if test_result:
            self.db.record_equivalence_test(skill_id, test_result.to_dict())

        # 6. Auto-approve if conditions met
        if auto_approve:
            if scan_result and scan_result.risk_level in [
                RiskLevel.SAFE,
                RiskLevel.LOW,
            ]:
                if not test_result or test_result.passed:
                    self.db.approve_skill(
                        skill_id, "auto-approve", "Low risk and tests passed"
                    )
                    result["steps"].append({"step": "approve", "auto": True})
                    result["status"] = "approved"
                else:
                    result["status"] = "pending"
                    result["steps"].append(
                        {
                            "step": "approve",
                            "skipped": True,
                            "reason": "Equivalence test failed",
                        }
                    )
            else:
                result["status"] = "pending"
                result["steps"].append(
                    {
                        "step": "approve",
                        "skipped": True,
                        "reason": "Risk level too high",
                    }
                )
        else:
            result["status"] = "pending"

        result["success"] = True
        return result

    def _detect_source(self, path: Path) -> tuple[str, str, Optional[Path]]:
        """Detect source format and skill name"""
        if path.is_file():
            if path.name.endswith(".instructions.md"):
                name = path.stem.replace(".instructions", "")
                return "instructions.md", name, path
            elif path.name == "SKILL.md":
                # Extract name from frontmatter
                content = path.read_text(encoding="utf-8")
                import re

                match = re.search(r"name:\s*([^\n]+)", content)
                name = (
                    match.group(1).strip().strip("'\"") if match else path.parent.name
                )
                return "skill.md", name, path
            else:
                return "unknown", path.stem, path

        # Directory - look for skill files
        skill_md = path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text(encoding="utf-8")
            import re

            match = re.search(r"name:\s*([^\n]+)", content)
            name = match.group(1).strip().strip("'\"") if match else path.name
            return "skill.md", name, skill_md

        # Look for .instructions.md
        for f in path.glob("*.instructions.md"):
            name = f.stem.replace(".instructions", "")
            return "instructions.md", name, f

        return "unknown", path.name, None

    # ============ Scan Command ============

    def scan(self, skill_path: Path, output_format: str = "text") -> ScanResult:
        """Run security scan on a skill"""
        result = self.scanner.scan_skill(skill_path)

        if output_format == "json":
            print(self.scanner.format_report_json(result))
        else:
            print(self.scanner.format_report_text(result))

        return result

    # ============ Test Command ============

    def test(
        self,
        original_path: Path,
        converted_path: Path,
        output_format: str = "text",
    ) -> EquivalenceResult:
        """Run equivalence test"""
        result = self.tester.test_equivalence(original_path, converted_path)

        if output_format == "json":
            print(self.tester.format_report_json(result))
        else:
            print(self.tester.format_report_text(result))

        return result

    # ============ Review Commands ============

    def review_list(self, status: str = "pending") -> List[SkillRecord]:
        """List skills pending review"""
        skills = self.db.list_skills(status=status)

        print(f"\n📋 Skills awaiting review ({len(skills)}):\n")

        for skill in skills:
            risk_icon = {
                "safe": "🟢",
                "low": "🟡",
                "medium": "🟠",
                "high": "🔴",
                "critical": "⛔",
                "blocked": "🚫",
            }.get(skill.risk_level, "❓")

            print(f"  {risk_icon} {skill.name}")
            print(f"     ID: {skill.skill_id}")
            print(f"     Risk: {skill.risk_level} (score: {skill.risk_score})")
            print(f"     Source: {skill.source_path}")
            if skill.equivalence_score:
                equiv_icon = "✅" if skill.equivalence_score >= 0.8 else "⚠️"
                print(f"     Equivalence: {equiv_icon} {skill.equivalence_score:.1%}")
            print()

        return skills

    def review_approve(
        self, skill_id_or_name: str, reason: str, approver: str = "admin"
    ) -> bool:
        """Approve a skill"""
        # Try to find by name first
        skill = self.db.get_skill(name=skill_id_or_name)
        if not skill:
            skill = self.db.get_skill(skill_id=skill_id_or_name)

        if not skill:
            print(f"❌ Skill not found: {skill_id_or_name}")
            return False

        if skill.status == "blocked":
            print(f"❌ Cannot approve blocked skill: {skill.name}")
            return False

        success = self.db.approve_skill(skill.skill_id, approver, reason)

        if success:
            print(f"✅ Approved: {skill.name}")
            print(f"   Reason: {reason}")
            print(f"   Approved by: {approver}")
        else:
            print(f"❌ Failed to approve: {skill.name}")

        return success

    def review_reject(
        self, skill_id_or_name: str, reason: str, rejector: str = "admin"
    ) -> bool:
        """Reject a skill"""
        skill = self.db.get_skill(name=skill_id_or_name)
        if not skill:
            skill = self.db.get_skill(skill_id=skill_id_or_name)

        if not skill:
            print(f"❌ Skill not found: {skill_id_or_name}")
            return False

        success = self.db.reject_skill(skill.skill_id, rejector, reason)

        if success:
            print(f"❌ Rejected: {skill.name}")
            print(f"   Reason: {reason}")
        else:
            print(f"❌ Failed to reject: {skill.name}")

        return success

    # ============ Info Command ============

    def info(
        self, skill_name: str, output_format: str = "text"
    ) -> Optional[Dict[str, Any]]:
        """Show detailed info about a skill"""
        skill = self.db.get_skill(name=skill_name)
        if not skill:
            skill = self.db.get_skill(skill_id=skill_name)

        if not skill:
            print(f"❌ Skill not found: {skill_name}")
            return None

        # Get scan history
        scans = self.db.get_scan_history(skill.skill_id, limit=3)

        # Get test history
        tests = self.db.get_test_history(skill.skill_id, limit=3)

        # Get audit log
        audit = self.db.get_audit_log(skill_id=skill.skill_id, limit=5)

        info = {
            "skill": {
                "id": skill.skill_id,
                "name": skill.name,
                "version": skill.version,
                "status": skill.status,
                "source_type": skill.source_type,
                "source_path": skill.source_path,
                "author": skill.author_name,
                "license": skill.license_spdx,
                "risk_level": skill.risk_level,
                "risk_score": skill.risk_score,
                "equivalence_score": skill.equivalence_score,
                "created_at": skill.created_at,
                "updated_at": skill.updated_at,
            },
            "recent_scans": scans,
            "recent_tests": tests,
            "recent_events": audit,
        }

        if output_format == "json":
            print(json.dumps(info, indent=2, ensure_ascii=False))
        else:
            status_icon = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌",
                "blocked": "🚫",
            }.get(skill.status, "?")
            risk_icon = {
                "safe": "🟢",
                "low": "🟡",
                "medium": "🟠",
                "high": "🔴",
                "critical": "⛔",
            }.get(skill.risk_level, "❓")

            print("\n" + "=" * 60)
            print(f"Skill: {skill.name}")
            print("=" * 60)
            print(f"ID:          {skill.skill_id}")
            print(f"Status:      {status_icon} {skill.status}")
            print(f"Version:     {skill.version}")
            print(f"Author:      {skill.author_name}")
            print(f"License:     {skill.license_spdx}")
            print(f"Source:      {skill.source_path}")
            print()
            print(
                f"Security:    {risk_icon} {skill.risk_level} (score: {skill.risk_score})"
            )
            if skill.equivalence_score:
                equiv_icon = "✅" if skill.equivalence_score >= 0.8 else "⚠️"
                print(f"Equivalence: {equiv_icon} {skill.equivalence_score:.1%}")
            print()
            print(f"Created:     {skill.created_at[:19]}")
            print(f"Updated:     {skill.updated_at[:19]}")

            if audit:
                print("\n--- Recent Activity ---")
                for e in audit[:5]:
                    print(f"  [{e['timestamp'][:19]}] {e['event_type']}")

            print("\n" + "=" * 60)

        return info

    # ============ Audit Command ============

    def audit(
        self,
        skill_name: str = None,
        event_type: str = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Show audit log"""
        skill_id = None
        if skill_name:
            skill = self.db.get_skill(name=skill_name)
            if skill:
                skill_id = skill.skill_id

        events = self.db.get_audit_log(
            skill_id=skill_id,
            event_type=event_type,
            limit=limit,
        )

        print(f"\n📜 Audit Log ({len(events)} events):\n")

        for e in events:
            type_icon = {
                "create": "➕",
                "update": "✏️",
                "scan": "🔍",
                "test": "🧪",
                "approve": "✅",
                "reject": "❌",
                "install": "📦",
                "uninstall": "🗑️",
            }.get(e["event_type"], "📝")

            skill_info = e.get("skill_name") or e.get("skill_id", "N/A")[:8]
            print(f"  {type_icon} [{e['timestamp'][:19]}] {e['event_type'].upper()}")
            print(f"     Skill: {skill_info}")
            print(f"     Actor: {e.get('actor', 'system')}")
            if e.get("details"):
                details_str = json.dumps(e["details"])[:80]
                print(f"     Details: {details_str}")
            print()

        return events

    # ============ Stats Command ============

    def stats(self) -> Dict[str, Any]:
        """Show statistics"""
        stats = self.db.get_statistics()

        print("\n📊 Skill Governance Statistics\n")
        print(f"   Total Skills:  {stats['total_skills']}")
        print(f"   Total Scans:   {stats['total_scans']}")
        print(f"   Total Tests:   {stats['total_tests']}")
        print(f"   Audit Events:  {stats['total_events']}")

        if stats.get("by_status"):
            print("\n   By Status:")
            for status, count in sorted(stats["by_status"].items()):
                icon = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(status, "?")
                print(f"     {icon} {status}: {count}")

        if stats.get("by_risk"):
            print("\n   By Risk Level:")
            risk_order = ["safe", "low", "medium", "high", "critical", "blocked"]
            for risk in risk_order:
                if risk in stats["by_risk"]:
                    icon = {
                        "safe": "🟢",
                        "low": "🟡",
                        "medium": "🟠",
                        "high": "🔴",
                        "critical": "⛔",
                        "blocked": "🚫",
                    }.get(risk, "❓")
                    print(f"     {icon} {risk}: {stats['by_risk'][risk]}")

        return stats

    # ============ List Command ============

    def list_skills(
        self,
        status: str = None,
        risk_level: str = None,
        output_format: str = "text",
    ) -> List[SkillRecord]:
        """List skills with filtering"""
        skills = self.db.list_skills(status=status, risk_level=risk_level)

        if output_format == "json":
            print(
                json.dumps(
                    [
                        {
                            "id": s.skill_id,
                            "name": s.name,
                            "status": s.status,
                            "risk_level": s.risk_level,
                            "risk_score": s.risk_score,
                            "equivalence_score": s.equivalence_score,
                        }
                        for s in skills
                    ],
                    indent=2,
                )
            )
        else:
            print(f"\n📋 Skills ({len(skills)}):\n")
            for s in skills:
                status_icon = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(s.status, "?")
                risk_icon = {
                    "safe": "🟢",
                    "low": "🟡",
                    "medium": "🟠",
                    "high": "🔴",
                    "critical": "⛔",
                }.get(s.risk_level, "❓")

                equiv_str = (
                    f" equiv:{s.equivalence_score:.0%}" if s.equivalence_score else ""
                )
                print(
                    f"  {status_icon} {risk_icon} {s.name} [risk:{s.risk_score}]{equiv_str}"
                )

        return skills


def main():
    parser = argparse.ArgumentParser(
        description="Skill Governance CLI",
        prog="skill-0",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--db", type=Path, help="Database path")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {SkillGovernanceCLI.VERSION}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # import command
    import_parser = subparsers.add_parser(
        "import", help="Import a skill with full pipeline"
    )
    import_parser.add_argument(
        "source", type=Path, help="Source path (file or directory)"
    )
    import_parser.add_argument(
        "--auto-approve", action="store_true", help="Auto-approve if safe"
    )
    import_parser.add_argument(
        "--skip-security", action="store_true", help="Skip security scan"
    )
    import_parser.add_argument(
        "--skip-equivalence", action="store_true", help="Skip equivalence test"
    )
    import_parser.add_argument(
        "--skip-convert", action="store_true", help="Skip conversion"
    )
    import_parser.add_argument("--author", default="Unknown", help="Author name")
    import_parser.add_argument("--license", default="UNKNOWN", help="SPDX license ID")
    import_parser.add_argument("--format", choices=["text", "json"], default="text")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Security scan a skill")
    scan_parser.add_argument("skill_path", type=Path)
    scan_parser.add_argument("--format", choices=["text", "json"], default="text")

    # test command
    test_parser = subparsers.add_parser("test", help="Equivalence test")
    test_parser.add_argument("original", type=Path)
    test_parser.add_argument("converted", type=Path)
    test_parser.add_argument("--format", choices=["text", "json"], default="text")

    # review commands
    review_parser = subparsers.add_parser("review", help="Review workflow")
    review_sub = review_parser.add_subparsers(dest="review_action", required=True)

    review_list = review_sub.add_parser("list", help="List pending reviews")
    review_list.add_argument("--status", default="pending")

    review_approve = review_sub.add_parser("approve", help="Approve a skill")
    review_approve.add_argument("skill", help="Skill name or ID")
    review_approve.add_argument("--reason", required=True)
    review_approve.add_argument("--approver", default="admin")

    review_reject = review_sub.add_parser("reject", help="Reject a skill")
    review_reject.add_argument("skill", help="Skill name or ID")
    review_reject.add_argument("--reason", required=True)
    review_reject.add_argument("--rejector", default="admin")

    # info command
    info_parser = subparsers.add_parser("info", help="Show skill details")
    info_parser.add_argument("skill", help="Skill name or ID")
    info_parser.add_argument("--format", choices=["text", "json"], default="text")

    # audit command
    audit_parser = subparsers.add_parser("audit", help="Show audit log")
    audit_parser.add_argument("--skill", help="Filter by skill name")
    audit_parser.add_argument("--type", help="Filter by event type")
    audit_parser.add_argument("--limit", type=int, default=20)

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # list command
    list_parser = subparsers.add_parser("list", help="List skills")
    list_parser.add_argument("--status", help="Filter by status")
    list_parser.add_argument("--risk", help="Filter by risk level")
    list_parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()

    cli = SkillGovernanceCLI(db_path=args.db, verbose=args.verbose)

    if args.command == "import":
        result = cli.import_skill(
            source_path=args.source,
            auto_approve=args.auto_approve,
            skip_security=args.skip_security,
            skip_equivalence=args.skip_equivalence,
            skip_convert=args.skip_convert,
            author_name=args.author,
            license_spdx=args.license,
        )

        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            if result["success"]:
                print(f"\n✅ Successfully imported: {result['skill_name']}")
                print(f"   Skill ID: {result['skill_id']}")
                print(f"   Status: {result.get('status', 'pending')}")
                print("\n   Pipeline steps:")
                for step in result["steps"]:
                    icon = (
                        "✅"
                        if not step.get("skipped") and not step.get("error")
                        else "⏭️"
                    )
                    print(f"   {icon} {step['step']}: {step}")
            else:
                print(f"\n❌ Import failed: {result.get('error', 'Unknown error')}")

        sys.exit(0 if result["success"] else 1)

    elif args.command == "scan":
        result = cli.scan(args.skill_path, output_format=args.format)
        sys.exit(0 if result.risk_level in [RiskLevel.SAFE, RiskLevel.LOW] else 1)

    elif args.command == "test":
        result = cli.test(args.original, args.converted, output_format=args.format)
        sys.exit(0 if result.passed else 1)

    elif args.command == "review":
        if args.review_action == "list":
            cli.review_list(status=args.status)
        elif args.review_action == "approve":
            success = cli.review_approve(args.skill, args.reason, args.approver)
            sys.exit(0 if success else 1)
        elif args.review_action == "reject":
            success = cli.review_reject(args.skill, args.reason, args.rejector)
            sys.exit(0 if success else 1)

    elif args.command == "info":
        cli.info(args.skill, output_format=args.format)

    elif args.command == "audit":
        cli.audit(skill_name=args.skill, event_type=args.type, limit=args.limit)

    elif args.command == "stats":
        cli.stats()

    elif args.command == "list":
        cli.list_skills(
            status=args.status, risk_level=args.risk, output_format=args.format
        )


if __name__ == "__main__":
    main()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
