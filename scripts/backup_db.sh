#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SKILLS_DB="${SKILL0_DB_PATH:-$PROJECT_ROOT/skills.db}"
GOVERNANCE_DB="${GOVERNANCE_DB_PATH:-$PROJECT_ROOT/governance/db/governance.db}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

backup_db() {
    local src="$1"
    local name="$2"

    if [ ! -f "$src" ]; then
        echo "[SKIP] $name not found at $src"
        return 0
    fi

    local dest="$BACKUP_DIR/${name}_${TIMESTAMP}.db"
    sqlite3 "$src" ".backup '$dest'"
    local size
    size=$(stat -c%s "$dest" 2>/dev/null || stat -f%z "$dest" 2>/dev/null)
    echo "[OK] $name -> $dest ($size bytes)"
}

cleanup_old() {
    local count
    count=$(find "$BACKUP_DIR" -name "*.db" -mtime +"$RETENTION_DAYS" 2>/dev/null | wc -l)
    if [ "$count" -gt 0 ]; then
        find "$BACKUP_DIR" -name "*.db" -mtime +"$RETENTION_DAYS" -delete
        echo "[CLEANUP] Removed $count backup(s) older than ${RETENTION_DAYS} days"
    fi
}

echo "=== Skill-0 Database Backup ==="
echo "Timestamp: $TIMESTAMP"
echo ""

backup_db "$SKILLS_DB" "skills"
backup_db "$GOVERNANCE_DB" "governance"

echo ""
cleanup_old

total=$(find "$BACKUP_DIR" -name "*.db" 2>/dev/null | wc -l)
echo "Total backups: $total"
echo "=== Backup complete ==="
