#!/usr/bin/env python3
"""
自動化批量解析 SKILL.md → Skill-0 JSON

從 converted-skills/ 讀取 SKILL.md，用啟發式規則提取
actions/rules/directives，輸出到 parsed/ 目錄。

用法:
    python scripts/auto_parse.py
    python scripts/auto_parse.py --dry-run
    python scripts/auto_parse.py --limit 10
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CONVERTED_DIR = PROJECT_ROOT / "converted-skills"
PARSED_DIR = PROJECT_ROOT / "parsed"

# --------------- Frontmatter 解析 ---------------

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 YAML frontmatter，回傳 (metadata_dict, body)。"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not m:
        return {}, content
    fm_text = m.group(1)
    body = content[m.end():]
    meta = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key:
                meta[key] = val
    return meta, body


# --------------- 關鍵字集合 ---------------

ACTION_VERBS = {
    "create", "read", "write", "generate", "build", "deploy", "install",
    "run", "execute", "parse", "convert", "extract", "transform", "send",
    "fetch", "load", "save", "import", "export", "compile", "test",
    "validate", "format", "render", "process", "upload", "download",
    "delete", "update", "merge", "clone", "push", "pull", "configure",
    "setup", "initialize", "start", "stop", "monitor", "scan", "analyze",
    "optimize", "migrate", "implement", "define", "register", "publish",
    "subscribe", "connect", "disconnect", "authenticate", "authorize",
    "encrypt", "decrypt", "hash", "sign", "verify", "package", "bundle",
}

RULE_KEYWORDS = {
    "must", "should", "avoid", "never", "always", "check", "verify",
    "ensure", "validate", "require", "prohibit", "restrict", "limit",
    "enforce", "mandatory", "forbidden", "do not", "don't",
}

DIRECTIVE_HEADING_KEYWORDS = {
    "best practice", "principle", "guideline", "strategy", "overview",
    "context", "philosophy", "standard", "convention", "pattern",
    "architecture", "design", "approach", "methodology", "recommendation",
}

ACTION_TYPE_MAP = [
    ({"read", "load", "fetch", "import", "parse", "extract", "get", "scan", "analyze", "monitor"}, "io_read"),
    ({"write", "save", "export", "create", "generate", "output", "publish", "upload", "send", "push"}, "io_write"),
    ({"transform", "convert", "format", "process", "modify", "merge", "optimize", "migrate", "refactor"}, "transform"),
    ({"calculate", "compute", "analyze", "evaluate", "compare", "hash", "encrypt", "decrypt"}, "compute"),
    ({"api", "call", "request", "connect", "subscribe", "authenticate", "authorize"}, "external_call"),
    ({"install", "deploy", "configure", "setup", "initialize", "start", "stop", "update", "delete", "register", "package", "bundle"}, "state_change"),
    ({"llm", "ai", "infer", "prompt", "chat"}, "llm_inference"),
    ({"input", "prompt", "ask", "wait", "await"}, "await_input"),
]

DIRECTIVE_TYPE_MAP = [
    ({"complete", "done", "finish", "success", "result", "output", "deliver"}, "completion"),
    ({"know", "domain", "reference", "specification", "standard", "documentation", "resource"}, "knowledge"),
    ({"principle", "philosophy", "approach", "clean", "solid", "dry", "kiss", "yagni"}, "principle"),
    ({"constraint", "limit", "restrict", "maximum", "minimum", "boundary", "threshold"}, "constraint"),
    ({"prefer", "recommend", "favor", "default", "convention", "style"}, "preference"),
    ({"strategy", "pattern", "method", "technique", "algorithm", "workflow", "process"}, "strategy"),
]


# --------------- 分類函式 ---------------

def classify_action_type(text: str) -> str:
    text_lower = text.lower()
    for keywords, atype in ACTION_TYPE_MAP:
        if any(kw in text_lower for kw in keywords):
            return atype
    return "transform"


def classify_directive_type(text: str) -> str:
    text_lower = text.lower()
    for keywords, dtype in DIRECTIVE_TYPE_MAP:
        if any(kw in text_lower for kw in keywords):
            return dtype
    return "knowledge"


def is_rule_sentence(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in RULE_KEYWORDS)


def is_action_sentence(text: str) -> bool:
    text_lower = text.lower()
    words = text_lower.split()
    if not words:
        return False
    first_word = re.sub(r"[^a-z]", "", words[0])
    return first_word in ACTION_VERBS or any(v in text_lower for v in ACTION_VERBS)


# --------------- Markdown 解析 ---------------

def extract_sections(body: str) -> list[dict]:
    """將 Markdown 分割成 sections，每個含 heading + items。"""
    sections = []
    current = {"heading": "", "level": 0, "items": []}

    for line in body.split("\n"):
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading_match:
            if current["heading"] or current["items"]:
                sections.append(current)
            current = {
                "heading": heading_match.group(2).strip(),
                "level": len(heading_match.group(1)),
                "items": [],
            }
        elif line.strip().startswith(("- ", "* ", "• ")):
            item = re.sub(r"^[-*•]\s+", "", line.strip())
            if len(item) > 10:  # 忽略太短的
                current["items"].append(item)
        elif line.strip() and not line.strip().startswith("```"):
            # 非空行、非代碼塊 → 可能是段落
            if len(line.strip()) > 30:
                current["items"].append(line.strip())

    if current["heading"] or current["items"]:
        sections.append(current)

    return sections


def extract_code_commands(body: str) -> list[str]:
    """從代碼區塊提取命令。"""
    commands = []
    in_code = False
    for line in body.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code and line.strip():
            stripped = line.strip()
            # 只提取看起來像命令的行
            if any(stripped.startswith(cmd) for cmd in
                   ["npm ", "npx ", "pip ", "python ", "git ", "docker ",
                    "curl ", "cargo ", "go ", "dotnet ", "mvn ", "gradle "]):
                commands.append(stripped)
    return commands[:5]  # 最多 5 個


# --------------- 主解析邏輯 ---------------

def parse_skill_md(skill_name: str, content: str) -> dict:
    """將一個 SKILL.md 解析為 Skill-0 JSON。"""
    meta, body = parse_frontmatter(content)
    name = meta.get("name", skill_name)
    description = meta.get("description", "")[:200]

    sections = extract_sections(body)
    code_cmds = extract_code_commands(body)

    actions = []
    rules = []
    directives = []

    # 從代碼命令提取 actions
    for cmd in code_cmds:
        verb = cmd.split()[0] if cmd.split() else "run"
        actions.append({
            "name": f"Run {verb}",
            "description": cmd[:100],
            "action_type": classify_action_type(cmd),
        })

    # 從 sections 提取
    for section in sections:
        heading_lower = section["heading"].lower()

        # 判斷 section 類型
        is_directive_section = any(kw in heading_lower for kw in DIRECTIVE_HEADING_KEYWORDS)

        for item in section["items"]:
            # 移除 emoji 和 markdown 標記
            clean = re.sub(r"[❌✅🔴🟡🟢⚠️💡🎯📌]+", "", item).strip()
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", clean)
            if len(clean) < 15:
                continue

            if is_rule_sentence(clean) and not is_directive_section:
                rules.append({
                    "description": clean[:150],
                    "condition": heading_lower[:80] if section["heading"] else "general",
                    "output": "proceed_or_halt",
                })
            elif is_action_sentence(clean) and not is_directive_section:
                actions.append({
                    "name": clean[:60],
                    "description": clean[:150],
                    "action_type": classify_action_type(clean),
                })
            elif is_directive_section or len(clean) > 50:
                directives.append({
                    "directive_type": classify_directive_type(clean),
                    "description": clean[:150],
                    "decomposable": False,
                })

    # 去重 + 限制數量
    actions = _deduplicate(actions, "name")[:15]
    rules = _deduplicate(rules, "description")[:10]
    directives = _deduplicate(directives, "description")[:10]

    # 加上 ID
    for i, a in enumerate(actions, 1):
        a["id"] = f"a_{i:03d}"
        a.setdefault("deterministic", True)
        a.setdefault("side_effects", [])

    for i, r in enumerate(rules, 1):
        r["id"] = f"r_{i:03d}"

    for i, d in enumerate(directives, 1):
        d["id"] = f"d_{i:03d}"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    return {
        "$schema": "../schema/skill-decomposition.schema.json",
        "meta": {
            "skill_id": f"claude__{name}",
            "name": name,
            "skill_layer": "claude_skill",
            "title": f"{name.replace('-', ' ').title()} Skill",
            "description": description or f"Skill for {name}",
            "schema_version": "2.4.0",
            "parse_timestamp": now,
            "parser_version": "skill-0 v2.4-auto",
            "parsed_by": "auto_parse.py",
        },
        "original_definition": {
            "source": f"converted-skills/{skill_name}/SKILL.md",
            "skill_name": name,
            "skill_description": description,
        },
        "decomposition": {
            "actions": actions,
            "rules": rules,
            "directives": directives,
        },
    }


def _deduplicate(items: list[dict], key: str) -> list[dict]:
    """按 key 值去重。"""
    seen = set()
    result = []
    for item in items:
        val = item.get(key, "")[:50].lower()
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


# --------------- 批量處理 ---------------

def main():
    parser = argparse.ArgumentParser(description="自動化批量解析 SKILL.md")
    parser.add_argument("--dry-run", action="store_true", help="只統計不寫入")
    parser.add_argument("--limit", type=int, default=0, help="限制處理數量（0=全部）")
    parser.add_argument("--force", action="store_true", help="覆蓋已存在的 parsed JSON")
    args = parser.parse_args()

    if not CONVERTED_DIR.exists():
        print(f"[ERROR] 找不到 {CONVERTED_DIR}")
        sys.exit(1)

    PARSED_DIR.mkdir(exist_ok=True)

    # 已存在的 parsed JSON
    existing = {f.stem.replace("-skill", "") for f in PARSED_DIR.glob("*-skill.json")}

    # 掃描 converted-skills
    dirs = sorted(d for d in CONVERTED_DIR.iterdir() if d.is_dir())
    total = len(dirs)
    skipped = 0
    parsed = 0
    errors = 0
    stats = {"actions": 0, "rules": 0, "directives": 0}

    print(f"{'=' * 60}")
    print(f"Skill-0 自動解析器 v2.4")
    print(f"{'=' * 60}")
    print(f"來源: {CONVERTED_DIR} ({total} 個技能)")
    print(f"輸出: {PARSED_DIR}")
    print(f"模式: {'Dry Run' if args.dry_run else '寫入'}")
    print()

    for i, skill_dir in enumerate(dirs):
        if args.limit and parsed >= args.limit:
            break

        skill_name = skill_dir.name
        output_file = PARSED_DIR / f"{skill_name}-skill.json"

        # 跳過已存在
        if not args.force and skill_name in existing:
            skipped += 1
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        try:
            content = skill_md.read_text(encoding="utf-8")
            result = parse_skill_md(skill_name, content)

            a = len(result["decomposition"]["actions"])
            r = len(result["decomposition"]["rules"])
            d = len(result["decomposition"]["directives"])
            stats["actions"] += a
            stats["rules"] += r
            stats["directives"] += d

            if not args.dry_run:
                output_file.write_text(
                    json.dumps(result, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            parsed += 1
            print(f"  [{parsed:3d}] {skill_name:<45} A:{a:2d} R:{r:2d} D:{d:2d}")

        except Exception as e:
            errors += 1
            print(f"  [ERR] {skill_name}: {e}")

    print()
    print(f"{'=' * 60}")
    print(f"統計摘要")
    print(f"{'=' * 60}")
    print(f"  總目錄:   {total}")
    print(f"  已跳過:   {skipped} (已存在)")
    print(f"  新解析:   {parsed}")
    print(f"  錯誤:     {errors}")
    print(f"  Actions:  {stats['actions']}")
    print(f"  Rules:    {stats['rules']}")
    print(f"  Directives: {stats['directives']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
