#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SKILLS_DB="${SKILL0_DB_PATH:-$PROJECT_ROOT/skills.db}"
GOVERNANCE_DB="${GOVERNANCE_DB_PATH:-${SKILL0_GOVERNANCE_DB_PATH:-$PROJECT_ROOT/governance/db/governance.db}}"
RUNTIME_DB="${RUNTIME_DB_PATH:-${SKILL0_RUNTIME_DB_PATH:-$PROJECT_ROOT/governance/db/runtime.db}}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
PYTHON_BIN="${PYTHON_BIN:-}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

failures=0

find_python_bin() {
    if [[ -n "$PYTHON_BIN" ]]; then
        return
    fi
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_BIN="python3"
        return
    fi
    if command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
        return
    fi
}

require_sqlite_backup_runtime() {
    if command -v sqlite3 >/dev/null 2>&1; then
        return
    fi
    find_python_bin
    if [[ -z "$PYTHON_BIN" ]]; then
        echo "Neither sqlite3 nor Python sqlite3 runtime was found." >&2
        exit 127
    fi
}

validate_retention_days() {
    if [[ ! "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
        echo "BACKUP_RETENTION_DAYS must be a non-negative integer." >&2
        exit 2
    fi
}

backup_database() {
    local db_path="$1"
    local prefix="$2"
    local label="$3"

    if [[ ! -f "$db_path" ]]; then
        echo "[FAIL] ${label}: database not found at ${db_path}"
        failures=$((failures + 1))
        return
    fi

    local backup_file="${BACKUP_DIR}/${prefix}_${TIMESTAMP}.db"
    if {
        if command -v sqlite3 >/dev/null 2>&1; then
            sqlite3 "$db_path" ".backup '${backup_file}'"
        else
            "$PYTHON_BIN" - "$db_path" "$backup_file" <<'PY'
import sqlite3
import sys

source_path, backup_path = sys.argv[1], sys.argv[2]
with sqlite3.connect(source_path) as source, sqlite3.connect(backup_path) as backup:
    source.backup(backup)
PY
        fi
    }; then
        echo "[OK] ${label}: wrote ${backup_file}"
    else
        echo "[FAIL] ${label}: backup failed (${db_path})"
        failures=$((failures + 1))
    fi
}

cleanup_old_backups() {
    local prefix="$1"
    local label="$2"
    local removed_count=0

    while IFS= read -r backup_file; do
        rm -f "$backup_file"
        removed_count=$((removed_count + 1))
    done < <(find "$BACKUP_DIR" -maxdepth 1 -type f -name "${prefix}_*.db" -mtime +"$BACKUP_RETENTION_DAYS")

    echo "[OK] ${label}: removed ${removed_count} file(s) older than ${BACKUP_RETENTION_DAYS} day(s)"
}

echo "=== Skill-0 Database Backup ==="
echo "Backup directory: ${BACKUP_DIR}"
echo "Retention: ${BACKUP_RETENTION_DAYS} day(s)"
echo ""

require_sqlite_backup_runtime
validate_retention_days
mkdir -p "$BACKUP_DIR"

backup_database "$SKILLS_DB" "skills" "skills.db"
backup_database "$GOVERNANCE_DB" "governance" "governance.db"
backup_database "$RUNTIME_DB" "runtime" "runtime.db"

echo ""
cleanup_old_backups "skills" "skills backups"
cleanup_old_backups "governance" "governance backups"
cleanup_old_backups "runtime" "runtime backups"

echo ""
if (( failures > 0 )); then
    echo "Backup completed with ${failures} failure(s)."
    exit 1
fi

echo "Backup completed successfully."
