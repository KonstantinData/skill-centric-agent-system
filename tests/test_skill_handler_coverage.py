from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.runtime.skill_handler_coverage import (
    build_coverage_manifest,
)
from scripts.runtime.skill_handler_coverage import (
    main as skill_handler_coverage_main,
)
from skill_centric_agent_system.runtime import SkillHandlerRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = REPO_ROOT / "examples" / "modules"
MANIFEST_PATH = REPO_ROOT / "examples" / "runtime" / "skill-handler-coverage.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "skill-handler-coverage.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_skill_handler_coverage_manifest_matches_schema() -> None:
    schema = load_json(SCHEMA_PATH)
    manifest = load_json(MANIFEST_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)


def test_skill_handler_coverage_manifest_is_current() -> None:
    assert load_json(MANIFEST_PATH) == build_coverage_manifest(modules_dir=MODULES_DIR)


def test_skill_handler_coverage_fails_closed_for_missing_required_handler() -> None:
    manifest = build_coverage_manifest(
        modules_dir=MODULES_DIR,
        registry=SkillHandlerRegistry(()),
    )

    assert manifest["coverage_status"] == "failed"
    assert manifest["summary"]["missing_handler_count"] == 6
    assert {
        skill["coverage_status"]
        for skill in manifest["skills"]
        if skill["production_required"]
    } == {"missing_handler"}


def test_skill_handler_coverage_cli_check_passes() -> None:
    assert skill_handler_coverage_main(["--check"]) == 0
