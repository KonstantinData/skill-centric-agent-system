from __future__ import annotations

import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON_PATH = REPO_ROOT / "package.json"
WRANGLER_CONFIG_PATH = REPO_ROOT / "workers" / "control-api" / "wrangler.toml"
WORKER_SOURCE_PATH = REPO_ROOT / "workers" / "control-api" / "src" / "index.ts"
WORKER_TEST_PATH = REPO_ROOT / "workers" / "control-api" / "test" / "index.test.ts"
VITEST_CONFIG_PATH = REPO_ROOT / "workers" / "control-api" / "vitest.config.ts"
CONTROL_API_DOC_PATH = REPO_ROOT / "docs" / "cloudflare" / "control-api.md"
BOOTSTRAP_SCRIPT_PATH = (
    REPO_ROOT / "scripts" / "cloudflare" / "bootstrap_control_api_dev.sh"
)
CI_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_toml(path: Path) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_worker_package_scripts_are_defined() -> None:
    package = load_json(PACKAGE_JSON_PATH)
    scripts = package["scripts"]

    assert scripts["worker:types"].startswith("wrangler types")
    assert scripts["worker:typecheck"] == "tsc --noEmit -p workers/control-api/tsconfig.json"
    assert scripts["worker:test"] == "vitest run --config workers/control-api/vitest.config.ts"
    assert (
        scripts["worker:check"]
        == "wrangler deploy --dry-run --config workers/control-api/wrangler.toml"
    )
    assert (
        scripts["worker:deploy:dev"]
        == "wrangler deploy --config workers/control-api/wrangler.toml"
    )


def test_wrangler_config_defines_control_api_bindings() -> None:
    config = load_toml(WRANGLER_CONFIG_PATH)

    assert config["name"] == "scas-control-api-dev"
    assert config["main"] == "src/index.ts"
    assert config["compatibility_date"] == "2026-05-20"
    assert config["compatibility_flags"] == ["nodejs_compat"]
    assert config["vars"] == {
        "ENVIRONMENT": "dev",
        "AI_GATEWAY_ACCOUNT_ID": "unset",
        "AI_GATEWAY_ID": "default",
    }

    d1_bindings = {binding["binding"]: binding for binding in config["d1_databases"]}
    r2_bindings = {binding["binding"]: binding for binding in config["r2_buckets"]}
    kv_bindings = {binding["binding"]: binding for binding in config["kv_namespaces"]}
    vectorize_bindings = {binding["binding"]: binding for binding in config["vectorize"]}

    assert d1_bindings["SCAS_CONTROL_DB"]["database_name"] == "scas-control-dev"
    assert d1_bindings["SCAS_CONTROL_DB"]["migrations_dir"] == "../../migrations/cloudflare/d1"
    assert r2_bindings["SCAS_KNOWLEDGE_BUCKET"]["bucket_name"] == "scas-knowledge-dev"
    assert r2_bindings["SCAS_MEMORY_BUCKET"]["bucket_name"] == "scas-memory-dev"
    assert "SCAS_CONFIG" in kv_bindings
    assert vectorize_bindings["SCAS_KNOWLEDGE_INDEX"]["index_name"] == "scas-knowledge-dev"
    assert vectorize_bindings["SCAS_MEMORY_INDEX"]["index_name"] == "scas-memory-dev"


def test_worker_source_exposes_health_and_composition_context_routes() -> None:
    source = load_text(WORKER_SOURCE_PATH)

    assert 'url.pathname === "/health"' in source
    assert 'url.pathname === "/composition/context"' in source
    assert 'url.pathname === "/retrieval/context"' in source
    assert 'url.pathname === "/ai-gateway/openai/chat/completions"' in source
    assert "loadRegistryModules" in source
    assert "registry_unavailable" in source
    assert "request_body_too_large" in source
    assert "queryVectorize" in source
    assert "ai_gateway_not_configured" in source


def test_worker_vitest_scaffold_is_present() -> None:
    vitest_config = load_text(VITEST_CONFIG_PATH)
    worker_test = load_text(WORKER_TEST_PATH)

    assert "@cloudflare/vitest-pool-workers" in vitest_config
    assert "workers/control-api/test/**/*.test.ts" in vitest_config
    assert 'import { SELF, env, reset } from "cloudflare:test"' in worker_test
    assert "composition_status" in worker_test


def test_control_api_docs_include_d1_bootstrap_and_deploy_sequence() -> None:
    docs = load_text(CONTROL_API_DOC_PATH)
    script = load_text(BOOTSTRAP_SCRIPT_PATH)

    assert "npx wrangler d1 create scas-control-dev" in docs
    assert "npx wrangler d1 migrations apply scas-control-dev --local" in docs
    assert "npx wrangler d1 migrations apply scas-control-dev --remote" in docs
    assert "npx wrangler r2 bucket create scas-knowledge-dev" in docs
    assert "npx wrangler kv namespace create SCAS_CONFIG" in docs
    assert "npx wrangler vectorize create scas-knowledge-dev" in docs
    assert "npx wrangler secret put OPENAI_API_KEY" in docs
    assert "npm run worker:deploy:dev" in docs
    assert "npx wrangler d1 create scas-control-dev" in script


def test_ci_runs_worker_checks_and_has_manual_dev_deploy_gate() -> None:
    workflow = load_text(CI_WORKFLOW_PATH)

    assert "deploy_control_api_dev:" in workflow
    assert "npm ci" in workflow
    assert "npm run worker:types" in workflow
    assert "npm run worker:typecheck" in workflow
    assert "npm run worker:test" in workflow
    assert "npm run worker:check" in workflow
    assert "inputs.deploy_control_api_dev == true" in workflow
    assert "npm run worker:deploy:dev" in workflow
