#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SKILLS_DB="${SKILL0_DB_PATH:-$PROJECT_ROOT/skills.db}"
GOVERNANCE_DB="${GOVERNANCE_DB_PATH:-${SKILL0_GOVERNANCE_DB_PATH:-$PROJECT_ROOT/governance/db/governance.db}}"
RUNTIME_DB="${RUNTIME_DB_PATH:-${SKILL0_RUNTIME_DB_PATH:-$PROJECT_ROOT/governance/db/runtime.db}}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
MAX_BACKUP_AGE_DAYS="${MAX_BACKUP_AGE_DAYS:-2}"
PYTHON_BIN="${PYTHON_BIN:-}"

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

file_mtime_epoch() {
    local file_path="$1"
    stat -c %Y "$file_path" 2>/dev/null || stat -f %m "$file_path" 2>/dev/null
}

sqlite_journal_mode() {
    local db_path="$1"
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$db_path" "PRAGMA journal_mode;"
        return
    fi
    find_python_bin
    if [[ -z "$PYTHON_BIN" ]]; then
        echo ""
        return 127
    fi
    "$PYTHON_BIN" - "$db_path" <<'PY'
import sqlite3
import sys

with sqlite3.connect(sys.argv[1]) as conn:
    row = conn.execute("PRAGMA journal_mode;").fetchone()
    print(row[0] if row else "")
PY
}

check_journal_mode() {
    local db_path="$1"
    local db_name="$2"
    local expected_mode="$3"

    if [[ ! -f "$db_path" ]]; then
        echo "[FAIL] ${db_name}: database not found at ${db_path}"
        failures=$((failures + 1))
        return
    fi

    local mode
    mode="$(sqlite_journal_mode "$db_path" | tr -d '\r\n' || true)"
    if [[ "$expected_mode" == "any" ]]; then
        echo "[OK] ${db_name}: journal mode is '${mode:-unknown}'"
    elif [[ "$mode" == "$expected_mode" ]]; then
        echo "[OK] ${db_name}: journal mode is '${mode}'"
    else
        echo "[FAIL] ${db_name}: journal mode is '${mode:-unknown}' (expected '${expected_mode}')"
        failures=$((failures + 1))
    fi
}

check_backup_recency() {
    local prefix="$1"
    local label="$2"

    local latest_backup
    latest_backup="$(ls -1t "$BACKUP_DIR"/"${prefix}"_*.db 2>/dev/null | head -n 1 || true)"

    if [[ -z "$latest_backup" ]]; then
        echo "[FAIL] ${label}: no backups found in ${BACKUP_DIR}"
        failures=$((failures + 1))
        return
    fi

    local mtime now age_days
    mtime="$(file_mtime_epoch "$latest_backup")"
    now="$(date +%s)"
    age_days="$(( (now - mtime) / 86400 ))"

    if (( age_days > MAX_BACKUP_AGE_DAYS )); then
        echo "[FAIL] ${label}: latest backup is ${age_days} day(s) old (${latest_backup})"
        failures=$((failures + 1))
    else
        echo "[OK] ${label}: latest backup age ${age_days} day(s) (${latest_backup})"
    fi
}

echo "=== Skill-0 DB Health Check ==="
echo "Max backup age: ${MAX_BACKUP_AGE_DAYS} day(s)"
echo ""

check_journal_mode "$SKILLS_DB" "skills.db" "${SKILLS_EXPECTED_JOURNAL_MODE:-any}"
check_journal_mode "$GOVERNANCE_DB" "governance.db" "${GOVERNANCE_EXPECTED_JOURNAL_MODE:-any}"
check_journal_mode "$RUNTIME_DB" "runtime.db" "${RUNTIME_EXPECTED_JOURNAL_MODE:-wal}"

echo ""
check_backup_recency "skills" "skills backup"
check_backup_recency "governance" "governance backup"
check_backup_recency "runtime" "runtime backup"

echo ""
if (( failures > 0 )); then
    echo "Health check failed: ${failures} issue(s) detected."
    exit 1
fi

echo "Health check passed."
