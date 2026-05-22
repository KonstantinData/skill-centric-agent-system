#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bootstrap_runtime_plane.sh [--rebuild] [--migration-file PATH] [--migrations-dir PATH]

Environment:
  SCAS_RUNTIME_DB        Database to create/use. Default: scas_runtime
  SCAS_RUNTIME_DB_OWNER  PostgreSQL owner role. Default: scas_runtime_app
  SCAS_RUNTIME_ROOT      Runtime artifact root. Default: /opt/scas/runtime

--rebuild drops only SCAS_RUNTIME_DB and SCAS_RUNTIME_ROOT before recreating them.
USAGE
}

SCAS_RUNTIME_DB="${SCAS_RUNTIME_DB:-scas_runtime}"
SCAS_RUNTIME_DB_OWNER="${SCAS_RUNTIME_DB_OWNER:-scas_runtime_app}"
SCAS_RUNTIME_ROOT="${SCAS_RUNTIME_ROOT:-/opt/scas/runtime}"
MIGRATIONS_DIR="/opt/scas/migrations/hetzner/postgres"
MIGRATION_FILE=""
REBUILD=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --rebuild)
      REBUILD=1
      shift
      ;;
    --migration-file)
      MIGRATION_FILE="${2:?missing value for --migration-file}"
      shift 2
      ;;
    --migrations-dir)
      MIGRATIONS_DIR="${2:?missing value for --migrations-dir}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

require_safe_identifier() {
  local name="$1"
  local value="$2"

  if ! printf '%s' "$value" | grep -Eq '^[a-z_][a-z0-9_]*$'; then
    echo "${name} must be a safe PostgreSQL identifier, got: ${value}" >&2
    exit 2
  fi
}

require_safe_runtime_root() {
  case "$SCAS_RUNTIME_ROOT" in
    /opt/scas/runtime|/opt/scas/runtime/*)
      ;;
    *)
      echo "SCAS_RUNTIME_ROOT must stay under /opt/scas/runtime" >&2
      exit 2
      ;;
  esac
}

psql_postgres() {
  sudo -u postgres psql -v ON_ERROR_STOP=1 "$@"
}

require_safe_identifier "SCAS_RUNTIME_DB" "$SCAS_RUNTIME_DB"
require_safe_identifier "SCAS_RUNTIME_DB_OWNER" "$SCAS_RUNTIME_DB_OWNER"
require_safe_runtime_root

if [ -n "$MIGRATION_FILE" ]; then
  if [ ! -f "$MIGRATION_FILE" ]; then
    echo "Migration file not found: ${MIGRATION_FILE}" >&2
    exit 2
  fi
else
  if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "Migrations directory not found: ${MIGRATIONS_DIR}" >&2
    exit 2
  fi
fi

if [ "$REBUILD" -eq 1 ]; then
  psql_postgres -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${SCAS_RUNTIME_DB}' AND pid <> pg_backend_pid();"
  sudo -u postgres dropdb --if-exists "$SCAS_RUNTIME_DB"
  rm -rf "$SCAS_RUNTIME_ROOT"
fi

if ! psql_postgres -d postgres -Atc \
  "SELECT 1 FROM pg_roles WHERE rolname = '${SCAS_RUNTIME_DB_OWNER}'" | grep -qx '1'; then
  sudo -u postgres createuser "$SCAS_RUNTIME_DB_OWNER"
fi

if ! psql_postgres -d postgres -Atc \
  "SELECT 1 FROM pg_database WHERE datname = '${SCAS_RUNTIME_DB}'" | grep -qx '1'; then
  sudo -u postgres createdb --owner="$SCAS_RUNTIME_DB_OWNER" "$SCAS_RUNTIME_DB"
fi

if [ -n "$MIGRATION_FILE" ]; then
  psql_postgres -d "$SCAS_RUNTIME_DB" -f "$MIGRATION_FILE"
else
  shopt -s nullglob
  migration_files=("$MIGRATIONS_DIR"/*.sql)
  shopt -u nullglob
  if [ "${#migration_files[@]}" -eq 0 ]; then
    echo "No migration files found in ${MIGRATIONS_DIR}" >&2
    exit 2
  fi
  for migration_file in "${migration_files[@]}"; do
    psql_postgres -d "$SCAS_RUNTIME_DB" -f "$migration_file"
  done
fi
psql_postgres -d "$SCAS_RUNTIME_DB" -c "
GRANT USAGE ON SCHEMA runtime TO \"${SCAS_RUNTIME_DB_OWNER}\";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA runtime TO \"${SCAS_RUNTIME_DB_OWNER}\";
ALTER DEFAULT PRIVILEGES IN SCHEMA runtime
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"${SCAS_RUNTIME_DB_OWNER}\";
"

install -d -m 750 "$SCAS_RUNTIME_ROOT"
install -d -m 750 "$SCAS_RUNTIME_ROOT/artifacts"
install -d -m 750 "$SCAS_RUNTIME_ROOT/tool_outputs"
install -d -m 750 "$SCAS_RUNTIME_ROOT/traces"
install -d -m 750 "$SCAS_RUNTIME_ROOT/logs"
install -d -m 750 "$SCAS_RUNTIME_ROOT/tmp"

cat > "$SCAS_RUNTIME_ROOT/README.txt" <<README
Skill-Centric Agent System runtime storage root.

Database: ${SCAS_RUNTIME_DB}
Schema: runtime
Migrations: ${MIGRATION_FILE:-$MIGRATIONS_DIR/*.sql}

This directory stores runtime artifacts only. Consolidated long-term memory is
written to Cloudflare through the validated memory feedback loop.
README

chmod 640 "$SCAS_RUNTIME_ROOT/README.txt"

echo "SCAS runtime plane ready"
echo "database=${SCAS_RUNTIME_DB}"
echo "root=${SCAS_RUNTIME_ROOT}"
