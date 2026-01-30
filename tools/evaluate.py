#!/usr/bin/env python3
"""
Skill-0 Analyzer Coverage and Performance Evaluation
"""

import json
import time
from pathlib import Path
from datetime import datetime


def evaluate_coverage():
    """Evaluate framework coverage"""
    parsed_dir = Path("parsed")
    skills = list(parsed_dir.glob("*.json"))
    
    coverage_results = {
        "total_skills": len(skills),
        "coverage_by_type": {},
        "uncovered_elements": [],
        "action_type_coverage": {},
        "directive_type_coverage": {},
    }
    
    # Define expected element types
    expected_action_types = {"io_read", "io_write", "transform", "external_call", "await_input"}
    expected_directive_types = {"completion", "knowledge", "principle", "constraint", "preference", "strategy"}
    
    found_action_types = set()
    found_directive_types = set()
    
    for skill_file in skills:
        with open(skill_file, 'r', encoding='utf-8') as f:
            skill = json.load(f)
        
        decomp = skill.get("decomposition", {})
        
        # Collect action types
        for action in decomp.get("actions", []):
            found_action_types.add(action.get("action_type", "unknown"))
        
        # Collect directive types
        for directive in decomp.get("directives", []):
            found_directive_types.add(directive.get("directive_type", "unknown"))
    
    # Calculate coverage
    coverage_results["action_type_coverage"] = {
        "expected": list(expected_action_types),
        "found": list(found_action_types),
        "missing": list(expected_action_types - found_action_types),
        "coverage_rate": len(found_action_types & expected_action_types) / len(expected_action_types)
    }
    
    coverage_results["directive_type_coverage"] = {
        "expected": list(expected_directive_types),
        "found": list(found_directive_types),
        "missing": list(expected_directive_types - found_directive_types),
        "coverage_rate": len(found_directive_types & expected_directive_types) / len(expected_directive_types)
    }
    
    return coverage_results


def evaluate_performance():
    """Evaluate analysis performance"""
    import subprocess
    
    performance_results = {
        "tests": []
    }
    
    # Test analyzer.py
    start_time = time.time()
    subprocess.run(["python", "tools/analyzer.py"], capture_output=True)
    analyzer_time = time.time() - start_time
    
    performance_results["tests"].append({
        "name": "analyzer.py",
        "duration_seconds": round(analyzer_time, 3),
        "status": "pass" if analyzer_time < 5 else "slow"
    })
    
    # Test pattern_extractor.py
    start_time = time.time()
    subprocess.run(["python", "tools/pattern_extractor.py"], capture_output=True)
    pattern_time = time.time() - start_time
    
    performance_results["tests"].append({
        "name": "pattern_extractor.py",
        "duration_seconds": round(pattern_time, 3),
        "status": "pass" if pattern_time < 5 else "slow"
    })
    
    # Calculate average
    total_time = analyzer_time + pattern_time
    performance_results["total_time_seconds"] = round(total_time, 3)
    performance_results["average_per_test"] = round(total_time / 2, 3)
    
    return performance_results


def evaluate_skill_types():
    """Evaluate parsing quality of different skill types"""
    parsed_dir = Path("parsed")
    
    # Categorize skills
    skill_categories = {
        "document_processing": ["anthropic-pdf-skill.json", "docx-skill.json", "xlsx-skill.json", "pptx-skill.json"],
        "development_tools": ["mcp-builder-skill.json", "webapp-testing-skill.json", "skill-creator-skill.json"],
        "creative": ["canvas-design-skill.json"],
        "utility": ["file-organizer-skill.json", "image-enhancer-skill.json", "internal-comms-skill.json"],
    }
    
    category_stats = {}
    
    for category, files in skill_categories.items():
        stats = {"skills": 0, "actions": 0, "rules": 0, "directives": 0}
        
        for filename in files:
            filepath = parsed_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    skill = json.load(f)
                
                decomp = skill.get("decomposition", {})
                stats["skills"] += 1
                stats["actions"] += len(decomp.get("actions", []))
                stats["rules"] += len(decomp.get("rules", []))
                stats["directives"] += len(decomp.get("directives", []))
        
        if stats["skills"] > 0:
            stats["avg_actions"] = round(stats["actions"] / stats["skills"], 1)
            stats["avg_rules"] = round(stats["rules"] / stats["skills"], 1)
            stats["avg_directives"] = round(stats["directives"] / stats["skills"], 1)
        
        category_stats[category] = stats
    
    return category_stats


def generate_report():
    """Generate complete evaluation report"""
    print("=" * 60)
    print("📊 Skill-0 Analyzer Coverage and Performance Evaluation Report")
    print("=" * 60)
    print(f"Evaluation time: {datetime.now().isoformat()}")
    print()
    
    # Coverage evaluation
    print("📈 Coverage Evaluation")
    print("-" * 40)
    coverage = evaluate_coverage()
    
    print(f"Skills analyzed: {coverage['total_skills']}")
    print()
    
    action_cov = coverage["action_type_coverage"]
    print(f"Action type coverage: {action_cov['coverage_rate']:.0%}")
    print(f"  Covered: {', '.join(action_cov['found'])}")
    if action_cov["missing"]:
        print(f"  Missing: {', '.join(action_cov['missing'])}")
    print()
    
    directive_cov = coverage["directive_type_coverage"]
    print(f"Directive type coverage: {directive_cov['coverage_rate']:.0%}")
    print(f"  Covered: {', '.join(directive_cov['found'])}")
    if directive_cov["missing"]:
        print(f"  Missing: {', '.join(directive_cov['missing'])}")
    print()
    
    # Category statistics
    print("📁 Statistics by Category")
    print("-" * 40)
    category_stats = evaluate_skill_types()
    
    for category, stats in category_stats.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        print(f"  Skills: {stats['skills']}")
        print(f"  Avg Actions: {stats.get('avg_actions', 0)}")
        print(f"  Avg Rules: {stats.get('avg_rules', 0)}")
        print(f"  Avg Directives: {stats.get('avg_directives', 0)}")
    print()
    
    # Performance evaluation
    print("⚡ Performance Evaluation")
    print("-" * 40)
    performance = evaluate_performance()
    
    for test in performance["tests"]:
        status_icon = "✓" if test["status"] == "pass" else "⚠️"
        print(f"  {status_icon} {test['name']}: {test['duration_seconds']}s")
    
    print(f"\nTotal execution time: {performance['total_time_seconds']}s")
    print(f"Average per tool: {performance['average_per_test']}s")
    print()
    
    # Conclusion
    print("📋 Evaluation Conclusion")
    print("-" * 40)
    
    overall_coverage = (action_cov['coverage_rate'] + directive_cov['coverage_rate']) / 2
    
    if overall_coverage >= 0.8:
        print("✅ Coverage is excellent (≥80%)")
    elif overall_coverage >= 0.6:
        print("⚠️ Coverage is acceptable (60-80%)")
    else:
        print("❌ Coverage is insufficient (<60%)")
    
    if performance['total_time_seconds'] < 2:
        print("✅ Performance is excellent (<2s)")
    elif performance['total_time_seconds'] < 5:
        print("⚠️ Performance is acceptable (2-5s)")
    else:
        print("❌ Performance needs optimization (>5s)")
    
    print()
    print("=" * 60)
    
    # Save report
    report = {
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "category_stats": category_stats,
        "performance": performance,
        "overall_coverage_rate": overall_coverage
    }
    
    output_path = Path("analysis/evaluation_report.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Report saved: {output_path}")


if __name__ == "__main__":
    generate_report()
