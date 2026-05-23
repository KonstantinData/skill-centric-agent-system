from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from skill_centric_agent_system.control_plane import build_seed_records, generate_seed_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = REPO_ROOT / "examples" / "modules"
MODULE_SCHEMA_PATH = REPO_ROOT / "schemas" / "module.schema.json"
DEV_SEED_SQL_PATH = REPO_ROOT / "examples" / "control-plane" / "dev-seed.sql"
D1_MIGRATION_DIR = REPO_ROOT / "migrations" / "cloudflare" / "d1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def create_d1_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    for migration_path in sorted(D1_MIGRATION_DIR.glob("*.sql")):
        connection.executescript(migration_path.read_text(encoding="utf-8"))
    return connection


def module_paths() -> list[Path]:
    return sorted(MODULES_DIR.glob("*.json"))


def test_seed_source_modules_match_module_schema() -> None:
    module_schema = load_json(MODULE_SCHEMA_PATH)
    validator = Draft202012Validator(module_schema)

    for module_path in module_paths():
        validator.validate(load_json(module_path))


def test_seed_records_include_module_dependencies_and_policy_scopes() -> None:
    seed = build_seed_records(module_paths())
    module_names = {module["name"] for module in seed.modules}

    assert module_names == {
        "architecture-docs",
        "coding-guidelines",
        "filesystem-read",
        "filesystem-list",
        "general-output-contract",
        "general-task-summary",
        "git-diff-analysis",
        "git-read",
        "no-destructive-commands",
        "project-memory",
        "repository-readonly",
        "research-context-synthesis",
        "research-output-contract",
        "require-file-references",
        "review-findings-contract",
        "task-execution-output-contract",
        "task-execution-planning",
        "test-runner",
    }
    assert len(seed.module_versions) == len(seed.modules)
    assert len(seed.module_selection_metadata) == len(seed.modules)
    assert len(seed.module_dependencies) == 25
    assert len(seed.policy_bindings) == 6
    assert len(seed.scope_bindings) == 4


def test_committed_dev_seed_sql_is_generated_from_module_contracts() -> None:
    expected_sql = generate_seed_sql(build_seed_records(module_paths()))

    assert DEV_SEED_SQL_PATH.read_text(encoding="utf-8") == expected_sql


def test_generated_seed_sql_is_valid_and_idempotent_d1_data() -> None:
    seed_sql = generate_seed_sql(build_seed_records(module_paths()))

    with create_d1_connection() as connection:
        connection.executescript(seed_sql)
        connection.executescript(seed_sql)

        module_count = connection.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        version_count = connection.execute("SELECT COUNT(*) FROM module_versions").fetchone()[0]
        metadata_count = connection.execute(
            "SELECT COUNT(*) FROM module_selection_metadata"
        ).fetchone()[0]
        dependency_count = connection.execute(
            "SELECT COUNT(*) FROM module_dependencies"
        ).fetchone()[0]
        policy_binding_count = connection.execute(
            "SELECT COUNT(*) FROM policy_bindings"
        ).fetchone()[0]
        scope_binding_count = connection.execute(
            "SELECT COUNT(*) FROM scope_bindings"
        ).fetchone()[0]
        missing_current_versions = connection.execute(
            """
            SELECT COUNT(*)
            FROM modules AS m
            LEFT JOIN module_versions AS mv
              ON mv.id = m.current_version_id
              AND mv.module_id = m.id
            WHERE mv.id IS NULL
            """
        ).fetchone()[0]
        wrong_dependency_kinds = connection.execute(
            """
            SELECT COUNT(*)
            FROM module_dependencies AS dep
            INNER JOIN modules AS dependency
              ON dependency.id = dep.dependency_id
            WHERE dependency.kind != dep.dependency_kind
            """
        ).fetchone()[0]

    assert module_count == 18
    assert version_count == 18
    assert metadata_count == 18
    assert dependency_count == 25
    assert policy_binding_count == 6
    assert scope_binding_count == 4
    assert missing_current_versions == 0
    assert wrong_dependency_kinds == 0
