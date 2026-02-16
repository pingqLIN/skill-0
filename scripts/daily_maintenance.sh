#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PYTHON_BIN="${PYTHON_BIN:-python3}"
RUN_SECURITY_SCAN="${RUN_SECURITY_SCAN:-1}"
SECURITY_SCAN_LIMIT="${SECURITY_SCAN_LIMIT:-}"
SECURITY_SCAN_FORCE="${SECURITY_SCAN_FORCE:-0}"
SECURITY_DB_PATH="${SECURITY_DB_PATH:-$PROJECT_ROOT/governance/db/governance.db}"

failures=0

run_step() {
    local name="$1"
    shift
    echo "[STEP] ${name}"
    if "$@"; then
        echo "[OK] ${name}"
    else
        echo "[FAIL] ${name}"
        failures=$((failures + 1))
    fi
    echo ""
}

build_security_scan_cmd() {
    local cmd=("$PYTHON_BIN" "$PROJECT_ROOT/tools/batch_security_scan.py" "--db" "$SECURITY_DB_PATH")
    if [[ -n "$SECURITY_SCAN_LIMIT" ]]; then
        cmd+=("--limit" "$SECURITY_SCAN_LIMIT")
    fi
    if [[ "$SECURITY_SCAN_FORCE" == "1" ]]; then
        cmd+=("--force")
    fi
    printf '%s\0' "${cmd[@]}"
}

echo "=== Skill-0 Daily Maintenance ==="
echo "Project root: $PROJECT_ROOT"
echo ""

run_step "Database backup" "$SCRIPT_DIR/backup_db.sh"
run_step "DB health check (WAL + backup recency)" "$SCRIPT_DIR/check_db_health.sh"

if [[ "$RUN_SECURITY_SCAN" == "1" ]]; then
    mapfile -d '' scan_cmd < <(build_security_scan_cmd)
    run_step "Security scan" "${scan_cmd[@]}"
else
    echo "[SKIP] Security scan disabled (RUN_SECURITY_SCAN=0)"
    echo ""
fi

if (( failures > 0 )); then
    echo "Daily maintenance finished with ${failures} failure(s)."
    exit 1
fi

echo "Daily maintenance completed successfully."
