from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "examples" / "infrastructure" / "environment-manifest.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "environment-manifest.schema.json"
DOC_PATH = REPO_ROOT / "docs" / "policies" / "environment-separation.md"
README_PATH = REPO_ROOT / "README.md"
WRANGLER_CONFIG_PATH = REPO_ROOT / "workers" / "control-api" / "wrangler.toml"


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

    assert "docs/policies/environment-separation.md" in readme


def test_wrangler_environments_match_manifest_resources() -> None:
    manifest = load_json(MANIFEST_PATH)
    wrangler = tomllib.loads(WRANGLER_CONFIG_PATH.read_text(encoding="utf-8"))

    for environment in manifest["environments"]:
        env_name = environment["name"]
        config = wrangler if env_name == "dev" else wrangler["env"][env_name]

        cloudflare = environment["cloudflare"]
        vars_section = config["vars"]
        d1 = config["d1_databases"][0]
        r2_by_binding = {entry["binding"]: entry for entry in config["r2_buckets"]}
        queues = config["queues"]
        queue_consumer = queues["consumers"][0]
        vectorize_by_binding = {entry["binding"]: entry for entry in config["vectorize"]}

        assert config["name"] == cloudflare["worker_name"]
        assert vars_section["ENVIRONMENT"] == env_name
        assert vars_section["AI_GATEWAY_ID"] == cloudflare["ai_gateway_id"]
        assert d1["database_name"] == cloudflare["control_d1_database"]
        assert (
            r2_by_binding["SCAS_KNOWLEDGE_BUCKET"]["bucket_name"]
            == cloudflare["knowledge_r2_bucket"]
        )
        assert r2_by_binding["SCAS_MEMORY_BUCKET"]["bucket_name"] == cloudflare["memory_r2_bucket"]
        assert queues["producers"][0]["queue"] == cloudflare["ingest_queue"]
        assert queue_consumer["queue"] == cloudflare["ingest_queue"]
        assert queue_consumer["dead_letter_queue"] == cloudflare["ingest_dead_letter_queue"]
        assert vectorize_by_binding["SCAS_KNOWLEDGE_INDEX"]["index_name"] == cloudflare[
            "knowledge_vectorize_index"
        ]
        assert vectorize_by_binding["SCAS_MEMORY_INDEX"]["index_name"] == cloudflare[
            "memory_vectorize_index"
        ]

