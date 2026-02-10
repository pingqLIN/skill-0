<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
#!/usr/bin/env python3
"""Migrate Skill-0 data/DB from schema v2.0.0 -> v2.1.0.

What this does:
- Updates parsed skill JSON files: meta.schema_version, meta.parser_version
- Updates skills.db (vector store) skills.version + raw_json.meta.* (does NOT touch embeddings)
- Optionally updates governance DB scanner_version fields (dashboard)

This migration is intentionally conservative: it does not invent provenance data.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


OLD_SCHEMA_VERSION = "2.0.0"
NEW_SCHEMA_VERSION = "2.1.0"
OLD_PARSER_VERSION = "skill-0 v2.0"
NEW_PARSER_VERSION = "skill-0 v2.1"


@dataclass
class Counters:
    parsed_files_total: int = 0
    parsed_files_updated: int = 0
    db_rows_total: int = 0
    db_rows_updated: int = 0
    governance_skills_updated: int = 0
    governance_scans_updated: int = 0


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _backup_file(path: Path, suffix: str, dry_run: bool) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".{suffix}.{ts}.bak")
    if dry_run:
        return backup
    shutil.copy2(path, backup)
    return backup


def _migrate_meta(meta: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    changed = False

    if meta.get("schema_version") == OLD_SCHEMA_VERSION:
        meta["schema_version"] = NEW_SCHEMA_VERSION
        changed = True

    pv = meta.get("parser_version")
    if pv == OLD_PARSER_VERSION:
        meta["parser_version"] = NEW_PARSER_VERSION
        changed = True
    elif isinstance(pv, str) and pv.startswith(OLD_PARSER_VERSION):
        meta["parser_version"] = pv.replace(OLD_PARSER_VERSION, NEW_PARSER_VERSION, 1)
        changed = True

    return meta, changed


def migrate_parsed_dir(parsed_dir: Path, dry_run: bool) -> Counters:
    counters = Counters()

    for path in sorted(parsed_dir.glob("*.json")):
        counters.parsed_files_total += 1
        data = _read_json(path)
        meta = data.get("meta")
        if not isinstance(meta, dict):
            continue

        _, changed = _migrate_meta(meta)
        if changed:
            counters.parsed_files_updated += 1
            if not dry_run:
                _write_json(path, data)

    return counters


def migrate_skills_db(skills_db: Path, make_backup: bool, dry_run: bool) -> Counters:
    counters = Counters()

    if make_backup:
        _backup_file(skills_db, "pre-migrate", dry_run=dry_run)

    con = sqlite3.connect(str(skills_db))
    try:
        cur = con.cursor()
        rows = cur.execute("SELECT id, version, raw_json FROM skills").fetchall()
        counters.db_rows_total = len(rows)

        for skill_id, version, raw_json in rows:
            if not raw_json:
                continue
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            meta = data.get("meta")
            if not isinstance(meta, dict):
                continue

            _, changed = _migrate_meta(meta)

            # Keep the version column aligned with meta.schema_version when it was OLD
            version_changed = False
            if version == OLD_SCHEMA_VERSION:
                version = NEW_SCHEMA_VERSION
                version_changed = True

            if changed or version_changed:
                counters.db_rows_updated += 1
                if not dry_run:
                    cur.execute(
                        "UPDATE skills SET version = ?, raw_json = ? WHERE id = ?",
                        (version, json.dumps(data, ensure_ascii=False), skill_id),
                    )

        if not dry_run:
            con.commit()
    finally:
        con.close()

    return counters


def migrate_governance_db(
    governance_db: Path,
    from_scanner_version: str,
    to_scanner_version: str,
    make_backup: bool,
    dry_run: bool,
) -> Counters:
    counters = Counters()

    if not governance_db.exists():
        return counters

    if make_backup:
        _backup_file(governance_db, "pre-migrate", dry_run=dry_run)

    con = sqlite3.connect(str(governance_db))
    try:
        cur = con.cursor()

        # skills.scanner_version
        cur.execute(
            "SELECT COUNT(*) FROM skills WHERE scanner_version = ?",
            (from_scanner_version,),
        )
        counters.governance_skills_updated = int(cur.fetchone()[0] or 0)

        # security_scans.scanner_version
        cur.execute(
            "SELECT COUNT(*) FROM security_scans WHERE scanner_version = ?",
            (from_scanner_version,),
        )
        counters.governance_scans_updated = int(cur.fetchone()[0] or 0)

        if not dry_run:
            cur.execute(
                "UPDATE skills SET scanner_version = ? WHERE scanner_version = ?",
                (to_scanner_version, from_scanner_version),
            )
            cur.execute(
                "UPDATE security_scans SET scanner_version = ? WHERE scanner_version = ?",
                (to_scanner_version, from_scanner_version),
            )
            con.commit()
    finally:
        con.close()

    return counters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", type=Path, default=Path("parsed"))
    ap.add_argument("--skills-db", type=Path, default=Path("skills.db"))
    ap.add_argument(
        "--governance-db",
        type=Path,
        default=Path("governance") / "db" / "governance.db",
    )
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--update-dashboard-scanner-version",
        action="store_true",
        help="Also update governance DB scanner_version fields (for dashboard display).",
    )
    ap.add_argument(
        "--scanner-from",
        default="2.0.0",
        help="Governance scanner_version to replace (default: 2.0.0)",
    )
    ap.add_argument(
        "--scanner-to",
        default="2.1.0",
        help="Governance scanner_version replacement (default: 2.1.0)",
    )

    args = ap.parse_args()
    make_backup = not args.no_backup

    if not args.parsed_dir.exists():
        raise SystemExit(f"Parsed dir not found: {args.parsed_dir}")
    if not args.skills_db.exists():
        raise SystemExit(f"skills.db not found: {args.skills_db}")

    p = migrate_parsed_dir(args.parsed_dir, dry_run=args.dry_run)
    d = migrate_skills_db(args.skills_db, make_backup=make_backup, dry_run=args.dry_run)

    g = Counters()
    if args.update_dashboard_scanner_version:
        g = migrate_governance_db(
            args.governance_db,
            from_scanner_version=args.scanner_from,
            to_scanner_version=args.scanner_to,
            make_backup=make_backup,
            dry_run=args.dry_run,
        )

    print(
        json.dumps(
            {
                "parsed_files_total": p.parsed_files_total,
                "parsed_files_updated": p.parsed_files_updated,
                "skills_db_rows_total": d.db_rows_total,
                "skills_db_rows_updated": d.db_rows_updated,
                "governance_skills_updated": g.governance_skills_updated,
                "governance_scans_updated": g.governance_scans_updated,
                "dry_run": bool(args.dry_run),
                "schema_from": OLD_SCHEMA_VERSION,
                "schema_to": NEW_SCHEMA_VERSION,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
=======
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
#!/usr/bin/env python3
"""Migrate Skill-0 data/DB from schema v2.0.0 -> v2.1.0.

What this does:
- Updates parsed skill JSON files: meta.schema_version, meta.parser_version
- Updates skills.db (vector store) skills.version + raw_json.meta.* (does NOT touch embeddings)
- Optionally updates governance DB scanner_version fields (dashboard)

This migration is intentionally conservative: it does not invent provenance data.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


OLD_SCHEMA_VERSION = "2.0.0"
NEW_SCHEMA_VERSION = "2.1.0"
OLD_PARSER_VERSION = "skill-0 v2.0"
NEW_PARSER_VERSION = "skill-0 v2.1"


@dataclass
class Counters:
    parsed_files_total: int = 0
    parsed_files_updated: int = 0
    db_rows_total: int = 0
    db_rows_updated: int = 0
    governance_skills_updated: int = 0
    governance_scans_updated: int = 0


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _backup_file(path: Path, suffix: str, dry_run: bool) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(path.suffix + f".{suffix}.{ts}.bak")
    if dry_run:
        return backup
    shutil.copy2(path, backup)
    return backup


def _migrate_meta(meta: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    changed = False

    if meta.get("schema_version") == OLD_SCHEMA_VERSION:
        meta["schema_version"] = NEW_SCHEMA_VERSION
        changed = True

    pv = meta.get("parser_version")
    if pv == OLD_PARSER_VERSION:
        meta["parser_version"] = NEW_PARSER_VERSION
        changed = True
    elif isinstance(pv, str) and pv.startswith(OLD_PARSER_VERSION):
        meta["parser_version"] = pv.replace(OLD_PARSER_VERSION, NEW_PARSER_VERSION, 1)
        changed = True

    return meta, changed


def migrate_parsed_dir(parsed_dir: Path, dry_run: bool) -> Counters:
    counters = Counters()

    for path in sorted(parsed_dir.glob("*.json")):
        counters.parsed_files_total += 1
        data = _read_json(path)
        meta = data.get("meta")
        if not isinstance(meta, dict):
            continue

        _, changed = _migrate_meta(meta)
        if changed:
            counters.parsed_files_updated += 1
            if not dry_run:
                _write_json(path, data)

    return counters


def migrate_skills_db(skills_db: Path, make_backup: bool, dry_run: bool) -> Counters:
    counters = Counters()

    if make_backup:
        _backup_file(skills_db, "pre-migrate", dry_run=dry_run)

    con = sqlite3.connect(str(skills_db))
    try:
        cur = con.cursor()
        rows = cur.execute("SELECT id, version, raw_json FROM skills").fetchall()
        counters.db_rows_total = len(rows)

        for skill_id, version, raw_json in rows:
            if not raw_json:
                continue
            try:
                data = json.loads(raw_json)
            except json.JSONDecodeError:
                continue

            meta = data.get("meta")
            if not isinstance(meta, dict):
                continue

            _, changed = _migrate_meta(meta)

            # Keep the version column aligned with meta.schema_version when it was OLD
            version_changed = False
            if version == OLD_SCHEMA_VERSION:
                version = NEW_SCHEMA_VERSION
                version_changed = True

            if changed or version_changed:
                counters.db_rows_updated += 1
                if not dry_run:
                    cur.execute(
                        "UPDATE skills SET version = ?, raw_json = ? WHERE id = ?",
                        (version, json.dumps(data, ensure_ascii=False), skill_id),
                    )

        if not dry_run:
            con.commit()
    finally:
        con.close()

    return counters


def migrate_governance_db(
    governance_db: Path,
    from_scanner_version: str,
    to_scanner_version: str,
    make_backup: bool,
    dry_run: bool,
) -> Counters:
    counters = Counters()

    if not governance_db.exists():
        return counters

    if make_backup:
        _backup_file(governance_db, "pre-migrate", dry_run=dry_run)

    con = sqlite3.connect(str(governance_db))
    try:
        cur = con.cursor()

        # skills.scanner_version
        cur.execute(
            "SELECT COUNT(*) FROM skills WHERE scanner_version = ?",
            (from_scanner_version,),
        )
        counters.governance_skills_updated = int(cur.fetchone()[0] or 0)

        # security_scans.scanner_version
        cur.execute(
            "SELECT COUNT(*) FROM security_scans WHERE scanner_version = ?",
            (from_scanner_version,),
        )
        counters.governance_scans_updated = int(cur.fetchone()[0] or 0)

        if not dry_run:
            cur.execute(
                "UPDATE skills SET scanner_version = ? WHERE scanner_version = ?",
                (to_scanner_version, from_scanner_version),
            )
            cur.execute(
                "UPDATE security_scans SET scanner_version = ? WHERE scanner_version = ?",
                (to_scanner_version, from_scanner_version),
            )
            con.commit()
    finally:
        con.close()

    return counters


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", type=Path, default=Path("parsed"))
    ap.add_argument("--skills-db", type=Path, default=Path("skills.db"))
    ap.add_argument(
        "--governance-db",
        type=Path,
        default=Path("governance") / "db" / "governance.db",
    )
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--update-dashboard-scanner-version",
        action="store_true",
        help="Also update governance DB scanner_version fields (for dashboard display).",
    )
    ap.add_argument(
        "--scanner-from",
        default="2.0.0",
        help="Governance scanner_version to replace (default: 2.0.0)",
    )
    ap.add_argument(
        "--scanner-to",
        default="2.1.0",
        help="Governance scanner_version replacement (default: 2.1.0)",
    )

    args = ap.parse_args()
    make_backup = not args.no_backup

    if not args.parsed_dir.exists():
        raise SystemExit(f"Parsed dir not found: {args.parsed_dir}")
    if not args.skills_db.exists():
        raise SystemExit(f"skills.db not found: {args.skills_db}")

    p = migrate_parsed_dir(args.parsed_dir, dry_run=args.dry_run)
    d = migrate_skills_db(args.skills_db, make_backup=make_backup, dry_run=args.dry_run)

    g = Counters()
    if args.update_dashboard_scanner_version:
        g = migrate_governance_db(
            args.governance_db,
            from_scanner_version=args.scanner_from,
            to_scanner_version=args.scanner_to,
            make_backup=make_backup,
            dry_run=args.dry_run,
        )

    print(
        json.dumps(
            {
                "parsed_files_total": p.parsed_files_total,
                "parsed_files_updated": p.parsed_files_updated,
                "skills_db_rows_total": d.db_rows_total,
                "skills_db_rows_updated": d.db_rows_updated,
                "governance_skills_updated": g.governance_skills_updated,
                "governance_scans_updated": g.governance_scans_updated,
                "dry_run": bool(args.dry_run),
                "schema_from": OLD_SCHEMA_VERSION,
                "schema_to": NEW_SCHEMA_VERSION,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
<<<<<<< Updated upstream
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
