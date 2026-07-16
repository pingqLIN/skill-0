from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from runtime.certification import (
    PRODUCTION_APPROVAL_SCHEMA_PATH,
    SignedProductionApprovalGate,
    build_production_approval,
    build_production_revocation,
    load_certification_evidence,
    load_certification_manifest,
)
from runtime.digest import canonical_digest
from runtime.validators import load_json, validate_schema


APPROVAL_KEY_ENV = "SKILL0_ADAPTER_APPROVAL_KEY"


def _key() -> str:
    value = os.getenv(APPROVAL_KEY_ENV, "")
    if len(value) < 32:
        raise SystemExit(
            f"{APPROVAL_KEY_ENV} must be present and contain at least 32 characters"
        )
    return value


def _identity_adapter(manifest: dict[str, Any]) -> Any:
    adapter = manifest["adapter"]
    return SimpleNamespace(
        adapter_id=adapter["id"],
        adapter_version=adapter["version"],
        adapter_kind=adapter["kind"],
        adapter_target=adapter["target"],
        adapter_artifact_digest=adapter["artifact_digest"],
        certification_manifest_digest=canonical_digest(manifest),
    )


def _bindings(approval: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "action_id": item["action_id"],
            "role": "primary",
            "adapter": {
                "kind": approval["adapter"]["kind"],
                "target": approval["adapter"]["target"],
            },
            "effect": {
                "resource_kind": item["resource_kind"],
                "operation": item["operation"],
            },
        }
        for item in approval["allowed_operations"]
    ]


def issue(args: argparse.Namespace) -> int:
    manifest = load_certification_manifest(args.manifest)
    evidence = load_certification_evidence(args.evidence)
    approval = build_production_approval(
        manifest,
        evidence,
        environment=args.environment,
        approved_by=args.approved_by,
        expires_at=args.expires_at,
        key=_key(),
    )
    if not args.output.parent.is_dir():
        raise SystemExit("output parent must already exist")
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(approval, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    print(
        json.dumps(
            {
                "approval_id": approval["approval_id"],
                "adapter_id": approval["adapter"]["id"],
                "environment": approval["environment"],
                "expires_at": approval["expires_at"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


def verify(args: argparse.Namespace) -> int:
    approval = load_json(args.approval)
    validate_schema(approval, load_json(PRODUCTION_APPROVAL_SCHEMA_PATH))
    manifest = load_certification_manifest(args.manifest)
    gate = SignedProductionApprovalGate(
        approval,
        key=_key(),
        environment=args.environment,
        now=lambda: datetime.now(timezone.utc),
    )
    decision = gate.evaluate(
        _identity_adapter(manifest),
        _bindings(approval),
    )
    print(
        json.dumps(
            {
                "allowed": decision.allowed,
                "reason": decision.reason,
                "approval_id": approval["approval_id"],
                "adapter_id": approval["adapter"]["id"],
                "environment": args.environment,
            },
            sort_keys=True,
        )
    )
    return 0 if decision.allowed else 1


def revoke(args: argparse.Namespace) -> int:
    approval = load_json(args.approval)
    revoked = build_production_revocation(
        approval,
        revoked_by=args.revoked_by,
        key=_key(),
    )
    if not args.output.parent.is_dir():
        raise SystemExit("output parent must already exist")
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(revoked, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    print(
        json.dumps(
            {
                "approval_id": revoked["approval_id"],
                "adapter_id": revoked["adapter"]["id"],
                "decision": "revoked",
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Issue or verify a scoped adapter production approval."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue_parser = subparsers.add_parser(
        "issue", help="Create a signed approval after human review."
    )
    issue_parser.add_argument("--manifest", type=Path, required=True)
    issue_parser.add_argument("--evidence", type=Path, required=True)
    issue_parser.add_argument("--environment", required=True)
    issue_parser.add_argument("--approved-by", required=True)
    issue_parser.add_argument("--expires-at", required=True)
    issue_parser.add_argument("--output", type=Path, required=True)
    issue_parser.set_defaults(handler=issue)

    verify_parser = subparsers.add_parser(
        "verify", help="Verify a signed approval without running an adapter."
    )
    verify_parser.add_argument("--approval", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.add_argument("--environment", required=True)
    verify_parser.set_defaults(handler=verify)

    revoke_parser = subparsers.add_parser(
        "revoke", help="Create a signed fail-closed revocation record."
    )
    revoke_parser.add_argument("--approval", type=Path, required=True)
    revoke_parser.add_argument("--revoked-by", required=True)
    revoke_parser.add_argument("--output", type=Path, required=True)
    revoke_parser.set_defaults(handler=revoke)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
