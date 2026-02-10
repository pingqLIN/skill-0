<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""
Batch Rescan Tool - Context-Aware Security Rescan

Re-scans skills that were flagged as high/critical/blocked using the
context-aware Advanced Skill Analyzer to reduce false positives.

The advanced analyzer:
1. Parses Markdown structure to identify code blocks
2. Reduces severity for patterns found in code examples
3. Tracks original vs adjusted severity for transparency
4. Provides detailed context and standard references

Usage:
    python batch_rescan.py                      # Rescan all flagged skills
    python batch_rescan.py --dry-run            # Preview without DB updates
    python batch_rescan.py --risk-levels critical blocked  # Only specific levels
    python batch_rescan.py --skill-name docker  # Rescan specific skill
    python batch_rescan.py --report             # Show improvement summary

Author: skill-0 project
Created: 2026-01-27
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from governance_db import GovernanceDB
from advanced_skill_analyzer import AdvancedSkillAnalyzer, RiskLevel


def find_skill_path(
    skill_name: str, source_path: str, base_dirs: List[Path]
) -> Optional[Path]:
    """
    Find the source path for a skill.
    Searches in multiple locations:
    1. Use source_path from database if available
    2. converted-skills/<skill_name>
    3. parsed/<skill_name>
    """
    # First try the source_path from database
    if source_path:
        sp = Path(source_path)
        if sp.exists():
            return sp

    # Try common locations
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue

        skill_path = base_dir / skill_name
        if skill_path.exists():
            return skill_path

        # Try with kebab-case
        kebab_name = skill_name.replace("_", "-")
        skill_path = base_dir / kebab_name
        if skill_path.exists():
            return skill_path

    # Last resort - partial match
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
        for item in base_dir.iterdir():
            if item.is_dir() and item.name.lower().startswith(skill_name.lower()[:10]):
                return item

    return None


def rescan_skill(
    analyzer: AdvancedSkillAnalyzer,
    skill_name: str,
    source_path: str,
    search_dirs: List[Path],
    verbose: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Rescan a single skill with the advanced analyzer.
    Returns (success, result_dict)
    """
    result = {
        "skill_name": skill_name,
        "source_path": source_path,
        "scanned_at": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "scan": None,
        "improvements": {},
    }

    try:
        # Find the skill directory
        skill_dir = find_skill_path(skill_name, source_path, search_dirs)

        if not skill_dir or not skill_dir.exists():
            result["error"] = f"Skill directory not found for '{skill_name}'"
            return False, result

        if verbose:
            print(f"  Scanning: {skill_dir}")

        # Run advanced security scan
        scan_result = analyzer.scan_skill(skill_dir)

        # Convert to dict for storage
        result["scan"] = scan_result.to_dict()
        result["success"] = True

        # Store key metrics for easy access
        result["new_risk_level"] = scan_result.risk_level.value
        result["new_risk_score"] = scan_result.risk_score
        result["original_risk_score"] = scan_result.original_risk_score
        result["findings_count"] = len(scan_result.findings)
        result["findings_in_code_blocks"] = scan_result.findings_in_code_blocks
        result["severity_adjustments"] = scan_result.severity_adjustments
        result["code_blocks_found"] = scan_result.code_blocks_found

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            import traceback

            traceback.print_exc()

    return result["success"], result


def main():
    parser = argparse.ArgumentParser(
        description="Rescan flagged skills with context-aware analyzer"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating database",
    )
    parser.add_argument(
        "--risk-levels",
        nargs="+",
        default=["high", "critical", "blocked"],
        help="Risk levels to rescan (default: high critical blocked)",
    )
    parser.add_argument(
        "--skill-name",
        type=str,
        help="Rescan a specific skill by name",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of skills to process",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show improvement report after scanning",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to governance database",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save detailed results to JSON file",
    )

    args = parser.parse_args()

    # Initialize
    project_root = Path(__file__).parent.parent
    db_path = args.db_path or project_root / "governance" / "db" / "governance.db"

    db = GovernanceDB(db_path)
    analyzer = AdvancedSkillAnalyzer(verbose=args.verbose)

    # Search directories for skill files
    search_dirs = [
        project_root / "converted-skills",
        project_root / "parsed",
        Path.cwd() / "converted-skills",
    ]

    print("=" * 70)
    print("Context-Aware Batch Rescan")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Analyzer: Advanced Skill Analyzer v{analyzer.VERSION}")
    print(f"Risk levels to rescan: {', '.join(args.risk_levels)}")
    print(f"Dry run: {args.dry_run}")
    print("")

    # Get skills to rescan
    skills_to_rescan = []

    if args.skill_name:
        # Single skill mode
        skill = db.get_skill(name=args.skill_name)
        if skill:
            skills_to_rescan.append(skill)
        else:
            print(f"Error: Skill '{args.skill_name}' not found in database")
            return 1
    else:
        # Batch mode - get all skills with specified risk levels
        for risk_level in args.risk_levels:
            skills = db.list_skills(risk_level=risk_level, limit=args.limit)
            skills_to_rescan.extend(skills)

    if not skills_to_rescan:
        print("No skills found matching criteria.")
        return 0

    print(f"Found {len(skills_to_rescan)} skills to rescan")
    print("-" * 70)

    # Track results
    results = []
    improvements = {
        "total_scanned": 0,
        "successful": 0,
        "failed": 0,
        "risk_reduced": 0,
        "level_changes": [],
        "total_score_reduction": 0,
    }

    for i, skill in enumerate(skills_to_rescan, 1):
        print(f"\n[{i}/{len(skills_to_rescan)}] {skill.name}")
        print(f"  Current: {skill.risk_level} (score: {skill.risk_score})")

        success, result = rescan_skill(
            analyzer=analyzer,
            skill_name=skill.name,
            source_path=skill.source_path,
            search_dirs=search_dirs,
            verbose=args.verbose,
        )

        results.append(result)
        improvements["total_scanned"] += 1

        if not success:
            print(f"  ERROR: {result['error']}")
            improvements["failed"] += 1
            continue

        improvements["successful"] += 1

        new_level = result["new_risk_level"]
        new_score = result["new_risk_score"]
        old_score = skill.risk_score
        score_diff = old_score - new_score

        print(f"  New:     {new_level} (score: {new_score})")

        if score_diff > 0:
            print(f"  Reduced: -{score_diff} points")
            improvements["risk_reduced"] += 1
            improvements["total_score_reduction"] += score_diff

        if skill.risk_level != new_level:
            change = {
                "skill_name": skill.name,
                "old_level": skill.risk_level,
                "new_level": new_level,
                "old_score": old_score,
                "new_score": new_score,
            }
            improvements["level_changes"].append(change)
            print(f"  Level:   {skill.risk_level} -> {new_level}")

        # Context stats
        if result.get("code_blocks_found", 0) > 0:
            print(
                f"  Context: {result['findings_in_code_blocks']} of {result['findings_count']} "
                f"findings in {result['code_blocks_found']} code blocks"
            )

        # Update database (unless dry run)
        if not args.dry_run:
            scan_data = result["scan"]

            # Record the scan
            db.record_security_scan(
                skill_id=skill.skill_id,
                scan_result={
                    "scanned_at": scan_data["scanned_at"],
                    "scanner_version": scan_data["scanner_version"],
                    "risk_level": scan_data["risk_level"],
                    "risk_score": scan_data["risk_score"],
                    "files_scanned": scan_data["files_scanned"],
                    "findings_count": scan_data["findings_count"],
                    "findings": scan_data["findings"],
                    "blocked": scan_data["blocked"],
                    "blocked_reason": scan_data.get("blocked_reason", ""),
                },
            )

            # If skill was blocked but now isn't, update status
            if skill.risk_level == "blocked" and new_level != "blocked":
                db.update_skill(skill.skill_id, status="pending")
                print(f"  Status:  blocked -> pending (needs review)")

    # Summary
    print("\n" + "=" * 70)
    print("RESCAN SUMMARY")
    print("=" * 70)
    print(f"Total scanned:    {improvements['total_scanned']}")
    print(f"Successful:       {improvements['successful']}")
    print(f"Failed:           {improvements['failed']}")
    print(f"Risk reduced:     {improvements['risk_reduced']}")
    print(f"Total reduction:  -{improvements['total_score_reduction']} points")
    print(f"Level changes:    {len(improvements['level_changes'])}")

    if improvements["level_changes"]:
        print("\nLevel Changes:")
        for change in improvements["level_changes"]:
            print(
                f"  {change['skill_name']}: "
                f"{change['old_level']} ({change['old_score']}) -> "
                f"{change['new_level']} ({change['new_score']})"
            )

    if args.dry_run:
        print("\n[DRY RUN] No database changes were made.")

    # Save detailed results
    if args.output:
        output_data = {
            "run_at": datetime.now().isoformat(),
            "analyzer_version": analyzer.VERSION,
            "dry_run": args.dry_run,
            "summary": improvements,
            "results": results,
        }
        args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
        print(f"\nDetailed results saved to: {args.output}")

    # Report mode
    if args.report:
        print("\n" + "=" * 70)
        print("IMPROVEMENT REPORT")
        print("=" * 70)

        # Get current distribution
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT risk_level, COUNT(*) as count 
                FROM skills 
                GROUP BY risk_level 
                ORDER BY 
                    CASE risk_level 
                        WHEN 'blocked' THEN 1
                        WHEN 'critical' THEN 2
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 4
                        WHEN 'low' THEN 5
                        WHEN 'safe' THEN 6
                        ELSE 7
                    END
            """)

            print("\nCurrent Risk Distribution:")
            for row in cursor.fetchall():
                print(f"  {row['risk_level']:10}: {row['count']}")

    return 0


if __name__ == "__main__":
    exit(main())
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""
Batch Rescan Tool - Context-Aware Security Rescan

Re-scans skills that were flagged as high/critical/blocked using the
context-aware Advanced Skill Analyzer to reduce false positives.

The advanced analyzer:
1. Parses Markdown structure to identify code blocks
2. Reduces severity for patterns found in code examples
3. Tracks original vs adjusted severity for transparency
4. Provides detailed context and standard references

Usage:
    python batch_rescan.py                      # Rescan all flagged skills
    python batch_rescan.py --dry-run            # Preview without DB updates
    python batch_rescan.py --risk-levels critical blocked  # Only specific levels
    python batch_rescan.py --skill-name docker  # Rescan specific skill
    python batch_rescan.py --report             # Show improvement summary

Author: skill-0 project
Created: 2026-01-27
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from governance_db import GovernanceDB
from advanced_skill_analyzer import AdvancedSkillAnalyzer, RiskLevel


def find_skill_path(
    skill_name: str, source_path: str, base_dirs: List[Path]
) -> Optional[Path]:
    """
    Find the source path for a skill.
    Searches in multiple locations:
    1. Use source_path from database if available
    2. converted-skills/<skill_name>
    3. parsed/<skill_name>
    """
    # First try the source_path from database
    if source_path:
        sp = Path(source_path)
        if sp.exists():
            return sp

    # Try common locations
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue

        skill_path = base_dir / skill_name
        if skill_path.exists():
            return skill_path

        # Try with kebab-case
        kebab_name = skill_name.replace("_", "-")
        skill_path = base_dir / kebab_name
        if skill_path.exists():
            return skill_path

    # Last resort - partial match
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
        for item in base_dir.iterdir():
            if item.is_dir() and item.name.lower().startswith(skill_name.lower()[:10]):
                return item

    return None


def rescan_skill(
    analyzer: AdvancedSkillAnalyzer,
    skill_name: str,
    source_path: str,
    search_dirs: List[Path],
    verbose: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Rescan a single skill with the advanced analyzer.
    Returns (success, result_dict)
    """
    result = {
        "skill_name": skill_name,
        "source_path": source_path,
        "scanned_at": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "scan": None,
        "improvements": {},
    }

    try:
        # Find the skill directory
        skill_dir = find_skill_path(skill_name, source_path, search_dirs)

        if not skill_dir or not skill_dir.exists():
            result["error"] = f"Skill directory not found for '{skill_name}'"
            return False, result

        if verbose:
            print(f"  Scanning: {skill_dir}")

        # Run advanced security scan
        scan_result = analyzer.scan_skill(skill_dir)

        # Convert to dict for storage
        result["scan"] = scan_result.to_dict()
        result["success"] = True

        # Store key metrics for easy access
        result["new_risk_level"] = scan_result.risk_level.value
        result["new_risk_score"] = scan_result.risk_score
        result["original_risk_score"] = scan_result.original_risk_score
        result["findings_count"] = len(scan_result.findings)
        result["findings_in_code_blocks"] = scan_result.findings_in_code_blocks
        result["severity_adjustments"] = scan_result.severity_adjustments
        result["code_blocks_found"] = scan_result.code_blocks_found

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            import traceback

            traceback.print_exc()

    return result["success"], result


def main():
    parser = argparse.ArgumentParser(
        description="Rescan flagged skills with context-aware analyzer"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without updating database",
    )
    parser.add_argument(
        "--risk-levels",
        nargs="+",
        default=["high", "critical", "blocked"],
        help="Risk levels to rescan (default: high critical blocked)",
    )
    parser.add_argument(
        "--skill-name",
        type=str,
        help="Rescan a specific skill by name",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of skills to process",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Show improvement report after scanning",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to governance database",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save detailed results to JSON file",
    )

    args = parser.parse_args()

    # Initialize
    project_root = Path(__file__).parent.parent
    db_path = args.db_path or project_root / "governance" / "db" / "governance.db"

    db = GovernanceDB(db_path)
    analyzer = AdvancedSkillAnalyzer(verbose=args.verbose)

    # Search directories for skill files
    search_dirs = [
        project_root / "converted-skills",
        project_root / "parsed",
        Path.cwd() / "converted-skills",
    ]

    print("=" * 70)
    print("Context-Aware Batch Rescan")
    print("=" * 70)
    print(f"Database: {db_path}")
    print(f"Analyzer: Advanced Skill Analyzer v{analyzer.VERSION}")
    print(f"Risk levels to rescan: {', '.join(args.risk_levels)}")
    print(f"Dry run: {args.dry_run}")
    print("")

    # Get skills to rescan
    skills_to_rescan = []

    if args.skill_name:
        # Single skill mode
        skill = db.get_skill(name=args.skill_name)
        if skill:
            skills_to_rescan.append(skill)
        else:
            print(f"Error: Skill '{args.skill_name}' not found in database")
            return 1
    else:
        # Batch mode - get all skills with specified risk levels
        for risk_level in args.risk_levels:
            skills = db.list_skills(risk_level=risk_level, limit=args.limit)
            skills_to_rescan.extend(skills)

    if not skills_to_rescan:
        print("No skills found matching criteria.")
        return 0

    print(f"Found {len(skills_to_rescan)} skills to rescan")
    print("-" * 70)

    # Track results
    results = []
    improvements = {
        "total_scanned": 0,
        "successful": 0,
        "failed": 0,
        "risk_reduced": 0,
        "level_changes": [],
        "total_score_reduction": 0,
    }

    for i, skill in enumerate(skills_to_rescan, 1):
        print(f"\n[{i}/{len(skills_to_rescan)}] {skill.name}")
        print(f"  Current: {skill.risk_level} (score: {skill.risk_score})")

        success, result = rescan_skill(
            analyzer=analyzer,
            skill_name=skill.name,
            source_path=skill.source_path,
            search_dirs=search_dirs,
            verbose=args.verbose,
        )

        results.append(result)
        improvements["total_scanned"] += 1

        if not success:
            print(f"  ERROR: {result['error']}")
            improvements["failed"] += 1
            continue

        improvements["successful"] += 1

        new_level = result["new_risk_level"]
        new_score = result["new_risk_score"]
        old_score = skill.risk_score
        score_diff = old_score - new_score

        print(f"  New:     {new_level} (score: {new_score})")

        if score_diff > 0:
            print(f"  Reduced: -{score_diff} points")
            improvements["risk_reduced"] += 1
            improvements["total_score_reduction"] += score_diff

        if skill.risk_level != new_level:
            change = {
                "skill_name": skill.name,
                "old_level": skill.risk_level,
                "new_level": new_level,
                "old_score": old_score,
                "new_score": new_score,
            }
            improvements["level_changes"].append(change)
            print(f"  Level:   {skill.risk_level} -> {new_level}")

        # Context stats
        if result.get("code_blocks_found", 0) > 0:
            print(
                f"  Context: {result['findings_in_code_blocks']} of {result['findings_count']} "
                f"findings in {result['code_blocks_found']} code blocks"
            )

        # Update database (unless dry run)
        if not args.dry_run:
            scan_data = result["scan"]

            # Record the scan
            db.record_security_scan(
                skill_id=skill.skill_id,
                scan_result={
                    "scanned_at": scan_data["scanned_at"],
                    "scanner_version": scan_data["scanner_version"],
                    "risk_level": scan_data["risk_level"],
                    "risk_score": scan_data["risk_score"],
                    "files_scanned": scan_data["files_scanned"],
                    "findings_count": scan_data["findings_count"],
                    "findings": scan_data["findings"],
                    "blocked": scan_data["blocked"],
                    "blocked_reason": scan_data.get("blocked_reason", ""),
                },
            )

            # If skill was blocked but now isn't, update status
            if skill.risk_level == "blocked" and new_level != "blocked":
                db.update_skill(skill.skill_id, status="pending")
                print(f"  Status:  blocked -> pending (needs review)")

    # Summary
    print("\n" + "=" * 70)
    print("RESCAN SUMMARY")
    print("=" * 70)
    print(f"Total scanned:    {improvements['total_scanned']}")
    print(f"Successful:       {improvements['successful']}")
    print(f"Failed:           {improvements['failed']}")
    print(f"Risk reduced:     {improvements['risk_reduced']}")
    print(f"Total reduction:  -{improvements['total_score_reduction']} points")
    print(f"Level changes:    {len(improvements['level_changes'])}")

    if improvements["level_changes"]:
        print("\nLevel Changes:")
        for change in improvements["level_changes"]:
            print(
                f"  {change['skill_name']}: "
                f"{change['old_level']} ({change['old_score']}) -> "
                f"{change['new_level']} ({change['new_score']})"
            )

    if args.dry_run:
        print("\n[DRY RUN] No database changes were made.")

    # Save detailed results
    if args.output:
        output_data = {
            "run_at": datetime.now().isoformat(),
            "analyzer_version": analyzer.VERSION,
            "dry_run": args.dry_run,
            "summary": improvements,
            "results": results,
        }
        args.output.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
        print(f"\nDetailed results saved to: {args.output}")

    # Report mode
    if args.report:
        print("\n" + "=" * 70)
        print("IMPROVEMENT REPORT")
        print("=" * 70)

        # Get current distribution
        with db.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT risk_level, COUNT(*) as count 
                FROM skills 
                GROUP BY risk_level 
                ORDER BY 
                    CASE risk_level 
                        WHEN 'blocked' THEN 1
                        WHEN 'critical' THEN 2
                        WHEN 'high' THEN 3
                        WHEN 'medium' THEN 4
                        WHEN 'low' THEN 5
                        WHEN 'safe' THEN 6
                        ELSE 7
                    END
            """)

            print("\nCurrent Risk Distribution:")
            for row in cursor.fetchall():
                print(f"  {row['risk_level']:10}: {row['count']}")

    return 0


if __name__ == "__main__":
    exit(main())
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
