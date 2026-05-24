from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "examples" / "infrastructure" / "environment-manifest.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "environment-manifest.schema.json"
DOC_PATH = REPO_ROOT / "docs" / "environment-separation.md"
README_PATH = REPO_ROOT / "README.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_environment_manifest_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    manifest = load_json(MANIFEST_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)


def test_environment_manifest_defines_required_environments() -> None:
    manifest = load_json(MANIFEST_PATH)
    environments = {environment["name"]: environment for environment in manifest["environments"]}

    assert set(environments) == {"dev", "staging", "prod"}
    assert environments["dev"]["release_role"] == "development"
    assert environments["staging"]["release_role"] == "rehearsal"
    assert environments["prod"]["release_role"] == "production"


def test_persistent_environment_resources_do_not_overlap() -> None:
    manifest = load_json(MANIFEST_PATH)

    cloudflare_fields = (
        "worker_name",
        "control_d1_database",
        "knowledge_r2_bucket",
        "memory_r2_bucket",
        "knowledge_vectorize_index",
        "memory_vectorize_index",
        "config_kv_namespace",
        "ingest_queue",
        "ingest_dead_letter_queue",
        "ai_gateway_id",
    )
    hetzner_fields = (
        "runtime_database",
        "runtime_owner_role",
        "artifact_root",
    )

    for field in cloudflare_fields:
        values = [environment["cloudflare"][field] for environment in manifest["environments"]]
        assert len(values) == len(set(values)), f"Cloudflare resource overlaps: {field}"

    for field in hetzner_fields:
        values = [environment["hetzner"][field] for environment in manifest["environments"]]
        assert len(values) == len(set(values)), f"Hetzner resource overlaps: {field}"


def test_environment_resource_names_use_environment_suffixes() -> None:
    manifest = load_json(MANIFEST_PATH)

    for environment in manifest["environments"]:
        env_name = environment["name"]
        for resource_name in environment["cloudflare"].values():
            assert f"-{env_name}" in resource_name or resource_name.endswith(f"-{env_name}-dlq")
        if env_name != "dev":
            assert environment["hetzner"]["runtime_database"].endswith(f"_{env_name}")
            assert environment["hetzner"]["runtime_owner_role"].endswith(f"_{env_name}_app")
        assert environment["hetzner"]["artifact_root"].endswith(f"/{env_name}")


def test_environment_docs_are_linked_from_readme() -> None:
    assert DOC_PATH.exists()
    readme = README_PATH.read_text(encoding="utf-8")

    assert "docs/environment-separation.md" in readme
