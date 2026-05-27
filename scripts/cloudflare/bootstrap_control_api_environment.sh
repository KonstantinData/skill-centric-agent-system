#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: $0 <dev|staging|prod> [--seed]" >&2
  exit 1
fi

TARGET_ENVIRONMENT="$1"
SEED_CONTROL_PLANE="false"
if [ "${2:-}" = "--seed" ]; then
  SEED_CONTROL_PLANE="true"
fi

case "${TARGET_ENVIRONMENT}" in
  dev|staging|prod) ;;
  *)
    echo "Unsupported target environment: ${TARGET_ENVIRONMENT}" >&2
    exit 1
    ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WRANGLER_CONFIG="$REPO_ROOT/workers/control-api/wrangler.toml"

CONTROL_DB="scas-control-${TARGET_ENVIRONMENT}"
KNOWLEDGE_BUCKET="scas-knowledge-${TARGET_ENVIRONMENT}"
MEMORY_BUCKET="scas-memory-${TARGET_ENVIRONMENT}"
INGEST_QUEUE="scas-ingest-${TARGET_ENVIRONMENT}"
INGEST_DLQ="scas-ingest-${TARGET_ENVIRONMENT}-dlq"
KNOWLEDGE_INDEX="scas-knowledge-${TARGET_ENVIRONMENT}"
MEMORY_INDEX="scas-memory-${TARGET_ENVIRONMENT}"
SEED_PATH="$REPO_ROOT/examples/control-plane/${TARGET_ENVIRONMENT}-seed.sql"

echo "Creating Cloudflare resources for environment: ${TARGET_ENVIRONMENT}"
echo "Wrangler config: $WRANGLER_CONFIG"
echo

npx wrangler d1 create "${CONTROL_DB}" --config "$WRANGLER_CONFIG"
echo
echo "Copy the returned D1 database_id into workers/control-api/wrangler.toml (env-specific config section)."
echo

npx wrangler r2 bucket create "${KNOWLEDGE_BUCKET}" --config "$WRANGLER_CONFIG"
npx wrangler r2 bucket create "${MEMORY_BUCKET}" --config "$WRANGLER_CONFIG"
echo

npx wrangler kv namespace create SCAS_CONFIG --config "$WRANGLER_CONFIG"
echo
echo "Copy the returned KV namespace id into workers/control-api/wrangler.toml (env-specific config section)."
echo

npx wrangler queues create "${INGEST_QUEUE}" --config "$WRANGLER_CONFIG"
npx wrangler queues create "${INGEST_DLQ}" --config "$WRANGLER_CONFIG"
echo

npx wrangler vectorize create "${KNOWLEDGE_INDEX}" --dimensions=1536 --metric=cosine --config "$WRANGLER_CONFIG"
npx wrangler vectorize create "${MEMORY_INDEX}" --dimensions=1536 --metric=cosine --config "$WRANGLER_CONFIG"
npx wrangler vectorize create-metadata-index "${KNOWLEDGE_INDEX}" --property-name=scope_id --type=string --config "$WRANGLER_CONFIG"
npx wrangler vectorize create-metadata-index "${MEMORY_INDEX}" --property-name=memory_scope_id --type=string --config "$WRANGLER_CONFIG"
echo

npx wrangler d1 migrations apply "${CONTROL_DB}" --remote --config "$WRANGLER_CONFIG"
echo

if [ "${SEED_CONTROL_PLANE}" = "true" ]; then
  python "$REPO_ROOT/scripts/cloudflare/generate_control_plane_seed.py" --output "$SEED_PATH"
  npx wrangler d1 execute "${CONTROL_DB}" --remote --file "$SEED_PATH" --config "$WRANGLER_CONFIG" --yes
fi

echo
echo "Done for ${TARGET_ENVIRONMENT}."
