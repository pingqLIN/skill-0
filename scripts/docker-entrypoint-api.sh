#!/bin/sh
set -eu

RUNTIME_DB="${SKILL0_DB_PATH:-/app/data/skills.db}"
SEED_DB="/app/bootstrap/skills.db"

mkdir -p "$(dirname "$RUNTIME_DB")"

if [ ! -s "$RUNTIME_DB" ]; then
  if [ -s "$SEED_DB" ]; then
    cp "$SEED_DB" "$RUNTIME_DB"
    echo "Seeded runtime database from $SEED_DB"
  else
    echo "Seed database missing at $SEED_DB" >&2
    exit 1
  fi
fi

exec "$@"
