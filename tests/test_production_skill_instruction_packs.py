from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.runtime.production_skill_instruction_packs import (
    ProductionSkillInstructionPackError,
    assert_instruction_packs_current,
    build_instruction_packs,
)
from scripts.runtime.production_skill_instruction_packs import (
    main as instruction_packs_cli_main,
)
from skill_centric_agent_system.runtime import (
    BUILTIN_SKILL_HANDLER_REGISTRY,
    SkillHandlerRegistry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = REPO_ROOT / "examples" / "modules"
OUTPUT_PATH = REPO_ROOT / "examples" / "runtime" / "production-skill-instruction-packs.json"
SCHEMA_PATH = REPO_ROOT / "schemas" / "production-skill-instruction-packs.schema.json"


def test_instruction_packs_manifest_is_current() -> None:
    payload = assert_instruction_packs_current(
        output_path=OUTPUT_PATH,
        modules_dir=MODULES_DIR,
        schema_path=SCHEMA_PATH,
    )

    assert payload["status"] == "passed"
    assert payload["summary"]["missing_handler_count"] == 0
    assert payload["summary"]["production_required_skill_count"] >= 1
    assert payload["summary"]["pack_count"] >= 1


def test_instruction_packs_fail_closed_when_handler_is_missing() -> None:
    handlers = tuple(
        handler
        for handler in BUILTIN_SKILL_HANDLER_REGISTRY.handlers()
        if handler.skill_name != "git-diff-analysis"
    )
    partial_registry = SkillHandlerRegistry(handlers)
    payload = build_instruction_packs(modules_dir=MODULES_DIR, registry=partial_registry)

    assert payload["status"] == "failed"
    assert "git-diff-analysis@0.1.0" in payload["missing_handlers"]
    assert payload["summary"]["missing_handler_count"] >= 1


def test_instruction_packs_cli_writes_and_checks_manifest(tmp_path: Path) -> None:
    output = tmp_path / "production-skill-instruction-packs.json"
    write_exit = instruction_packs_cli_main(
        [
            "--modules-dir",
            str(MODULES_DIR),
            "--output",
            str(output),
            "--schema",
            str(SCHEMA_PATH),
        ]
    )
    assert write_exit == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"

    check_exit = instruction_packs_cli_main(
        [
            "--modules-dir",
            str(MODULES_DIR),
            "--output",
            str(output),
            "--schema",
            str(SCHEMA_PATH),
            "--check",
        ]
    )
    assert check_exit == 0


def test_instruction_packs_check_fails_on_stale_manifest(tmp_path: Path) -> None:
    output = tmp_path / "stale-production-skill-instruction-packs.json"
    output.write_text(json.dumps({"status": "passed"}), encoding="utf-8")

    with pytest.raises(ProductionSkillInstructionPackError):
        assert_instruction_packs_current(
            output_path=output,
            modules_dir=MODULES_DIR,
            schema_path=SCHEMA_PATH,
        )
