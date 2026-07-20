#!/bin/sh
set -eu

RUNTIME_DB="${SKILL0_DB_PATH:-/app/data/skills.db}"
RUNTIME_LEDGER="${SKILL0_RUNTIME_DB_PATH:-/app/runtime-data/runtime.db}"
RUNTIME_JOURNAL_MODE="${SKILL0_RUNTIME_JOURNAL_MODE:-DELETE}"
HITL_TTL_SECONDS="${SKILL0_RUNTIME_HITL_TTL_SECONDS:-86400}"
ALLOW_RUNTIME_INITIALIZE="${SKILL0_RUNTIME_ALLOW_INITIALIZE:-false}"
SEED_DB="/app/bootstrap/skills.db"

mkdir -p "$(dirname "$RUNTIME_DB")"
mkdir -p "$(dirname "$RUNTIME_LEDGER")"

if [ ! -s "$RUNTIME_DB" ]; then
  if [ -s "$SEED_DB" ]; then
    cp "$SEED_DB" "$RUNTIME_DB"
    echo "Seeded runtime database from $SEED_DB"
  else
    echo "Seed database missing at $SEED_DB" >&2
    exit 1
  fi
fi

case "${SKILL0_ENV:-development}" in
  production|prod)
    if [ "$ALLOW_RUNTIME_INITIALIZE" = "true" ]; then
      echo "Runtime initialization must be disabled in production; restore a verified ledger instead" >&2
      exit 1
    fi
    if [ ! -s "$RUNTIME_LEDGER" ]; then
      echo "Runtime ledger is missing at $RUNTIME_LEDGER; restore a verified ledger before production startup" >&2
      exit 1
    fi
    ;;
esac

python - "$RUNTIME_LEDGER" "$RUNTIME_JOURNAL_MODE" "$HITL_TTL_SECONDS" <<'PY'
import sys

from runtime.ledger import RuntimeLedger

path, journal_mode, ttl_seconds = sys.argv[1:]
with RuntimeLedger(
    path,
    journal_mode=journal_mode,
    hitl_ttl_seconds=int(ttl_seconds),
):
    pass
PY

case "${SKILL0_ENV:-development}" in
  production|prod)
    python /app/scripts/runtime_doctor.py --production --json
    ;;
esac

exec "$@"
