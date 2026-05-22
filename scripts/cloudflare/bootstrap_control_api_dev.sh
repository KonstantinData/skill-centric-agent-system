#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WRANGLER_CONFIG="$REPO_ROOT/workers/control-api/wrangler.toml"

echo "Creating Cloudflare dev resources for the Control API."
echo "Wrangler config: $WRANGLER_CONFIG"
echo

npx wrangler d1 create scas-control-dev --config "$WRANGLER_CONFIG"
echo
echo "Copy the returned D1 database_id into workers/control-api/wrangler.toml."
echo

npx wrangler r2 bucket create scas-knowledge-dev --config "$WRANGLER_CONFIG"
npx wrangler r2 bucket create scas-memory-dev --config "$WRANGLER_CONFIG"
echo

npx wrangler kv namespace create SCAS_CONFIG --config "$WRANGLER_CONFIG"
echo
echo "Copy the returned KV namespace id into workers/control-api/wrangler.toml."
echo

npx wrangler vectorize create scas-knowledge-dev --dimensions=1536 --metric=cosine --config "$WRANGLER_CONFIG"
npx wrangler vectorize create scas-memory-dev --dimensions=1536 --metric=cosine --config "$WRANGLER_CONFIG"
echo

npx wrangler d1 migrations apply scas-control-dev --local --config "$WRANGLER_CONFIG"
echo
echo "After the Cloudflare resource IDs are committed, run:"
echo "  npx wrangler d1 migrations apply scas-control-dev --remote --config workers/control-api/wrangler.toml"
echo "  npm run worker:types"
echo "  npm run worker:typecheck"
echo "  npm run worker:test"
echo "  npm run worker:check"
echo "  npm run worker:deploy:dev"
