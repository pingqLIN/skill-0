#!/usr/bin/env python3
"""
Vector DB 同步腳本

功能：
1. 從 parsed/ 目錄載入所有技能 JSON
2. 重建 Vector DB 索引（冪等操作）
3. 交叉比對 Governance DB，產出同步報告

用法：
    python scripts/sync_vector_db.py
    python scripts/sync_vector_db.py --parsed-dir parsed --db-path skills.db
    python scripts/sync_vector_db.py --report-only  # 只產出報告不重建
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime

# 確保專案根目錄在 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))


def get_parsed_skill_names(parsed_dir: Path) -> dict:
    """取得 parsed 目錄中所有技能的名稱映射。

    Returns: {filename: skill_name_from_json}
    """
    mapping = {}
    for f in sorted(parsed_dir.glob("*-skill.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            name = data.get("meta", {}).get("name", f.stem)
            mapping[f.name] = name
        except (json.JSONDecodeError, KeyError):
            mapping[f.name] = f.stem
    return mapping


def get_governance_skills():
    """從 Governance DB 取得所有技能記錄。"""
    try:
        from governance_db import GovernanceDB
        db = GovernanceDB()
        # list_skills 支援 status/risk_level/limit 參數，不傳 status 則取全部
        return db.list_skills(limit=9999)
    except Exception as e:
        print(f"[WARN] 無法連接 Governance DB: {e}")
        return []


def sync_vector_db(parsed_dir: str, db_path: str, report_only: bool = False):
    """執行同步。"""
    parsed_path = PROJECT_ROOT / parsed_dir
    db_full_path = PROJECT_ROOT / db_path

    print(f"{'='*60}")
    print(f"Vector DB 同步工具")
    print(f"{'='*60}")
    print(f"Parsed 目錄: {parsed_path}")
    print(f"Vector DB:   {db_full_path}")
    print(f"模式:        {'報告' if report_only else '同步 + 報告'}")
    print()

    # 1. 掃描 parsed 目錄
    parsed_skills = get_parsed_skill_names(parsed_path)
    print(f"[1/4] Parsed 目錄: {len(parsed_skills)} 個技能 JSON")

    # 2. 取得 Governance DB 狀態
    gov_skills = get_governance_skills()
    gov_by_status = {}
    for s in gov_skills:
        status = s.status if hasattr(s, "status") else "unknown"
        gov_by_status.setdefault(status, []).append(s)

    print(f"[2/4] Governance DB: {len(gov_skills)} 筆記錄")
    for status, items in sorted(gov_by_status.items()):
        print(f"       - {status}: {len(items)}")

    # 3. 重建 Vector DB（除非 report_only）
    indexed_count = 0
    if not report_only:
        print(f"\n[3/4] 重建 Vector DB 索引...")
        try:
            from vector_db import SemanticSearch
            search = SemanticSearch(db_path=str(db_full_path))
            search.store.clear()
            indexed_count = search.index_skills(str(parsed_path), show_progress=True)
            search.close()
            print(f"       索引完成: {indexed_count} 個技能")
        except Exception as e:
            print(f"       [ERROR] 索引失敗: {e}")
            if "sentence_transformers" in str(e) or "No module" in str(e):
                print("       提示: 需要安裝 sentence-transformers 套件")
                print("       pip install sentence-transformers")
    else:
        print(f"\n[3/4] 跳過索引（報告模式）")
        # 報告模式下，讀取目前 Vector DB 中已有的數量
        try:
            from vector_db import VectorStore
            store = VectorStore(db_path=str(db_full_path))
            existing = store.get_all_skills()
            indexed_count = len(existing) if existing else 0
            print(f"       目前 Vector DB 已有: {indexed_count} 個技能")
        except Exception as e:
            print(f"       [WARN] 無法讀取 Vector DB: {e}")

    # 4. 產出同步報告
    print(f"\n[4/4] 同步報告")
    print(f"{'='*60}")

    # 交叉比對（以小寫名稱比對）
    gov_names = {(s.name if hasattr(s, "name") else "").lower() for s in gov_skills}
    parsed_names = {name.lower() for name in parsed_skills.values()}

    in_both = gov_names & parsed_names
    in_gov_only = gov_names - parsed_names - {""}
    in_parsed_only = parsed_names - gov_names - {""}

    report = {
        "sync_date": datetime.now().isoformat(),
        "parsed_count": len(parsed_skills),
        "governance_count": len(gov_skills),
        "indexed_count": indexed_count,
        "governance_by_status": {k: len(v) for k, v in sorted(gov_by_status.items())},
        "coverage": {
            "in_both": len(in_both),
            "governance_only": len(in_gov_only),
            "parsed_only": len(in_parsed_only),
        },
        "governance_only_skills": sorted(in_gov_only),
        "parsed_only_skills": sorted(in_parsed_only),
    }

    print(f"  Parsed 技能:       {len(parsed_skills)}")
    print(f"  Governance 技能:   {len(gov_skills)}")
    print(f"  Vector DB 索引:    {indexed_count}")
    print(f"  兩邊都有:          {len(in_both)}")
    print(f"  僅 Governance:     {len(in_gov_only)} (缺少 parsed JSON)")
    print(f"  僅 Parsed:         {len(in_parsed_only)} (未在 Governance 中)")

    if in_gov_only:
        print(f"\n  --- 僅在 Governance 中（無法索引）前 20 筆 ---")
        for name in sorted(in_gov_only)[:20]:
            print(f"    - {name}")
        if len(in_gov_only) > 20:
            print(f"    ... 還有 {len(in_gov_only) - 20} 個")

    if in_parsed_only:
        print(f"\n  --- 僅在 Parsed 中（未登錄 Governance） ---")
        for name in sorted(in_parsed_only)[:20]:
            print(f"    - {name}")
        if len(in_parsed_only) > 20:
            print(f"    ... 還有 {len(in_parsed_only) - 20} 個")

    # 寫入報告 JSON
    report_path = PROJECT_ROOT / "sync_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  報告已寫入: {report_path}")
    print(f"{'='*60}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Vector DB 同步工具")
    parser.add_argument("--parsed-dir", default="parsed", help="Parsed 技能目錄")
    parser.add_argument("--db-path", default="skills.db", help="Vector DB 路徑")
    parser.add_argument("--report-only", action="store_true", help="只產出報告")
    args = parser.parse_args()

    sync_vector_db(args.parsed_dir, args.db_path, args.report_only)


if __name__ == "__main__":
    main()
