from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "hetzner" / "provision_tenant_database.sh"
ADR_PATH = REPO_ROOT / "docs" / "adr" / "0011-tenant-postgresql-databases.md"
INFRA_BOUNDARY_PATH = REPO_ROOT / "docs" / "policies" / "infrastructure-boundary.md"
DASKUECHENHAUS_RUNBOOK_PATH = (
    REPO_ROOT / "docs" / "runbooks" / "daskuechenhaus-tenant-onboarding.md"
)


def load_script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_tenant_database_provisioning_script_exists() -> None:
    assert SCRIPT_PATH.exists()


def test_tenant_database_provisioning_defaults_to_daskuechenhaus() -> None:
    script = load_script()

    assert 'SCAS_TENANT_DB="${SCAS_TENANT_DB:-tenant_das_kuechenhaus}"' in script
    assert (
        'SCAS_TENANT_DB_OWNER="${SCAS_TENANT_DB_OWNER:-tenant_das_kuechenhaus_app}"'
        in script
    )


def test_tenant_database_provisioning_is_non_destructive() -> None:
    script = load_script()

    forbidden_fragments = {
        "dropdb",
        "DROP DATABASE",
        "rm -rf",
        "TRUNCATE",
        "DELETE FROM",
    }

    for fragment in forbidden_fragments:
        assert fragment not in script


def test_tenant_database_provisioning_enforces_tenant_identifier_scope() -> None:
    script = load_script()

    assert "require_safe_identifier \"SCAS_TENANT_DB\"" in script
    assert "require_safe_identifier \"SCAS_TENANT_DB_OWNER\"" in script
    assert "^tenant_[a-z][a-z0-9_]*$" in script


def test_tenant_database_provisioning_creates_database_role_and_schemas() -> None:
    script = load_script()

    assert "createuser \"$SCAS_TENANT_DB_OWNER\"" in script
    assert "createdb --owner=\"$SCAS_TENANT_DB_OWNER\" \"$SCAS_TENANT_DB\"" in script
    assert "REVOKE ALL ON DATABASE" in script
    assert "GRANT CONNECT, TEMPORARY ON DATABASE" in script
    assert "CREATE SCHEMA IF NOT EXISTS tenant" in script
    assert "CREATE SCHEMA IF NOT EXISTS audit" in script
    assert "REVOKE CREATE ON SCHEMA public FROM PUBLIC" in script


def test_tenant_database_docs_keep_memory_out_of_scope() -> None:
    script = load_script()
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ADR_PATH, INFRA_BOUNDARY_PATH, DASKUECHENHAUS_RUNBOOK_PATH)
    )
    normalized_docs = " ".join(docs.split())

    assert "not change the existing memory architecture" in normalized_docs
    assert "It does not change the separate Cloudflare memory" in normalized_docs
    assert "It does not change SCAS memory handling" in docs
    assert "It does not create SCAS memory storage." in script
