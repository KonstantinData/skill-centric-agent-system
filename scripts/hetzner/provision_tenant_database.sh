#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  provision_tenant_database.sh

Environment:
  SCAS_TENANT_DB        Tenant PostgreSQL database. Default: tenant_das_kuechenhaus
  SCAS_TENANT_DB_OWNER  PostgreSQL owner/application role. Default: tenant_das_kuechenhaus_app

This script is idempotent and non-destructive. It creates or verifies one
tenant business database. It does not create SCAS memory storage.
USAGE
}

SCAS_TENANT_DB="${SCAS_TENANT_DB:-tenant_das_kuechenhaus}"
SCAS_TENANT_DB_OWNER="${SCAS_TENANT_DB_OWNER:-tenant_das_kuechenhaus_app}"

while [ "$#" -gt 0 ]; do
  case "$1" in
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

  if ! printf '%s' "$value" | grep -Eq '^tenant_[a-z][a-z0-9_]*$'; then
    echo "${name} must be a safe tenant PostgreSQL identifier, got: ${value}" >&2
    exit 2
  fi
}

psql_postgres() {
  sudo -u postgres psql -v ON_ERROR_STOP=1 "$@"
}

require_safe_identifier "SCAS_TENANT_DB" "$SCAS_TENANT_DB"
require_safe_identifier "SCAS_TENANT_DB_OWNER" "$SCAS_TENANT_DB_OWNER"

if ! psql_postgres -d postgres -Atc \
  "SELECT 1 FROM pg_roles WHERE rolname = '${SCAS_TENANT_DB_OWNER}'" | grep -qx '1'; then
  sudo -u postgres createuser "$SCAS_TENANT_DB_OWNER"
fi

if ! psql_postgres -d postgres -Atc \
  "SELECT 1 FROM pg_database WHERE datname = '${SCAS_TENANT_DB}'" | grep -qx '1'; then
  sudo -u postgres createdb --owner="$SCAS_TENANT_DB_OWNER" "$SCAS_TENANT_DB"
fi

psql_postgres -d postgres -c "
REVOKE ALL ON DATABASE \"${SCAS_TENANT_DB}\" FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE \"${SCAS_TENANT_DB}\" TO \"${SCAS_TENANT_DB_OWNER}\";
COMMENT ON DATABASE \"${SCAS_TENANT_DB}\" IS
  'SCAS tenant business/customer database. Not SCAS memory storage.';
"

psql_postgres -d "$SCAS_TENANT_DB" -c "
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA IF NOT EXISTS tenant AUTHORIZATION \"${SCAS_TENANT_DB_OWNER}\";
CREATE SCHEMA IF NOT EXISTS audit AUTHORIZATION \"${SCAS_TENANT_DB_OWNER}\";
COMMENT ON SCHEMA tenant IS
  'Tenant business and customer data schema. Not SCAS memory storage.';
COMMENT ON SCHEMA audit IS
  'Tenant-local business audit schema. Not SCAS memory storage.';
GRANT USAGE, CREATE ON SCHEMA tenant TO \"${SCAS_TENANT_DB_OWNER}\";
GRANT USAGE, CREATE ON SCHEMA audit TO \"${SCAS_TENANT_DB_OWNER}\";
ALTER DEFAULT PRIVILEGES FOR ROLE \"${SCAS_TENANT_DB_OWNER}\" IN SCHEMA tenant
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"${SCAS_TENANT_DB_OWNER}\";
ALTER DEFAULT PRIVILEGES FOR ROLE \"${SCAS_TENANT_DB_OWNER}\" IN SCHEMA tenant
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO \"${SCAS_TENANT_DB_OWNER}\";
ALTER DEFAULT PRIVILEGES FOR ROLE \"${SCAS_TENANT_DB_OWNER}\" IN SCHEMA audit
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO \"${SCAS_TENANT_DB_OWNER}\";
ALTER DEFAULT PRIVILEGES FOR ROLE \"${SCAS_TENANT_DB_OWNER}\" IN SCHEMA audit
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO \"${SCAS_TENANT_DB_OWNER}\";
"

echo "SCAS tenant PostgreSQL database ready"
echo "database=${SCAS_TENANT_DB}"
echo "owner=${SCAS_TENANT_DB_OWNER}"
echo "schemas=tenant,audit"
