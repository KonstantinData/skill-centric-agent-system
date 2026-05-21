from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MIGRATION_PATH = (
    REPO_ROOT / "migrations" / "hetzner" / "postgres" / "0001_runtime_plane.sql"
)
BOOTSTRAP_SCRIPT_PATH = REPO_ROOT / "scripts" / "hetzner" / "bootstrap_runtime_plane.sh"


def load_runtime_migration() -> str:
    return RUNTIME_MIGRATION_PATH.read_text(encoding="utf-8")


def load_bootstrap_script() -> str:
    return BOOTSTRAP_SCRIPT_PATH.read_text(encoding="utf-8")


def test_hetzner_runtime_migration_exists() -> None:
    assert RUNTIME_MIGRATION_PATH.exists()


def test_hetzner_runtime_migration_creates_required_tables() -> None:
    migration = load_runtime_migration()
    required_tables = {
        "runtime.runtime_runs",
        "runtime.runtime_steps",
        "runtime.tool_invocations",
        "runtime.validation_results",
        "runtime.memory_candidates",
    }

    for table in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration


def test_hetzner_runtime_migration_enforces_runtime_contract_constraints() -> None:
    migration = load_runtime_migration()

    assert "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')" in migration
    assert "kind IN ('context', 'planner', 'executor', 'validator')" in migration
    assert "status IN ('passed', 'failed', 'warning')" in migration
    assert "sensitivity IN ('public', 'internal', 'confidential', 'secret')" in migration
    assert "validator_status IN ('pending', 'approved', 'rejected')" in migration
    assert (
        "policy_status IN ('pending', 'approved', 'rejected', 'needs_clarification')"
        in migration
    )
    assert "profile_version ~ '^[0-9]+\\.[0-9]+\\.[0-9]+$'" in migration


def test_hetzner_runtime_migration_keeps_cross_table_references_consistent() -> None:
    migration = load_runtime_migration()

    assert "FOREIGN KEY (run_id) REFERENCES runtime.runtime_runs (id)" in migration
    assert "FOREIGN KEY (step_id, run_id)" in migration
    assert "REFERENCES runtime.runtime_steps (id, run_id)" in migration
    assert "FOREIGN KEY (run_id, profile_id)" in migration
    assert "REFERENCES runtime.runtime_runs (id, profile_id)" in migration
    assert "FOREIGN KEY (source_step_id, run_id)" in migration


def test_hetzner_runtime_migration_adds_lookup_indexes() -> None:
    migration = load_runtime_migration()
    required_indexes = {
        "idx_runtime_runs_status_started",
        "idx_runtime_steps_run_index",
        "idx_tool_invocations_run_step",
        "idx_validation_results_validator_status",
        "idx_memory_candidates_scope_status",
    }

    for index in required_indexes:
        assert f"CREATE INDEX IF NOT EXISTS {index}" in migration


def test_bootstrap_script_rebuild_is_scoped_to_scas_runtime_resources() -> None:
    script = load_bootstrap_script()

    assert "SCAS_RUNTIME_DB=\"${SCAS_RUNTIME_DB:-scas_runtime}\"" in script
    assert "SCAS_RUNTIME_DB_OWNER=\"${SCAS_RUNTIME_DB_OWNER:-scas_runtime_app}\"" in script
    assert "SCAS_RUNTIME_ROOT=\"${SCAS_RUNTIME_ROOT:-/opt/scas/runtime}\"" in script
    assert "dropdb --if-exists \"$SCAS_RUNTIME_DB\"" in script
    assert "rm -rf \"$SCAS_RUNTIME_ROOT\"" in script
    assert "SCAS_RUNTIME_ROOT must stay under /opt/scas/runtime" in script


def test_bootstrap_script_applies_migration_and_creates_artifact_dirs() -> None:
    script = load_bootstrap_script()

    assert "psql_postgres -d \"$SCAS_RUNTIME_DB\" -f \"$MIGRATION_FILE\"" in script
    assert "GRANT USAGE ON SCHEMA runtime" in script
    assert "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA runtime" in script
    for directory in ("artifacts", "tool_outputs", "traces", "logs", "tmp"):
        assert f"\"$SCAS_RUNTIME_ROOT/{directory}\"" in script
