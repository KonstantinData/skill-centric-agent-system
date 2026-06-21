from __future__ import annotations

import json
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_JSON_PATH = REPO_ROOT / "package.json"
WRANGLER_CONFIG_PATH = REPO_ROOT / "workers" / "control-api" / "wrangler.toml"
DKH_SITE_WRANGLER_CONFIG_PATH = (
    REPO_ROOT / "workers" / "es-daskuechenhaus-site" / "wrangler.toml"
)
DKH_SITE_WORKER_SOURCE_PATH = (
    REPO_ROOT / "workers" / "es-daskuechenhaus-site" / "src" / "index.ts"
)
DKH_SITE_ACCESS_SCRIPT_PATH = (
    REPO_ROOT / "scripts" / "cloudflare" / "es_daskuechenhaus_access.py"
)
WORKER_SOURCE_PATH = REPO_ROOT / "workers" / "control-api" / "src" / "index.ts"
WORKER_TEST_PATH = REPO_ROOT / "workers" / "control-api" / "test" / "index.test.ts"
VITEST_CONFIG_PATH = REPO_ROOT / "workers" / "control-api" / "vitest.config.ts"
CONTROL_API_DOC_PATH = REPO_ROOT / "docs" / "reference" / "cloudflare" / "control-api.md"
BOOTSTRAP_SCRIPT_PATH = (
    REPO_ROOT / "scripts" / "cloudflare" / "bootstrap_control_api_dev.sh"
)
BOOTSTRAP_ENV_SCRIPT_PATH = (
    REPO_ROOT / "scripts" / "cloudflare" / "bootstrap_control_api_environment.sh"
)
AI_GATEWAY_LIVE_SMOKE_SCRIPT_PATH = (
    REPO_ROOT / "scripts" / "cloudflare" / "ai_gateway_live_smoke.py"
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
    assert (
        scripts["dkh-site:typecheck"]
        == "tsc --noEmit -p workers/es-daskuechenhaus-site/tsconfig.json"
    )
    assert (
        scripts["dkh-site:check"]
        == "wrangler deploy --dry-run --config workers/es-daskuechenhaus-site/wrangler.toml"
    )


def test_es_daskuechenhaus_site_worker_is_private_route_scaffold() -> None:
    config = load_toml(DKH_SITE_WRANGLER_CONFIG_PATH)
    source = load_text(DKH_SITE_WORKER_SOURCE_PATH)

    assert config["name"] == "es-daskuechenhaus-site"
    assert config["main"] == "src/index.ts"
    assert config["workers_dev"] is False
    assert config["preview_urls"] is False
    assert config["vars"] == {
        "DKH_ADMIN_API_BASE_URL": (
            "https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api"
        )
    }
    assert config["routes"] == [
        {
            "pattern": "es-daskuechenhaus.de/*",
            "zone_name": "es-daskuechenhaus.de",
        },
        {
            "pattern": "www.es-daskuechenhaus.de/*",
            "zone_name": "es-daskuechenhaus.de",
        }
    ]

    assert 'url.pathname === "/health"' in source
    assert 'url.pathname === "/index.php"' in source
    assert 'url.pathname === "/kunden.php"' in source
    assert 'url.pathname === "/aufgaben.php"' in source
    assert 'url.pathname === "/admin.php"' in source
    assert 'url.pathname.startsWith("/admin-api/")' in source
    assert 'url.pathname.startsWith("/overview-api/")' in source
    assert 'url.pathname.startsWith("/customers-api/")' in source
    assert "DKH_ADMIN_API_TOKEN" in source
    assert "DKH_ADMIN_API_BASE_URL" in source
    assert "DKH_TENANT_UI" in source
    assert '"sota-2026-tenant-crm"' in source
    assert "assets/images/daskuechenhaus/logo_daskuechenhaus.png" in source
    assert 'logoRoute: "/tenant-assets/daskuechenhaus/logo.svg"' in source
    assert 'url.pathname.startsWith("/tenant-assets/")' in source
    assert "serveTenantAsset" in source
    assert 'logoPath.startsWith("assets/images/daskuechenhaus/")' in source
    assert "renderTenantThemeVars(DKH_TENANT_UI)" in source
    assert "renderTenantLogo(DKH_TENANT_UI)" in source
    assert "LOGO_MARKUP" not in source
    assert "svg.logo" not in source
    assert 'url.pathname.replace(/^\\/admin-api/, "/admin")' in source
    assert 'url.pathname.replace(/^\\/overview-api/, "/overview")' in source
    assert 'url.pathname.replace(/^\\/customers-api/, "/customers")' in source
    assert 'location' in source
    assert "Uebersicht" in source
    assert "CRM Steuerung" in source
    assert "Entscheidungszentrale" in source
    assert "Jetzt bearbeiten" in source
    assert "Kundenfortschritt" in source
    assert "SCAS Kontrolle" in source
    assert "Audit Trail" in source
    assert "Command Center" in source
    assert "renderCommandCenter" in source
    assert "renderDecisionQueue" in source
    assert "renderCustomerFocus" in source
    assert "renderScasReviewQueue" in source
    assert "renderAuditTrail" in source
    assert "Naechste Aktion" in source
    assert 'id="command-search"' in source
    assert 'name="q"' in source
    assert "customerMatchesQuery" in source
    assert "SCAS" in source
    assert "Ausfuehrung nur mit Bestaetigung" in source
    assert "filter-note" in source
    assert "Heute arbeiten" in source
    assert "Team & Termine" in source
    assert "Auslastung und Termine" in source
    assert "Kunde anlegen" in source
    assert "Kunden, Kontaktdaten, Verantwortlichkeiten" in source
    assert "Aufgabe anlegen" in source
    assert "E-Mail-Eingang" in source
    assert "Zuordnung bestaetigen" in source
    assert "Ablehnen" not in source
    assert "In Papierkorb" in source
    assert "Archivieren" in source
    assert "customer-case-options" in source
    assert 'name="customer_case_search"' in source
    assert 'action="/overview-api/emails/suggestions/${suggestion.id}/accept?return_to=' in source
    assert "Kein Treffer" in source
    assert "Instrumententafel" not in source
    assert "Kontrollverlust" not in source
    assert "Was jetzt kippen kann" not in source
    assert "Funkverkehr" not in source
    assert "Flugplan" not in source
    assert "Blackbox" not in source
    assert "Sonntag ist nicht als Arbeitstag vorgesehen" in source
    assert "modal users-modal" in source
    assert "modal settings-modal" in source
    assert "modal integrations-modal" in source
    assert "Mitarbeiter anlegen" in source
    assert "Konstantin Milonas" not in source
    assert "Verkauf" in source
    assert "Cloudflare Subject" not in source
    assert "Neuer Mitarbeiter" not in source
    assert "Worker eine gesicherte API" not in source
    assert 'id="admin-workdays"' not in source
    assert 'for="admin-workdays"' not in source
    assert 'id="employee-roles"' in source
    assert 'id="employee-workdays"' in source
    assert "employee-roles-panel" in source
    assert "employee-workdays-panel" in source
    assert "Mitarbeiteruebersicht" in source
    assert 'method="post"' in source
    assert 'href="/admin.php?modal=users&edit=${user.id}"' in source
    assert "fetchAdminState" in source
    assert "proxyAdminApi" in source
    assert "morning_start_time_" in source
    assert "afternoon_end_time_" in source
    assert 'name="department"' in source
    assert 'name="is_active"' in source
    assert 'name="external_identity_provider"' in source
    assert 'name="company_name"' in source
    assert 'name="secret_reference"' in source
    assert "SECURITY_HEADERS" in source
    assert "default-src 'none'" in source
    assert "x-robots-tag" in source


def test_es_daskuechenhaus_access_script_requires_explicit_allow_list() -> None:
    script = load_text(DKH_SITE_ACCESS_SCRIPT_PATH)

    assert "DKH_CLOUDFLARE_ACCOUNT_ID" in script
    assert "DKH_CLOUDFLARE_ZONE_ID" in script
    assert "DKH_CLOUDFLARE_API_TOKEN" in script
    assert "allowed-emails" in script
    assert "allowed_emails is required when --apply is used" in script
    assert "PRIMARY_HOSTNAME" in script
    assert "access_app_name" in script
    assert '"app_launcher_visible": True' in script
    assert "100::" in script
    assert "/dns_records" in script
    assert "/access/apps" in script
    assert "mfa_config" in script
    assert "security_key" in script
    assert "totp" in script


def test_wrangler_config_defines_control_api_bindings() -> None:
    config = load_toml(WRANGLER_CONFIG_PATH)

    assert config["name"] == "scas-control-api-dev"
    assert config["main"] == "src/index.ts"
    assert config["compatibility_date"] == "2026-05-20"
    assert config["compatibility_flags"] == ["nodejs_compat"]
    assert config["vars"] == {
        "ENVIRONMENT": "dev",
        "AI_GATEWAY_ACCOUNT_ID": "unset",
        "AI_GATEWAY_ID": "scas-ai-gateway-dev-run",
    }

    d1_bindings = {binding["binding"]: binding for binding in config["d1_databases"]}
    r2_bindings = {binding["binding"]: binding for binding in config["r2_buckets"]}
    kv_bindings = {binding["binding"]: binding for binding in config["kv_namespaces"]}
    vectorize_bindings = {binding["binding"]: binding for binding in config["vectorize"]}
    queue_producers = {binding["binding"]: binding for binding in config["queues"]["producers"]}
    queue_consumers = {binding["queue"]: binding for binding in config["queues"]["consumers"]}

    assert d1_bindings["SCAS_CONTROL_DB"]["database_name"] == "scas-control-dev"
    assert d1_bindings["SCAS_CONTROL_DB"]["migrations_dir"] == "../../migrations/cloudflare/d1"
    assert r2_bindings["SCAS_KNOWLEDGE_BUCKET"]["bucket_name"] == "scas-knowledge-dev"
    assert r2_bindings["SCAS_MEMORY_BUCKET"]["bucket_name"] == "scas-memory-dev"
    assert "SCAS_CONFIG" in kv_bindings
    assert queue_producers["SCAS_INGEST_QUEUE"]["queue"] == "scas-ingest-dev"
    assert queue_consumers["scas-ingest-dev"]["max_retries"] == 3
    assert queue_consumers["scas-ingest-dev"]["dead_letter_queue"] == "scas-ingest-dev-dlq"
    assert vectorize_bindings["SCAS_KNOWLEDGE_INDEX"]["index_name"] == "scas-knowledge-dev"
    assert vectorize_bindings["SCAS_MEMORY_INDEX"]["index_name"] == "scas-memory-dev"


def test_worker_source_exposes_health_and_composition_context_routes() -> None:
    source = load_text(WORKER_SOURCE_PATH)

    assert 'url.pathname === "/health"' in source
    assert 'url.pathname === "/composition/context"' in source
    assert 'url.pathname.startsWith("/tenant-admin/tenants/")' in source
    assert 'url.pathname === "/retrieval/context"' in source
    assert 'url.pathname === "/ai-gateway/openai/chat/completions"' in source
    assert "loadRegistryModules" in source
    assert "registry_unavailable" in source
    assert "request_body_too_large" in source
    assert "queryVectorize" in source
    assert "ai_gateway_not_configured" in source
    assert "processEmbeddingIndexMessage" in source
    assert "SCAS_INGEST_QUEUE" in source


def test_worker_vitest_scaffold_is_present() -> None:
    vitest_config = load_text(VITEST_CONFIG_PATH)
    worker_test = load_text(WORKER_TEST_PATH)

    assert "@cloudflare/vitest-pool-workers" in vitest_config
    assert "workers/control-api/test/**/*.test.ts" in vitest_config
    assert 'import { env, reset } from "cloudflare:test"' in worker_test
    assert 'import worker from "../src/index"' in worker_test
    assert "composition_status" in worker_test


def test_control_api_docs_include_d1_bootstrap_and_deploy_sequence() -> None:
    docs = load_text(CONTROL_API_DOC_PATH)
    script = load_text(BOOTSTRAP_SCRIPT_PATH)
    env_script = load_text(BOOTSTRAP_ENV_SCRIPT_PATH)

    assert "npx wrangler d1 create scas-control-dev" in docs
    assert "npx wrangler d1 migrations apply scas-control-dev --local" in docs
    assert "npx wrangler d1 migrations apply scas-control-dev --remote" in docs
    assert "npx wrangler r2 bucket create scas-knowledge-dev" in docs
    assert "npx wrangler kv namespace create SCAS_CONFIG" in docs
    assert "npx wrangler queues create scas-ingest-dev" in docs
    assert "npx wrangler vectorize create scas-knowledge-dev" in docs
    assert "npx wrangler vectorize create-metadata-index scas-knowledge-dev" in docs
    assert "npx wrangler secret put OPENAI_API_KEY" in docs
    assert "npx wrangler secret put AI_GATEWAY_AUTH_TOKEN" in docs
    assert "npx wrangler secret put CONTROL_API_COMPOSITION_TOKEN" in docs
    assert "npm run worker:deploy:dev" in docs
    assert "bootstrap_control_api_environment.sh\" dev --seed" in script
    assert 'Usage: $0 <dev|staging|prod> [--seed]' in env_script
    assert "npx wrangler d1 create \"${CONTROL_DB}\"" in env_script
    assert "npx wrangler queues create \"${INGEST_QUEUE}\"" in env_script
    assert "npx wrangler vectorize create \"${KNOWLEDGE_INDEX}\"" in env_script
    assert "python \"$REPO_ROOT/scripts/cloudflare/generate_control_plane_seed.py\"" in env_script


def test_ci_runs_worker_checks_and_has_manual_dev_deploy_gate() -> None:
    workflow = load_text(CI_WORKFLOW_PATH)

    assert "deploy_control_api_dev:" in workflow
    assert "npm ci" in workflow
    assert "npm run worker:types" in workflow
    assert "npm run worker:typecheck" in workflow
    assert "npm run worker:test" in workflow
    assert "npm run worker:check" in workflow
    assert "inputs.deploy_control_api_dev == true" in workflow
    assert "npx wrangler deploy" in workflow
    assert "--secrets-file" in workflow


def test_ai_gateway_live_smoke_script_is_documented_and_uses_control_api_route() -> None:
    docs = load_text(CONTROL_API_DOC_PATH)
    script = load_text(AI_GATEWAY_LIVE_SMOKE_SCRIPT_PATH)

    assert "scripts/cloudflare/ai_gateway_live_smoke.py" in docs
    assert "/ai-gateway/openai/chat/completions" in script
    assert "SCAS_CONTROL_API_TOKEN" in script
    assert "choices" in script
