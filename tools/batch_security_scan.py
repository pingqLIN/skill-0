<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Batch Security Scan Tool for Skill Governance

Performs comprehensive security scans on all pending skills in the governance database.
Updates skill records with:
- risk_level (safe/low/medium/high/critical)
- risk_score (0-100)
- security_findings (JSON)
- security_scanned_at (timestamp)

Also records results in security_scans table for audit trail.

Usage:
    python batch_security_scan.py [--limit N] [--force] [--verbose]
    python batch_security_scan.py --list          # Show pending skills
    python batch_security_scan.py --report        # Show current statistics
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from governance_db import GovernanceDB
from skill_scanner import SkillSecurityScanner, RiskLevel


def find_skill_path(skill_name: str, base_dirs: List[Path]) -> Path:
    """
    Find the source path for a skill.
    Searches in multiple locations:
    1. converted-skills/<skill_name>
    2. parsed/<skill_name>
    3. Use source_path from database if available
    """
    # Try common locations
    for base_dir in base_dirs:
        skill_path = base_dir / skill_name
        if skill_path.exists():
            return skill_path

        # Try with kebab-case
        kebab_name = skill_name.replace("_", "-")
        skill_path = base_dir / kebab_name
        if skill_path.exists():
            return skill_path

    # Last resort - try with underscores and numbers
    for base_dir in base_dirs:
        for item in base_dir.iterdir():
            if item.is_dir() and item.name.lower().startswith(skill_name.lower()):
                return item

    return None


def scan_skill(
    scanner: SkillSecurityScanner,
    skill_name: str,
    source_path: str,
    search_dirs: List[Path],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Scan a single skill and return (success, result_dict)
    """
    result = {
        "skill_name": skill_name,
        "source_path": source_path,
        "scanned_at": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "scan": None,
    }

    try:
        # Try to find the skill directory
        skill_dir = None

        # First try the source_path from database
        if source_path and Path(source_path).exists():
            skill_dir = Path(source_path)
        else:
            # Search in common locations
            skill_dir = find_skill_path(skill_name, search_dirs)

        if not skill_dir or not skill_dir.exists():
            result["error"] = (
                f"Skill directory not found (searched: {source_path}, {search_dirs})"
            )
            return False, result

        # Run security scan
        scan_result = scanner.scan_skill(skill_dir)

        result["success"] = True
        result["scan"] = scan_result.to_dict()
        return True, result

    except Exception as e:
        result["error"] = str(e)
        return False, result


def main():
    parser = argparse.ArgumentParser(
        description="Batch Security Scan for Skill Governance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all pending skills (up to 160)
  python batch_security_scan.py
  
  # Scan only first 10 skills
  python batch_security_scan.py --limit 10
  
  # Force rescan of approved skills
  python batch_security_scan.py --force
  
  # Show pending skills without scanning
  python batch_security_scan.py --list
  
  # Show statistics
  python batch_security_scan.py --report
        """,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of skills to scan (default: all pending)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rescan all skills regardless of status",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List pending skills without scanning",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show statistics without scanning",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--db",
        type=Path,
        help="Database path",
    )

    args = parser.parse_args()

    # Initialize database and scanner
    db = GovernanceDB(db_path=args.db)
    scanner = SkillSecurityScanner(verbose=args.verbose)

    # Set up search directories
    project_root = Path(__file__).parent.parent
    search_dirs = [
        project_root / "converted-skills",
        project_root / "parsed",
    ]

    # Handle --list command
    if args.list:
        skills = db.list_skills(status="pending", limit=1000)
        print(f"\n📋 Pending Skills ({len(skills)}):\n")
        for i, skill in enumerate(skills, 1):
            print(f"  {i:3d}. {skill.name:40s} (ID: {skill.skill_id[:12]}...)")
        print()
        return 0

    # Handle --report command
    if args.report:
        stats = db.get_statistics()
        print(f"\n📊 Skill Governance Statistics\n")
        print(f"   Total Skills:  {stats['total_skills']}")

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

        print()
        return 0

    # Main scanning workflow
    if args.force:
        skills = db.list_skills(limit=1000)
        print(f"\n🔄 Force scanning ALL skills ({len(skills)} total)\n")
    else:
        skills = db.list_skills(status="pending", limit=1000)
        print(f"\n🔍 Scanning pending skills ({len(skills)} pending)\n")

    if args.limit:
        skills = skills[: args.limit]

    if not skills:
        print("No skills to scan.")
        return 0

    print(f"{'=' * 80}")
    print(f"📊 BATCH SECURITY SCAN")
    print(f"{'=' * 80}")
    print(f"Target skills: {len(skills)}")
    print(f"Search directories: {search_dirs}")
    print(f"{'=' * 80}\n")

    # Scan each skill
    scanned = 0
    succeeded = 0
    failed = 0
    errors = []
    results_by_risk = {}

    start_time = datetime.now()

    for i, skill in enumerate(skills, 1):
        print(
            f"[{i:3d}/{len(skills)}] Scanning {skill.name:40s} ... ", end="", flush=True
        )

        try:
            # Scan the skill
            success, scan_result = scan_skill(
                scanner,
                skill.name,
                skill.source_path,
                search_dirs,
            )

            if not success:
                print(f"❌ {scan_result['error'][:50]}")
                failed += 1
                errors.append((skill.name, scan_result["error"]))
                continue

            # Record the scan
            scan_data = scan_result["scan"]
            db.record_security_scan(skill.skill_id, scan_data)

            # Track results
            risk_level = scan_data["risk_level"]
            if risk_level not in results_by_risk:
                results_by_risk[risk_level] = 0
            results_by_risk[risk_level] += 1

            # Print result
            icon = {
                "safe": "🟢",
                "low": "🟡",
                "medium": "🟠",
                "high": "🔴",
                "critical": "⛔",
                "blocked": "🚫",
            }.get(risk_level, "❓")

            print(
                f"✅ {icon} {risk_level.upper():8s} (score: {scan_data['risk_score']:3d})"
            )

            succeeded += 1
            scanned += 1

        except Exception as e:
            print(f"💥 Exception: {str(e)[:40]}")
            failed += 1
            errors.append((skill.name, str(e)))

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # Print summary
    print(f"\n{'=' * 80}")
    print(f"📊 SCAN SUMMARY")
    print(f"{'=' * 80}")
    print(f"✅ Successfully scanned: {succeeded}")
    print(f"❌ Failed scans:         {failed}")
    print(f"📊 Total processed:      {scanned}/{len(skills)}")
    print(
        f"⏱️  Time elapsed:         {elapsed:.1f}s ({elapsed / len(skills) if len(skills) > 0 else 0:.1f}s per skill)"
    )

    # Risk level distribution
    if results_by_risk:
        print(f"\n📈 Risk Level Distribution:")
        risk_order = ["safe", "low", "medium", "high", "critical", "blocked"]
        for level in risk_order:
            if level in results_by_risk:
                count = results_by_risk[level]
                icon = {
                    "safe": "🟢",
                    "low": "🟡",
                    "medium": "🟠",
                    "high": "🔴",
                    "critical": "⛔",
                    "blocked": "🚫",
                }.get(level, "❓")
                pct = (count / succeeded * 100) if succeeded > 0 else 0
                print(f"  {icon} {level:9s}: {count:3d} ({pct:5.1f}%)")

    # Database statistics
    print(f"\n💾 Database Status:")
    stats = db.get_statistics()
    print(f"   Total skills: {stats.get('total_skills', 'N/A')}")
    if stats.get("by_status"):
        for status in ["approved", "pending", "rejected", "blocked"]:
            if status in stats["by_status"]:
                count = stats["by_status"][status]
                icon = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(status, "?")
                print(f"   {icon} {status}: {count}")

    # Show errors if any
    if errors:
        print(f"\n⚠️  First 10 Errors:")
        for skill_name, error in errors[:10]:
            error_short = error[:60] + "..." if len(error) > 60 else error
            print(f"   - {skill_name}: {error_short}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")

    print(f"\n{'=' * 80}\n")

    # Return success if no failures
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""
Batch Security Scan Tool for Skill Governance

Performs comprehensive security scans on all pending skills in the governance database.
Updates skill records with:
- risk_level (safe/low/medium/high/critical)
- risk_score (0-100)
- security_findings (JSON)
- security_scanned_at (timestamp)

Also records results in security_scans table for audit trail.

Usage:
    python batch_security_scan.py [--limit N] [--force] [--verbose]
    python batch_security_scan.py --list          # Show pending skills
    python batch_security_scan.py --report        # Show current statistics
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from governance_db import GovernanceDB
from skill_scanner import SkillSecurityScanner, RiskLevel


def find_skill_path(skill_name: str, base_dirs: List[Path]) -> Path:
    """
    Find the source path for a skill.
    Searches in multiple locations:
    1. converted-skills/<skill_name>
    2. parsed/<skill_name>
    3. Use source_path from database if available
    """
    # Try common locations
    for base_dir in base_dirs:
        skill_path = base_dir / skill_name
        if skill_path.exists():
            return skill_path

        # Try with kebab-case
        kebab_name = skill_name.replace("_", "-")
        skill_path = base_dir / kebab_name
        if skill_path.exists():
            return skill_path

    # Last resort - try with underscores and numbers
    for base_dir in base_dirs:
        for item in base_dir.iterdir():
            if item.is_dir() and item.name.lower().startswith(skill_name.lower()):
                return item

    return None


def scan_skill(
    scanner: SkillSecurityScanner,
    skill_name: str,
    source_path: str,
    search_dirs: List[Path],
) -> Tuple[bool, Dict[str, Any]]:
    """
    Scan a single skill and return (success, result_dict)
    """
    result = {
        "skill_name": skill_name,
        "source_path": source_path,
        "scanned_at": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "scan": None,
    }

    try:
        # Try to find the skill directory
        skill_dir = None

        # First try the source_path from database
        if source_path and Path(source_path).exists():
            skill_dir = Path(source_path)
        else:
            # Search in common locations
            skill_dir = find_skill_path(skill_name, search_dirs)

        if not skill_dir or not skill_dir.exists():
            result["error"] = (
                f"Skill directory not found (searched: {source_path}, {search_dirs})"
            )
            return False, result

        # Run security scan
        scan_result = scanner.scan_skill(skill_dir)

        result["success"] = True
        result["scan"] = scan_result.to_dict()
        return True, result

    except Exception as e:
        result["error"] = str(e)
        return False, result


def main():
    parser = argparse.ArgumentParser(
        description="Batch Security Scan for Skill Governance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all pending skills (up to 160)
  python batch_security_scan.py
  
  # Scan only first 10 skills
  python batch_security_scan.py --limit 10
  
  # Force rescan of approved skills
  python batch_security_scan.py --force
  
  # Show pending skills without scanning
  python batch_security_scan.py --list
  
  # Show statistics
  python batch_security_scan.py --report
        """,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of skills to scan (default: all pending)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rescan all skills regardless of status",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List pending skills without scanning",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show statistics without scanning",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--db",
        type=Path,
        help="Database path",
    )

    args = parser.parse_args()

    # Initialize database and scanner
    db = GovernanceDB(db_path=args.db)
    scanner = SkillSecurityScanner(verbose=args.verbose)

    # Set up search directories
    project_root = Path(__file__).parent.parent
    search_dirs = [
        project_root / "converted-skills",
        project_root / "parsed",
    ]

    # Handle --list command
    if args.list:
        skills = db.list_skills(status="pending", limit=1000)
        print(f"\n📋 Pending Skills ({len(skills)}):\n")
        for i, skill in enumerate(skills, 1):
            print(f"  {i:3d}. {skill.name:40s} (ID: {skill.skill_id[:12]}...)")
        print()
        return 0

    # Handle --report command
    if args.report:
        stats = db.get_statistics()
        print(f"\n📊 Skill Governance Statistics\n")
        print(f"   Total Skills:  {stats['total_skills']}")

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

        print()
        return 0

    # Main scanning workflow
    if args.force:
        skills = db.list_skills(limit=1000)
        print(f"\n🔄 Force scanning ALL skills ({len(skills)} total)\n")
    else:
        skills = db.list_skills(status="pending", limit=1000)
        print(f"\n🔍 Scanning pending skills ({len(skills)} pending)\n")

    if args.limit:
        skills = skills[: args.limit]

    if not skills:
        print("No skills to scan.")
        return 0

    print(f"{'=' * 80}")
    print(f"📊 BATCH SECURITY SCAN")
    print(f"{'=' * 80}")
    print(f"Target skills: {len(skills)}")
    print(f"Search directories: {search_dirs}")
    print(f"{'=' * 80}\n")

    # Scan each skill
    scanned = 0
    succeeded = 0
    failed = 0
    errors = []
    results_by_risk = {}

    start_time = datetime.now()

    for i, skill in enumerate(skills, 1):
        print(
            f"[{i:3d}/{len(skills)}] Scanning {skill.name:40s} ... ", end="", flush=True
        )

        try:
            # Scan the skill
            success, scan_result = scan_skill(
                scanner,
                skill.name,
                skill.source_path,
                search_dirs,
            )

            if not success:
                print(f"❌ {scan_result['error'][:50]}")
                failed += 1
                errors.append((skill.name, scan_result["error"]))
                continue

            # Record the scan
            scan_data = scan_result["scan"]
            db.record_security_scan(skill.skill_id, scan_data)

            # Track results
            risk_level = scan_data["risk_level"]
            if risk_level not in results_by_risk:
                results_by_risk[risk_level] = 0
            results_by_risk[risk_level] += 1

            # Print result
            icon = {
                "safe": "🟢",
                "low": "🟡",
                "medium": "🟠",
                "high": "🔴",
                "critical": "⛔",
                "blocked": "🚫",
            }.get(risk_level, "❓")

            print(
                f"✅ {icon} {risk_level.upper():8s} (score: {scan_data['risk_score']:3d})"
            )

            succeeded += 1
            scanned += 1

        except Exception as e:
            print(f"💥 Exception: {str(e)[:40]}")
            failed += 1
            errors.append((skill.name, str(e)))

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # Print summary
    print(f"\n{'=' * 80}")
    print(f"📊 SCAN SUMMARY")
    print(f"{'=' * 80}")
    print(f"✅ Successfully scanned: {succeeded}")
    print(f"❌ Failed scans:         {failed}")
    print(f"📊 Total processed:      {scanned}/{len(skills)}")
    print(
        f"⏱️  Time elapsed:         {elapsed:.1f}s ({elapsed / len(skills) if len(skills) > 0 else 0:.1f}s per skill)"
    )

    # Risk level distribution
    if results_by_risk:
        print(f"\n📈 Risk Level Distribution:")
        risk_order = ["safe", "low", "medium", "high", "critical", "blocked"]
        for level in risk_order:
            if level in results_by_risk:
                count = results_by_risk[level]
                icon = {
                    "safe": "🟢",
                    "low": "🟡",
                    "medium": "🟠",
                    "high": "🔴",
                    "critical": "⛔",
                    "blocked": "🚫",
                }.get(level, "❓")
                pct = (count / succeeded * 100) if succeeded > 0 else 0
                print(f"  {icon} {level:9s}: {count:3d} ({pct:5.1f}%)")

    # Database statistics
    print(f"\n💾 Database Status:")
    stats = db.get_statistics()
    print(f"   Total skills: {stats.get('total_skills', 'N/A')}")
    if stats.get("by_status"):
        for status in ["approved", "pending", "rejected", "blocked"]:
            if status in stats["by_status"]:
                count = stats["by_status"][status]
                icon = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌",
                    "blocked": "🚫",
                }.get(status, "?")
                print(f"   {icon} {status}: {count}")

    # Show errors if any
    if errors:
        print(f"\n⚠️  First 10 Errors:")
        for skill_name, error in errors[:10]:
            error_short = error[:60] + "..." if len(error) > 60 else error
            print(f"   - {skill_name}: {error_short}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more errors")

    print(f"\n{'=' * 80}\n")

    # Return success if no failures
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
