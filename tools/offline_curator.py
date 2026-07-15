#!/usr/bin/env python3
"""Prepare offline Curator prompts and build dry Skill-0 proposals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# This bootstrap keeps direct `python tools/offline_curator.py` execution working.
from curation.offline_curator import (  # noqa: E402
    DEFAULT_MANIFEST_PATH,
    CuratorBoundaryError,
    build_draft_proposal,
    build_prompt_package,
    load_json_object,
    write_dry_json_artifact,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Verified offline Curator manifest.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Build a deterministic prompt package.")
    prepare.add_argument("--trajectory", type=Path, required=True)
    prepare.add_argument("--skill-context", type=Path, required=True)
    prepare.add_argument("--model-id", required=True)
    prepare.add_argument("--output", type=Path)

    propose = subparsers.add_parser("propose", help="Build a dry draft proposal.")
    propose.add_argument("--prompt-package", type=Path, required=True)
    propose.add_argument("--decision", type=Path, required=True)
    propose.add_argument("--current-context", type=Path, required=True)
    propose.add_argument("--candidate-artifact", type=Path)
    propose.add_argument("--created-at")
    propose.add_argument("--output", type=Path)
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "prepare":
        return build_prompt_package(
            load_json_object(args.trajectory),
            load_json_object(args.skill_context),
            model_id=args.model_id,
            manifest_path=args.manifest,
        )

    candidate_artifact = None
    candidate_name = "SKILL.md"
    if args.candidate_artifact is not None:
        candidate_artifact = args.candidate_artifact.read_bytes()
        candidate_name = args.candidate_artifact.name
    return build_draft_proposal(
        load_json_object(args.prompt_package),
        load_json_object(args.decision),
        load_json_object(args.current_context),
        candidate_artifact=candidate_artifact,
        candidate_name=candidate_name,
        created_at=args.created_at,
        manifest_path=args.manifest,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        document = run(args)
        if args.output is None:
            print(json.dumps(document, ensure_ascii=False, indent=2))
        else:
            output_path = write_dry_json_artifact(document, args.output)
            print(f"Dry Curator artifact written to {output_path}")
    except (CuratorBoundaryError, OSError, json.JSONDecodeError) as exc:
        print(f"offline curator rejected input: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
