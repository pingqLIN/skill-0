#!/usr/bin/env python3
"""
自動化批量解析 SKILL.md → Skill-0 JSON

從 converted-skills/ 讀取 SKILL.md，用啟發式規則提取
actions/rules/directives，輸出到 parsed/ 目錄。

用法:
    python scripts/auto_parse.py
    python scripts/auto_parse.py --dry-run
    python scripts/auto_parse.py --limit 10
    python scripts/auto_parse.py --skills yolo-unattended
    python scripts/auto_parse.py --skills yolo-unattended --validate
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
sys.path.insert(0, str(PROJECT_ROOT))

from tools.schema_contract import DEFAULT_SCHEMA_PATH, iter_validation_errors, normalize_skill_document

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

COMMAND_STARTERS = (
    "npm",
    "npx",
    "pip",
    "python",
    "python3",
    "bash",
    "sh",
    "node",
    "git",
    "docker",
    "curl",
    "cargo",
    "go",
    "dotnet",
    "mvn",
    "gradle",
    "uv",
    "pytest",
    "pnpm",
    "yarn",
    "cd",
    "rg",
    "wget",
)

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
    in_code = False

    for line in body.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
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
            if len(item) > 10 and not is_command_line(item):  # 忽略太短的
                current["items"].append(item)
        elif line.strip() and not line.strip().startswith("```"):
            # 非空行、非代碼塊 → 可能是段落
            if len(line.strip()) > 30 and not is_command_line(line.strip()):
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
            if is_command_line(stripped):
                commands.append(stripped)
    return commands[:5]  # 最多 5 個


def is_command_line(text: str) -> bool:
    """Heuristically detect shell commands inside fenced code blocks."""
    stripped = text.strip()
    if not stripped:
        return False

    first_token = stripped.split()[0]
    normalized = first_token.lower()
    normalized = normalized.rstrip(":")
    basename = Path(normalized).name

    if normalized in COMMAND_STARTERS or basename in COMMAND_STARTERS:
        return True
    if basename in {"python", "python3", "bash", "sh", "node", "pytest"}:
        return True
    if first_token.startswith(("./", "../")) and Path(first_token).suffix in {".py", ".sh"}:
        return True
    return False


# --------------- 主解析邏輯 ---------------

def parse_skill_md(skill_name: str, content: str) -> dict:
    """將一個 SKILL.md 解析為 Skill-0 JSON。"""
    meta, body = parse_frontmatter(content)
    name = meta.get("name", skill_name)
    full_description = meta.get("description", "")
    meta_description = full_description[:200]

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
            "action_type": "external_call",
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

    skill = {
        "$schema": "../schema/skill-decomposition.schema.json",
        "meta": {
            "skill_id": f"claude__skill__{name}",
            "name": name,
            "skill_layer": "claude_skill",
            "title": f"{name.replace('-', ' ').title()} Skill",
            "description": meta_description or f"Skill for {name}",
            "schema_version": "2.4.0",
            "parse_timestamp": now,
            "parser_version": "skill-0 v2.4-auto",
            "parsed_by": "auto_parse.py",
        },
        "original_definition": {
            "source": f"converted-skills/{skill_name}/SKILL.md",
            "skill_name": name,
            "skill_description": full_description,
        },
        "decomposition": {
            "actions": actions,
            "rules": rules,
            "directives": directives,
        },
    }

    return normalize_skill_document(skill)


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

def resolve_skill_dirs(
    converted_dir: Path,
    skill_names: list[str] | None = None,
) -> list[Path]:
    """Resolve requested skill directories in a stable order."""
    available = {path.name: path for path in sorted(converted_dir.iterdir()) if path.is_dir()}
    if not skill_names:
        return list(available.values())

    resolved = []
    seen = set()
    for skill_name in skill_names:
        if skill_name in seen:
            continue
        skill_dir = available.get(skill_name)
        if skill_dir is None:
            raise FileNotFoundError(f"找不到 skill 目錄: {converted_dir / skill_name}")
        resolved.append(skill_dir)
        seen.add(skill_name)
    return resolved


def run_auto_parse(
    *,
    converted_dir: Path = CONVERTED_DIR,
    parsed_dir: Path = PARSED_DIR,
    dry_run: bool = False,
    limit: int = 0,
    force: bool = False,
    skill_names: list[str] | None = None,
    validate: bool = False,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    max_errors_per_file: int = 20,
) -> int:
    """Run the auto parser and return a shell-style exit code."""
    if not converted_dir.exists():
        print(f"[ERROR] 找不到 {converted_dir}")
        return 1

    parsed_dir.mkdir(exist_ok=True)

    # 已存在的 parsed JSON
    existing = {f.stem.replace("-skill", "") for f in parsed_dir.glob("*-skill.json")}

    try:
        dirs = resolve_skill_dirs(converted_dir, skill_names)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 1

    total = len(dirs)
    skipped = 0
    parsed = 0
    errors = 0
    validated = 0
    stats = {"actions": 0, "rules": 0, "directives": 0}

    print(f"{'=' * 60}")
    print(f"Skill-0 自動解析器 v2.4")
    print(f"{'=' * 60}")
    print(f"來源: {converted_dir} ({total} 個技能)")
    print(f"輸出: {parsed_dir}")
    print(f"模式: {'Dry Run' if dry_run else '寫入'}")
    if validate:
        print(f"驗證: 啟用 ({schema_path})")
    if skill_names:
        print(f"篩選: {', '.join(skill_names)}")
    print()

    for skill_dir in dirs:
        if limit and parsed >= limit:
            break

        skill_name = skill_dir.name
        output_file = parsed_dir / f"{skill_name}-skill.json"

        # 跳過已存在
        if not force and skill_name in existing:
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

            if validate:
                validation_errors = []
                for error in iter_validation_errors(result, schema_path):
                    location = ".".join(str(part) for part in error.absolute_path) or "<root>"
                    validation_errors.append(f"{location}: {error.message}")
                    if len(validation_errors) >= max_errors_per_file:
                        break

                if validation_errors:
                    errors += 1
                    print(f"  [FAIL] {skill_name}: schema validation failed")
                    for message in validation_errors:
                        print(f"         - {message}")
                    continue

                validated += 1

            if not dry_run:
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
    if validate:
        print(f"  已驗證:   {validated}")
    print(f"  Actions:  {stats['actions']}")
    print(f"  Rules:    {stats['rules']}")
    print(f"  Directives: {stats['directives']}")
    print(f"{'=' * 60}")
    return 0 if errors == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="自動化批量解析 SKILL.md")
    parser.add_argument("--dry-run", action="store_true", help="只統計不寫入")
    parser.add_argument("--limit", type=int, default=0, help="限制處理數量（0=全部）")
    parser.add_argument("--force", action="store_true", help="覆蓋已存在的 parsed JSON")
    parser.add_argument(
        "--skills",
        nargs="+",
        help="只解析指定的 skill 名稱，例如 --skills yolo-unattended",
    )
    parser.add_argument("--validate", action="store_true", help="寫入前先用 schema 驗證輸出")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH, help="Schema JSON 路徑")
    parser.add_argument(
        "--max-errors-per-file",
        type=int,
        default=20,
        help="每個 skill 最多列出的 schema 錯誤數",
    )
    args = parser.parse_args()

    return run_auto_parse(
        dry_run=args.dry_run,
        limit=args.limit,
        force=args.force,
        skill_names=args.skills,
        validate=args.validate,
        schema_path=args.schema,
        max_errors_per_file=args.max_errors_per_file,
    )


if __name__ == "__main__":
    raise SystemExit(main())
