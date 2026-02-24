#!/usr/bin/env python3
"""
Skill-0 TUI Dashboard (Feature 8 — inspired by Hive's Terminal UI)

A Rich-based terminal dashboard for browsing parsed skills and governance status.
Supports headless/CI environments without requiring a browser.

Usage:
    python tools/skill_tui.py                    # Full dashboard
    python tools/skill_tui.py --parsed-only      # Parsed skills only
    python tools/skill_tui.py --skill pdf        # Detail view for a skill
    python tools/skill_tui.py --quality          # Quality signals report
    python tools/skill_tui.py --json             # JSON output (CI-friendly)

Author: skill-0 project
Created: 2026-02-24
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Project root relative to this file
REPO_ROOT = Path(__file__).parent.parent
PARSED_DIR = REPO_ROOT / "parsed"
SCHEMA_FILE = REPO_ROOT / "schema" / "skill-decomposition.schema.json"

console = Console() if RICH_AVAILABLE else None


def _quality_bar(score, width=10):
    """Return a visual bar for a 0-1 score."""
    if score is None:
        return "[dim]N/A[/dim]"
    filled = int(round(score * width))
    bar = "█" * filled + "░" * (width - filled)
    if score >= 0.8:
        color = "green"
    elif score >= 0.5:
        color = "yellow"
    else:
        color = "red"
    return f"[{color}]{bar}[/{color}] {score:.0%}"


def _status_icon(status):
    """Return colored status icon."""
    return {
        "pending": "[yellow]⏳[/yellow]",
        "approved": "[green]✅[/green]",
        "rejected": "[red]❌[/red]",
        "blocked": "[red]🚫[/red]",
    }.get(status or "pending", "[dim]?[/dim]")


def _quality_icon(overall):
    """Return colored quality icon."""
    return {
        "high": "[green]●[/green]",
        "medium": "[yellow]●[/yellow]",
        "low": "[red]●[/red]",
    }.get(overall or "", "[dim]○[/dim]")


def load_parsed_skills(parsed_dir=None):
    """Load all parsed skill JSON files from the parsed/ directory."""
    search_dir = parsed_dir or PARSED_DIR
    skills = []
    if not search_dir.exists():
        return skills
    for path in sorted(search_dir.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                skill = json.load(f)
            skill["_filename"] = path.name
            skill["_path"] = str(path)
            skills.append(skill)
        except (json.JSONDecodeError, OSError):
            pass
    return skills


def load_schema_version():
    """Load schema version string."""
    try:
        with open(SCHEMA_FILE, encoding="utf-8") as f:
            schema = json.load(f)
        return schema.get("version", "unknown")
    except (json.JSONDecodeError, OSError):
        return "unknown"


def get_skill_stats(skills):
    """Compute aggregate stats from parsed skills list."""
    total = len(skills)
    total_actions = 0
    total_rules = 0
    total_directives = 0
    has_quality_signals = 0
    has_success_criteria = 0
    has_failure_patterns = 0
    providers_seen = set()

    for skill in skills:
        decomp = skill.get("decomposition", {})
        total_actions += len(decomp.get("actions", []))
        total_rules += len(decomp.get("rules", []))
        total_directives += len(decomp.get("directives", []))
        if skill.get("quality_signals"):
            has_quality_signals += 1
        if skill.get("success_criteria"):
            has_success_criteria += 1
        if skill.get("failure_patterns"):
            has_failure_patterns += 1
        for p in skill.get("meta", {}).get("supported_llm_providers", []):
            providers_seen.add(p)

    return {
        "total": total,
        "total_actions": total_actions,
        "total_rules": total_rules,
        "total_directives": total_directives,
        "has_quality_signals": has_quality_signals,
        "has_success_criteria": has_success_criteria,
        "has_failure_patterns": has_failure_patterns,
        "providers_seen": sorted(providers_seen),
    }


def render_overview(skills, schema_version):
    """Render overview panel."""
    stats = get_skill_stats(skills)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"[bold cyan]Skill-0 TUI Dashboard[/bold cyan]  [dim]v{schema_version}[/dim]  [dim]{now}[/dim]",
        "",
        f"  📦 Parsed Skills:     [bold]{stats['total']}[/bold]",
        f"  ⚡ Actions:           [bold]{stats['total_actions']}[/bold]",
        f"  📏 Rules:             [bold]{stats['total_rules']}[/bold]",
        f"  🎯 Directives:        [bold]{stats['total_directives']}[/bold]",
        "",
        f"  [cyan]Quality Signals[/cyan] (Feature 1):  {stats['has_quality_signals']}/{stats['total']}",
        f"  [cyan]Success Criteria[/cyan] (Feature 2): {stats['has_success_criteria']}/{stats['total']}",
        f"  [cyan]Failure Patterns[/cyan] (Feature 3): {stats['has_failure_patterns']}/{stats['total']}",
    ]

    if stats["providers_seen"]:
        providers_str = ", ".join(stats["providers_seen"][:5])
        if len(stats["providers_seen"]) > 5:
            providers_str += f" +{len(stats['providers_seen'])-5}"
        lines.append(f"  [cyan]LLM Providers[/cyan] (Feature 5):   {providers_str}")

    return Panel("\n".join(lines), box=box.ROUNDED, border_style="cyan")


def render_skills_table(skills):
    """Render the main skills table."""
    table = Table(
        title="Parsed Skills",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        header_style="bold cyan",
        min_width=80,
    )
    table.add_column("Skill", style="bold", min_width=28)
    table.add_column("Layer", min_width=18)
    table.add_column("A/R/D", justify="center", min_width=9)
    table.add_column("Quality", min_width=16)
    table.add_column("Providers (F5)", min_width=16)
    table.add_column("Criteria (F2)", justify="center", min_width=10)
    table.add_column("Failures (F3)", justify="center", min_width=10)

    for skill in skills:
        meta = skill.get("meta", {})
        decomp = skill.get("decomposition", {})
        qs = skill.get("quality_signals") or {}

        a = len(decomp.get("actions", []))
        r = len(decomp.get("rules", []))
        d = len(decomp.get("directives", []))

        # Quality column
        if qs:
            ov = qs.get("overall_quality")
            sc = qs.get("schema_validation_score")
            co = qs.get("completeness_score")
            quality_cell = f"{_quality_icon(ov)} sc:{sc:.1f} co:{co:.1f}" if sc is not None and co is not None else f"{_quality_icon(ov)} {ov}"
        else:
            quality_cell = "[dim]—[/dim]"

        # Providers
        providers = meta.get("supported_llm_providers", [])
        providers_str = ", ".join(providers[:2]) if providers else "[dim]—[/dim]"
        if len(providers) > 2:
            providers_str += f" +{len(providers)-2}"

        # Success criteria count
        sc_count = len(skill.get("success_criteria") or [])
        sc_str = f"[green]{sc_count}[/green]" if sc_count > 0 else "[dim]0[/dim]"

        # Failure patterns count
        fp_count = len(skill.get("failure_patterns") or [])
        fp_str = f"[yellow]{fp_count}[/yellow]" if fp_count > 0 else "[dim]0[/dim]"

        # Skill name (strip .json)
        name = meta.get("title") or meta.get("name") or skill.get("_filename", "?").replace(".json", "")
        layer = meta.get("skill_layer", "")

        table.add_row(
            name[:30],
            layer,
            f"{a}/{r}/{d}",
            quality_cell,
            providers_str,
            sc_str,
            fp_str,
        )

    return table


def render_quality_report(skills):
    """Render a quality signals report (Feature 1)."""
    table = Table(
        title="Quality Signals Report (Feature 1 — Triangulated Verification)",
        box=box.SIMPLE_HEAD,
        header_style="bold green",
        min_width=80,
    )
    table.add_column("Skill", style="bold", min_width=30)
    table.add_column("Schema Score", min_width=18)
    table.add_column("Completeness", min_width=18)
    table.add_column("Human Review", justify="center", min_width=12)
    table.add_column("Converged", justify="center", min_width=10)
    table.add_column("Overall", justify="center", min_width=8)

    for skill in skills:
        meta = skill.get("meta", {})
        qs = skill.get("quality_signals") or {}
        name = meta.get("title") or meta.get("name") or skill.get("_filename", "?").replace(".json", "")

        if not qs:
            table.add_row(name[:32], "[dim]—[/dim]", "[dim]—[/dim]", "[dim]—[/dim]", "[dim]—[/dim]", "[dim]—[/dim]")
            continue

        sv = qs.get("schema_validation_score")
        co = qs.get("completeness_score")
        hr = qs.get("human_review_flag")
        sc = qs.get("signal_convergence")
        ov = qs.get("overall_quality")

        sv_str = _quality_bar(sv) if sv is not None else "[dim]—[/dim]"
        co_str = _quality_bar(co) if co is not None else "[dim]—[/dim]"
        hr_str = "[yellow]⚑ Yes[/yellow]" if hr else "[green]✓ No[/green]"
        sc_str = "[green]✓[/green]" if sc else ("[red]✗[/red]" if sc is not None else "[dim]—[/dim]")
        ov_str = f"{_quality_icon(ov)} {ov}" if ov else "[dim]—[/dim]"

        table.add_row(name[:32], sv_str, co_str, hr_str, sc_str, ov_str)

    return table


def render_skill_detail(skill):
    """Render detailed view of a single skill."""
    meta = skill.get("meta", {})
    decomp = skill.get("decomposition", {})
    qs = skill.get("quality_signals") or {}
    criteria = skill.get("success_criteria") or []
    patterns = skill.get("failure_patterns") or []
    providers = meta.get("supported_llm_providers", [])

    name = meta.get("title") or meta.get("name") or "Unknown"
    console.rule(f"[bold cyan]{name}[/bold cyan]")

    # Basic info
    info_lines = [
        f"[bold]ID:[/bold]          {meta.get('skill_id', '—')}",
        f"[bold]Layer:[/bold]       {meta.get('skill_layer', '—')}",
        f"[bold]Schema:[/bold]      {meta.get('schema_version', '—')}",
        f"[bold]Parsed at:[/bold]   {meta.get('parse_timestamp', '—')}",
        f"[bold]Description:[/bold] {meta.get('description', '—')[:80]}",
    ]

    actions = decomp.get("actions", [])
    rules = decomp.get("rules", [])
    directives = decomp.get("directives", [])
    info_lines += [
        "",
        f"[bold]Actions:[/bold]    {len(actions)}",
        f"[bold]Rules:[/bold]      {len(rules)}",
        f"[bold]Directives:[/bold] {len(directives)}",
    ]

    console.print(Panel("\n".join(info_lines), title="Info", border_style="cyan", box=box.ROUNDED))

    # Feature 5: providers
    if providers:
        console.print(Panel(", ".join(providers), title="[cyan]Supported LLM Providers (Feature 5)[/cyan]", border_style="blue", box=box.ROUNDED))

    # Feature 1: quality signals
    if qs:
        qs_lines = []
        sv = qs.get("schema_validation_score")
        co = qs.get("completeness_score")
        if sv is not None:
            qs_lines.append(f"[bold]Schema Validation:[/bold] {_quality_bar(sv)}")
        if co is not None:
            qs_lines.append(f"[bold]Completeness:[/bold]      {_quality_bar(co)}")
        hr = qs.get("human_review_flag")
        if hr is not None:
            qs_lines.append(f"[bold]Human Review Flag:[/bold] {'[yellow]⚑ Required[/yellow]' if hr else '[green]✓ Not Required[/green]'}")
        sc = qs.get("signal_convergence")
        if sc is not None:
            qs_lines.append(f"[bold]Signal Convergence:[/bold] {'[green]✓ Converged[/green]' if sc else '[red]✗ Diverged — escalate[/red]'}")
        ov = qs.get("overall_quality")
        if ov:
            qs_lines.append(f"[bold]Overall Quality:[/bold]    {_quality_icon(ov)} {ov}")
        if qs.get("review_notes"):
            qs_lines.append(f"[bold]Notes:[/bold]             {qs['review_notes']}")
        console.print(Panel("\n".join(qs_lines), title="[green]Quality Signals (Feature 1 — Triangulated Verification)[/green]", border_style="green", box=box.ROUNDED))

    # Feature 2: success criteria
    if criteria:
        sc_table = Table(box=box.SIMPLE, header_style="bold yellow")
        sc_table.add_column("ID")
        sc_table.add_column("Description")
        sc_table.add_column("Metric")
        sc_table.add_column("Weight", justify="right")
        sc_table.add_column("Target")
        for c in criteria:
            sc_table.add_row(
                c.get("id", ""),
                c.get("description", "")[:40],
                c.get("metric", ""),
                f"{c.get('weight', 0):.1%}",
                c.get("target", "[dim]—[/dim]"),
            )
        console.print(Panel(sc_table, title="[yellow]Success Criteria (Feature 2)[/yellow]", border_style="yellow", box=box.ROUNDED))

    # Feature 3: failure patterns
    if patterns:
        fp_table = Table(box=box.SIMPLE, header_style="bold red")
        fp_table.add_column("ID")
        fp_table.add_column("Description")
        fp_table.add_column("Recovery")
        fp_table.add_column("Freq")
        fp_table.add_column("Evolution Hint")
        for p in patterns:
            fp_table.add_row(
                p.get("pattern_id", ""),
                p.get("description", "")[:35],
                p.get("recovery_strategy", "[dim]—[/dim]")[:30],
                p.get("frequency", "[dim]—[/dim]"),
                p.get("evolution_hint", "[dim]—[/dim]")[:35],
            )
        console.print(Panel(fp_table, title="[red]Failure Patterns (Feature 3 — Reflexion)[/red]", border_style="red", box=box.ROUNDED))

    # Feature 6: completion directives with satisfaction score
    completion_dirs = [d for d in directives if d.get("directive_type") == "completion" and (d.get("satisfaction_score") is not None or d.get("satisfaction_criteria"))]
    if completion_dirs:
        cd_lines = []
        for d in completion_dirs:
            score = d.get("satisfaction_score")
            criteria_text = d.get("satisfaction_criteria", "")
            score_str = _quality_bar(score) if score is not None else "[dim]—[/dim]"
            cd_lines.append(f"[bold]{d.get('id')}[/bold] {d.get('name', '')} → {score_str}")
            if criteria_text:
                cd_lines.append(f"  [dim]{criteria_text[:70]}[/dim]")
        console.print(Panel("\n".join(cd_lines), title="[magenta]Directive Satisfaction Scores (Feature 6)[/magenta]", border_style="magenta", box=box.ROUNDED))


def output_json(skills):
    """Output skills data as JSON (CI-friendly mode)."""
    stats = get_skill_stats(skills)
    output = {
        "schema_version": load_schema_version(),
        "generated_at": datetime.now().isoformat(),
        "stats": stats,
        "skills": [
            {
                "filename": s.get("_filename"),
                "skill_id": s.get("meta", {}).get("skill_id"),
                "name": s.get("meta", {}).get("name"),
                "layer": s.get("meta", {}).get("skill_layer"),
                "actions": len(s.get("decomposition", {}).get("actions", [])),
                "rules": len(s.get("decomposition", {}).get("rules", [])),
                "directives": len(s.get("decomposition", {}).get("directives", [])),
                "quality_signals": s.get("quality_signals"),
                "success_criteria_count": len(s.get("success_criteria") or []),
                "failure_patterns_count": len(s.get("failure_patterns") or []),
                "supported_llm_providers": s.get("meta", {}).get("supported_llm_providers", []),
            }
            for s in skills
        ],
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="Skill-0 TUI Dashboard — terminal UI for parsed skills and governance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Features implemented (from Hive comparison):
  Feature 1: quality_signals  — triangulated verification scores
  Feature 2: success_criteria — weighted multi-dimensional quality metrics
  Feature 3: failure_patterns — reflexion-style failure mode recording
  Feature 5: supported_llm_providers — LLM provider tagging in meta
  Feature 6: satisfaction_score — completion directive satisfaction
  Feature 8: TUI dashboard    — this tool
        """,
    )
    parser.add_argument("--parsed-dir", type=Path, default=PARSED_DIR, help="Parsed skills directory")
    parser.add_argument("--skill", metavar="NAME", help="Show detail view for a specific skill (partial name match)")
    parser.add_argument("--quality", action="store_true", help="Show quality signals report (Feature 1)")
    parser.add_argument("--json", action="store_true", help="Output as JSON (CI-friendly, no Rich required)")
    parser.add_argument("--parsed-only", action="store_true", help="Show parsed skills table only")

    args = parser.parse_args()

    parsed_dir = args.parsed_dir
    skills = load_parsed_skills(parsed_dir)

    # JSON mode — no Rich required
    if args.json:
        output_json(skills)
        return

    # Non-Rich fallback
    if not RICH_AVAILABLE:
        print("Rich not installed. Install with: pip install rich")
        print()
        stats = get_skill_stats(skills)
        print(f"Skill-0 Dashboard | Schema v{load_schema_version()}")
        print(f"Parsed skills: {stats['total']}")
        print(f"  A:{stats['total_actions']} R:{stats['total_rules']} D:{stats['total_directives']}")
        print(f"With quality_signals:  {stats['has_quality_signals']}")
        print(f"With success_criteria: {stats['has_success_criteria']}")
        print(f"With failure_patterns: {stats['has_failure_patterns']}")
        return

    schema_version = load_schema_version()

    if not skills:
        console.print(f"[yellow]No parsed skills found in {parsed_dir}[/yellow]")
        return

    # Detail view for a specific skill
    if args.skill:
        query = args.skill.lower()
        matches = [s for s in skills if query in (s.get("meta", {}).get("name") or "").lower()
                   or query in (s.get("meta", {}).get("title") or "").lower()
                   or query in s.get("_filename", "").lower()]
        if not matches:
            console.print(f"[red]No skill found matching '{args.skill}'[/red]")
            sys.exit(1)
        render_skill_detail(matches[0])
        return

    # Quality report
    if args.quality:
        console.print(render_quality_report(skills))
        return

    # Full dashboard (default)
    console.print()
    console.print(render_overview(skills, schema_version))
    console.print()
    console.print(render_skills_table(skills))
    console.print()
    console.print("[dim]Run with --skill <name> for details  |  --quality for quality report  |  --json for CI output[/dim]")


if __name__ == "__main__":
    main()
