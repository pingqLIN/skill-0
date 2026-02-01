#!/usr/bin/env python3
"""
Skill-0 分析器覆蓋率與效能評估
"""

import argparse
import json
import time
from pathlib import Path
from datetime import datetime


# 全域設定，可由 CLI 參數覆寫
CONFIG = {
    "parsed_dir": "parsed",
    "analysis_dir": "analysis",
    "tools_dir": "tools"
}


def evaluate_coverage():
    """評估框架覆蓋率"""
    parsed_dir = Path(CONFIG["parsed_dir"])
    skills = list(parsed_dir.glob("*.json"))
    
    coverage_results = {
        "total_skills": len(skills),
        "coverage_by_type": {},
        "uncovered_elements": [],
        "action_type_coverage": {},
        "directive_type_coverage": {},
    }
    
    # 定義預期的元素類型
    expected_action_types = {"io_read", "io_write", "transform", "external_call", "await_input"}
    expected_directive_types = {"completion", "knowledge", "principle", "constraint", "preference", "strategy"}
    
    found_action_types = set()
    found_directive_types = set()
    
    for skill_file in skills:
        with open(skill_file, 'r', encoding='utf-8') as f:
            skill = json.load(f)
        
        decomp = skill.get("decomposition", {})
        
        # 收集 action 類型
        for action in decomp.get("actions", []):
            found_action_types.add(action.get("action_type", "unknown"))
        
        # 收集 directive 類型
        for directive in decomp.get("directives", []):
            found_directive_types.add(directive.get("directive_type", "unknown"))
    
    # 計算覆蓋率
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
    """評估分析效能"""
    import subprocess
    
    performance_results = {
        "tests": []
    }
    
    tools_dir = CONFIG["tools_dir"]
    
    # 測試 analyzer.py
    start_time = time.time()
    subprocess.run(["python", f"{tools_dir}/analyzer.py"], capture_output=True)
    analyzer_time = time.time() - start_time
    
    performance_results["tests"].append({
        "name": "analyzer.py",
        "duration_seconds": round(analyzer_time, 3),
        "status": "pass" if analyzer_time < 5 else "slow"
    })
    
    # 測試 pattern_extractor.py
    start_time = time.time()
    subprocess.run(["python", f"{tools_dir}/pattern_extractor.py"], capture_output=True)
    pattern_time = time.time() - start_time
    
    performance_results["tests"].append({
        "name": "pattern_extractor.py",
        "duration_seconds": round(pattern_time, 3),
        "status": "pass" if pattern_time < 5 else "slow"
    })
    
    # 計算平均
    total_time = analyzer_time + pattern_time
    performance_results["total_time_seconds"] = round(total_time, 3)
    performance_results["average_per_test"] = round(total_time / 2, 3)
    
    return performance_results


def evaluate_skill_types():
    """評估不同類型 skill 的解析品質"""
    parsed_dir = Path(CONFIG["parsed_dir"])
    
    # 分類 skills
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
    """產生完整評估報告"""
    print("=" * 60)
    print("📊 Skill-0 分析器覆蓋率與效能評估報告")
    print("=" * 60)
    print(f"評估時間: {datetime.now().isoformat()}")
    print()
    
    # 覆蓋率評估
    print("📈 覆蓋率評估")
    print("-" * 40)
    coverage = evaluate_coverage()
    
    print(f"分析 Skills 數量: {coverage['total_skills']}")
    print()
    
    action_cov = coverage["action_type_coverage"]
    print(f"Action 類型覆蓋率: {action_cov['coverage_rate']:.0%}")
    print(f"  已涵蓋: {', '.join(action_cov['found'])}")
    if action_cov["missing"]:
        print(f"  未涵蓋: {', '.join(action_cov['missing'])}")
    print()
    
    directive_cov = coverage["directive_type_coverage"]
    print(f"Directive 類型覆蓋率: {directive_cov['coverage_rate']:.0%}")
    print(f"  已涵蓋: {', '.join(directive_cov['found'])}")
    if directive_cov["missing"]:
        print(f"  未涵蓋: {', '.join(directive_cov['missing'])}")
    print()
    
    # 分類統計
    print("📁 按類別統計")
    print("-" * 40)
    category_stats = evaluate_skill_types()
    
    for category, stats in category_stats.items():
        print(f"\n{category.replace('_', ' ').title()}:")
        print(f"  Skills: {stats['skills']}")
        print(f"  平均 Actions: {stats.get('avg_actions', 0)}")
        print(f"  平均 Rules: {stats.get('avg_rules', 0)}")
        print(f"  平均 Directives: {stats.get('avg_directives', 0)}")
    print()
    
    # 效能評估
    print("⚡ 效能評估")
    print("-" * 40)
    performance = evaluate_performance()
    
    for test in performance["tests"]:
        status_icon = "✓" if test["status"] == "pass" else "⚠️"
        print(f"  {status_icon} {test['name']}: {test['duration_seconds']}s")
    
    print(f"\n總執行時間: {performance['total_time_seconds']}s")
    print(f"平均每個工具: {performance['average_per_test']}s")
    print()
    
    # 結論
    print("📋 評估結論")
    print("-" * 40)
    
    overall_coverage = (action_cov['coverage_rate'] + directive_cov['coverage_rate']) / 2
    
    if overall_coverage >= 0.8:
        print("✅ 覆蓋率優良 (≥80%)")
    elif overall_coverage >= 0.6:
        print("⚠️ 覆蓋率尚可 (60-80%)")
    else:
        print("❌ 覆蓋率不足 (<60%)")
    
    if performance['total_time_seconds'] < 2:
        print("✅ 效能優良 (<2s)")
    elif performance['total_time_seconds'] < 5:
        print("⚠️ 效能尚可 (2-5s)")
    else:
        print("❌ 效能需優化 (>5s)")
    
    print()
    print("=" * 60)
    
    # 儲存報告
    report = {
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "category_stats": category_stats,
        "performance": performance,
        "overall_coverage_rate": overall_coverage
    }
    
    output_path = Path(CONFIG["analysis_dir"]) / "evaluation_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"📄 報告已儲存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Skill-0 覆蓋率與效能評估工具")
    parser.add_argument("--parsed-dir", "-p", default="parsed",
                        help="已解析 skills 的目錄 (預設: parsed)")
    parser.add_argument("--analysis-dir", "-a", default="analysis",
                        help="分析報告輸出目錄 (預設: analysis)")
    parser.add_argument("--tools-dir", "-t", default="tools",
                        help="工具目錄 (預設: tools)")
    args = parser.parse_args()
    
    # 更新全域設定
    CONFIG["parsed_dir"] = args.parsed_dir
    CONFIG["analysis_dir"] = args.analysis_dir
    CONFIG["tools_dir"] = args.tools_dir
    
    generate_report()


if __name__ == "__main__":
    main()
