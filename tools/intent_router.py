#!/usr/bin/env python3
"""
Goal-first intent router for Skill-0 workflows.

This CLI does not execute repo operations directly. It maps an explicit goal,
task phase, and optional freeform request into the next recommended Skill-0
workflow plus concrete commands the operator can run.

The current version is intentionally lightweight: a table-driven operator
starter that makes Skill-0's existing paths easier to discover and sequence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


GOALS = (
    "discover",
    "ingest",
    "analyze",
    "govern",
    "compare",
    "validate",
)

PHASES = (
    "intake",
    "triage",
    "execution",
    "review",
)

GOAL_KEYWORDS: Dict[str, tuple[str, ...]] = {
    "discover": (
        "discover",
        "search",
        "find",
        "inventory",
        "dedup",
        "semantic",
        "lookup",
        "搜尋",
        "查找",
        "發現",
        "盤點",
    ),
    "ingest": (
        "import",
        "ingest",
        "parse",
        "convert",
        "normalize",
        "adopt",
        "匯入",
        "解析",
        "轉換",
        "正規化",
    ),
    "analyze": (
        "analyze",
        "analysis",
        "pattern",
        "cluster",
        "coverage",
        "分析",
        "模式",
        "聚類",
        "覆蓋",
    ),
    "govern": (
        "govern",
        "governance",
        "review",
        "approve",
        "reject",
        "audit",
        "risk",
        "治理",
        "審核",
        "核准",
        "拒絕",
        "稽核",
        "風險",
    ),
    "compare": (
        "compare",
        "comparison",
        "similar",
        "overlap",
        "diff",
        "比較",
        "相似",
        "重疊",
        "差異",
    ),
    "validate": (
        "validate",
        "verification",
        "verify",
        "test",
        "schema",
        "contract",
        "驗證",
        "測試",
        "規格",
        "契約",
    ),
}


@dataclass
class RouteDecision:
    goal: str
    phase: str
    summary: str
    rationale: List[str]
    primary_capability: str
    recommended_commands: List[str]
    secondary_capabilities: List[str]
    follow_up_questions: List[str]


def infer_goal(request_text: str) -> str:
    lowered = request_text.lower()
    scores = {goal: 0 for goal in GOALS}
    for goal, keywords in GOAL_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in lowered:
                scores[goal] += 1

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_goal, best_score = ranked[0]
    return best_goal if best_score > 0 else "discover"


def default_phase_for_goal(goal: str) -> str:
    if goal in {"discover", "compare"}:
        return "triage"
    if goal in {"govern", "validate"}:
        return "review"
    return "execution"


def build_commands(
    goal: str,
    phase: str,
    query: Optional[str],
    skill_name: Optional[str],
    source_path: Optional[str],
) -> List[str]:
    query_text = query or "document processing"
    skill_text = skill_name
    path_text = source_path or "<source-dir-or-skill>"

    if goal == "discover":
        commands = []
        if phase == "intake":
            commands.extend(
                [
                    ".venv/bin/python -m vector_db.search --db skills.db --parsed-dir parsed index",
                    ".venv/bin/python -m vector_db.search --db skills.db stats",
                ]
            )
        commands.append(
            f'.venv/bin/python -m vector_db.search --db skills.db search "{query_text}"',
        )
        if phase != "intake":
            commands.append(".venv/bin/python -m vector_db.search --db skills.db stats")
        if skill_text:
            commands.append(
                f'.venv/bin/python -m vector_db.search --db skills.db similar "{skill_text}"'
            )
        return commands
    if goal == "ingest":
        commands = [
            f".venv/bin/python tools/batch_parse.py -i {path_text} -o parsed --validate",
            ".venv/bin/python tools/validate_skill_schema.py parsed",
        ]
        if phase in {"execution", "review"}:
            commands.append(".venv/bin/python tools/batch_import.py --skip-security")
        return commands
    if goal == "analyze":
        commands = [
            ".venv/bin/python tools/analyzer.py -p parsed -o analysis/report.json -t",
            ".venv/bin/python tools/pattern_extractor.py -o analysis/patterns.json",
        ]
        if phase in {"execution", "review"}:
            commands.append(".venv/bin/python tools/evaluate.py -p parsed -o analysis/evaluation.json")
        return commands
    if goal == "govern":
        commands = []
        if phase == "intake":
            commands.append(".venv/bin/python tools/skill_governance.py list")
        else:
            commands.extend(
                [
            ".venv/bin/python tools/batch_security_scan.py",
            ".venv/bin/python tools/skill_governance.py list",
            ".venv/bin/python tools/skill_governance.py review list",
                ]
            )
        return commands
    if goal == "compare":
        commands = []
        if phase == "intake":
            commands.append(".venv/bin/python -m vector_db.search --db skills.db --parsed-dir parsed index")
        commands.extend(
            [
            f'.venv/bin/python -m vector_db.search --db skills.db search "{query_text}"',
            ".venv/bin/python tools/pattern_extractor.py -o analysis/patterns.json",
            ]
        )
        if skill_text:
            commands.insert(
                1,
                f'.venv/bin/python -m vector_db.search --db skills.db similar "{skill_text}"',
            )
        return commands
    commands = [
        ".venv/bin/python tools/validate_skill_schema.py parsed",
    ]
    if phase in {"execution", "review"}:
        commands.extend(
            [
                ".venv/bin/python -m pytest tests/test_schema_contract.py tests/test_governance_revisions.py -q",
                ".venv/bin/python tools/evaluate.py -p parsed",
            ]
        )
    return commands


def build_route(
    goal: str,
    phase: str,
    query: Optional[str] = None,
    skill_name: Optional[str] = None,
    source_path: Optional[str] = None,
) -> RouteDecision:
    summaries = {
        "discover": "Use goal-first discovery routing to gather existing skill evidence before editing or importing anything.",
        "ingest": "Use parse/import routing when the task is to bring external skill material into the Skill-0 sidecar data layer.",
        "analyze": "Use analysis routing when the task is to extract patterns, coverage signals, or structural findings from the parsed corpus.",
        "govern": "Use governance routing when the next decision depends on risk, approval state, auditability, or reviewer workflow.",
        "compare": "Use comparison routing when the task is to evaluate overlap, similarity, or adoption boundaries between skill sets.",
        "validate": "Use validation routing when the task is to prove schema, contract, or governance baseline health.",
    }
    primary_capabilities = {
        "discover": "semantic-search",
        "ingest": "parse-and-import",
        "analyze": "pattern-analysis",
        "govern": "governance-review",
        "compare": "similarity-and-overlap-analysis",
        "validate": "schema-and-regression-validation",
    }
    secondary = {
        "discover": ["comparison", "governance"],
        "ingest": ["validation", "governance"],
        "analyze": ["comparison", "validation"],
        "govern": ["security-scan", "audit-log"],
        "compare": ["semantic-search", "pattern-analysis"],
        "validate": ["evaluation", "governance"],
    }
    rationale = {
        "discover": [
            "Goal-first routing starts from the operator objective, not from whichever tool seems available first.",
            "Search and discovery act as evidence-gathering layers for later decisions, and intake phase can front-load indexing when needed.",
        ],
        "ingest": [
            "When the operator intent is adoption, parsing and schema normalization should precede search or approval.",
            "Phase hints keep intake steps distinct from later registration or review work.",
        ],
        "analyze": [
            "Pattern extraction is useful after the corpus exists and before new governance policy is imposed.",
            "This route optimizes for comparative evidence rather than immediate mutation, while review phase can append evaluation checks.",
        ],
        "govern": [
            "Governance is a decision workflow around approval, risk, and auditability.",
            "Discovery signals can feed governance, but should not replace the review path or audit trail.",
        ],
        "compare": [
            "Comparison starts from the question being asked, then uses search and pattern tools as supporting evidence.",
            "This avoids treating raw skill lists as the primary control surface, while intake phase can bootstrap indexing first.",
        ],
        "validate": [
            "Validation should prove baseline health with schema and regression checks before broader rollout.",
            "This route is appropriate when trust and contract integrity are the next gating concern.",
        ],
    }
    follow_up = {
        "discover": [
            "What capability or domain are you trying to locate?",
            "Do you want inventory-level search, similar-skill lookup, or deduplication evidence?",
        ],
        "ingest": [
            "What is the source corpus path?",
            "Should the new material stop at parsed sidecars, or continue into governance registration?",
        ],
        "analyze": [
            "Are you looking for pattern reuse, overlap, or quality gaps?",
            "Should the output be a report only or feed a governance decision later?",
        ],
        "govern": [
            "Is the next action scan, review, approval, or audit lookup?",
            "Do you need reviewer-facing evidence or only operator-side status?",
        ],
        "compare": [
            "Which skill set or repo is the baseline for comparison?",
            "Do you need semantic similarity, structural overlap, or adoption-boundary analysis?",
        ],
        "validate": [
            "Are you validating schema, parser behavior, or governance semantics?",
            "Should this stay as a smoke check or expand into focused regression coverage?",
        ],
    }

    return RouteDecision(
        goal=goal,
        phase=phase,
        summary=summaries[goal],
        rationale=rationale[goal],
        primary_capability=primary_capabilities[goal],
        recommended_commands=build_commands(goal, phase, query, skill_name, source_path),
        secondary_capabilities=secondary[goal],
        follow_up_questions=follow_up[goal],
    )


def render_text(decision: RouteDecision) -> str:
    lines = [
        "Skill-0 Intent Router",
        "=====================",
        f"Goal: {decision.goal}",
        f"Phase: {decision.phase}",
        f"Primary capability: {decision.primary_capability}",
        "",
        f"Summary: {decision.summary}",
        "",
        "Rationale:",
    ]
    lines.extend(f"- {item}" for item in decision.rationale)
    lines.extend(
        [
            "",
            "Recommended commands:",
        ]
    )
    lines.extend(f"- {item}" for item in decision.recommended_commands)
    lines.extend(
        [
            "",
            "Secondary capabilities:",
        ]
    )
    lines.extend(f"- {item}" for item in decision.secondary_capabilities)
    lines.extend(
        [
            "",
            "Follow-up questions:",
        ]
    )
    lines.extend(f"- {item}" for item in decision.follow_up_questions)
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route Skill-0 work from top-level intent to the next recommended workflow."
    )
    parser.add_argument(
        "request",
        nargs="?",
        default="",
        help="Optional freeform request text used to infer a goal when --goal is not supplied.",
    )
    parser.add_argument("--goal", choices=GOALS, help="Explicit top-level goal.")
    parser.add_argument("--phase", choices=PHASES, help="Explicit task phase.")
    parser.add_argument("--query", help="Search or comparison query to embed in recommendations.")
    parser.add_argument("--skill-name", help="Specific skill name for similarity or governance flows.")
    parser.add_argument("--source-path", help="Source path used by ingest recommendations.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    goal = args.goal or infer_goal(args.request)
    phase = args.phase or default_phase_for_goal(goal)
    decision = build_route(
        goal=goal,
        phase=phase,
        query=args.query,
        skill_name=args.skill_name,
        source_path=args.source_path,
    )

    if args.format == "json":
        print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
    else:
        print(render_text(decision))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
