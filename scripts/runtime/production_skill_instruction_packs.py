from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    BUILTIN_SKILL_HANDLER_REGISTRY,
    SkillHandlerRegistry,
)

CONTRACT_VERSION = "0.1.0"
GENERATED_BY = "scripts/runtime/production_skill_instruction_packs.py"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODULES_DIR = REPO_ROOT / "registry" / "modules"
DEFAULT_OUTPUT = REPO_ROOT / "examples" / "runtime" / "production-skill-instruction-packs.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "production-skill-instruction-packs.schema.json"


class ProductionSkillInstructionPackError(ValueError):
    """Raised when production skill instruction packs are invalid or stale."""


def build_instruction_packs(
    *,
    modules_dir: Path = DEFAULT_MODULES_DIR,
    registry: SkillHandlerRegistry = BUILTIN_SKILL_HANDLER_REGISTRY,
) -> dict[str, Any]:
    skill_modules = _load_runtime_skill_modules(modules_dir)
    instruction_packs: list[dict[str, Any]] = []
    missing_handlers: list[str] = []

    for module_path, module in skill_modules:
        skill_name = str(module["name"])
        skill_version = str(module["version"])
        handler = registry.handler_for(skill_name, skill_version)
        if handler is None:
            missing_handlers.append(f"{skill_name}@{skill_version}")
            continue

        instruction_packs.append(
            {
                "skill_name": skill_name,
                "skill_version": skill_version,
                "runtime_role": str(module["runtime_role"]),
                "description": str(module["description"]),
                "module_path": _repo_path(module_path),
                "triggers": [str(value) for value in module.get("triggers", [])],
                "required_tools": [str(value) for value in module.get("required_tools", [])],
                "optional_tools": [str(value) for value in module.get("optional_tools", [])],
                "required_policies": [str(value) for value in module.get("policies", [])],
                "required_validators": [str(value) for value in module.get("validators", [])],
                "handler": handler.descriptor(),
                "test_evidence": {
                    "module_tests": _module_tests(module),
                    "runtime_tests": list(handler.test_coverage),
                },
                "execution_instructions": _execution_instructions(
                    skill_name,
                    skill_version,
                    module,
                ),
                "live_run_requirements": _live_run_requirements(skill_name),
            }
        )

    instruction_packs.sort(key=lambda item: (item["skill_name"], item["skill_version"]))
    payload: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "generated_by": GENERATED_BY,
        "status": "failed" if missing_handlers else "passed",
        "summary": {
            "pack_count": len(instruction_packs),
            "production_required_skill_count": len(skill_modules),
            "missing_handler_count": len(missing_handlers),
        },
        "instruction_packs": instruction_packs,
    }
    if missing_handlers:
        payload["missing_handlers"] = missing_handlers
    return payload


def validate_instruction_packs(
    payload: Mapping[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
) -> None:
    schema = _load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(payload)
    except Exception as exc:  # pragma: no cover - wrapper for deterministic CLI errors
        raise ProductionSkillInstructionPackError(str(exc)) from exc


def assert_instruction_packs_current(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    modules_dir: Path = DEFAULT_MODULES_DIR,
    registry: SkillHandlerRegistry = BUILTIN_SKILL_HANDLER_REGISTRY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    expected = build_instruction_packs(modules_dir=modules_dir, registry=registry)
    validate_instruction_packs(expected, schema_path=schema_path)
    if expected["status"] != "passed":
        missing = ", ".join(expected.get("missing_handlers", []))
        raise ProductionSkillInstructionPackError(
            "production skill instruction packs have missing handlers: " + missing
        )

    try:
        committed = _load_json(output_path)
    except FileNotFoundError as exc:
        raise ProductionSkillInstructionPackError(
            f"production skill instruction packs are missing: {_repo_path(output_path)}"
        ) from exc

    validate_instruction_packs(committed, schema_path=schema_path)
    if committed != expected:
        raise ProductionSkillInstructionPackError(
            "production skill instruction packs are stale; run "
            "`python scripts/runtime/production_skill_instruction_packs.py` and commit the result"
        )
    return expected


def write_instruction_packs(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    modules_dir: Path = DEFAULT_MODULES_DIR,
    registry: SkillHandlerRegistry = BUILTIN_SKILL_HANDLER_REGISTRY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    payload = build_instruction_packs(modules_dir=modules_dir, registry=registry)
    validate_instruction_packs(payload, schema_path=schema_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json_dump(payload), encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or validate production skill instruction packs.",
    )
    parser.add_argument("--modules-dir", type=Path, default=DEFAULT_MODULES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            payload = assert_instruction_packs_current(
                output_path=args.output,
                modules_dir=args.modules_dir,
                schema_path=args.schema,
            )
        else:
            payload = write_instruction_packs(
                output_path=args.output,
                modules_dir=args.modules_dir,
                schema_path=args.schema,
            )
        if args.print_json:
            print(_json_dump(payload), end="")
    except ProductionSkillInstructionPackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _load_runtime_skill_modules(modules_dir: Path) -> tuple[tuple[Path, dict[str, Any]], ...]:
    modules: list[tuple[Path, dict[str, Any]]] = []
    for module_path in sorted(modules_dir.rglob("module.json")):
        payload = _load_json(module_path)
        if payload.get("kind") != "skill":
            continue
        if str(payload.get("runtime_role", "runtime")) not in {"runtime", "shared"}:
            continue
        modules.append((module_path, payload))
    return tuple(
        sorted(
            modules,
            key=lambda item: (str(item[1]["name"]), str(item[1]["version"])),
        )
    )


def _module_tests(module: Mapping[str, Any]) -> list[str]:
    tests = module.get("tests", [])
    if isinstance(tests, Mapping):
        values: list[str] = []
        for field in ("contract", "runtime", "fixtures"):
            field_values = tests.get(field, [])
            if isinstance(field_values, list):
                values.extend(str(value) for value in field_values)
        return values
    if isinstance(tests, list):
        return [str(value) for value in tests]
    return []


def _execution_instructions(
    skill_name: str,
    skill_version: str,
    module: Mapping[str, Any],
) -> list[str]:
    task_types = ", ".join(str(value) for value in module["task_signals"]["task_types"])
    required_inputs = ", ".join(str(value) for value in module["task_signals"]["required_inputs"])
    return [
        (
            f"Compose a runtime profile that selects {skill_name}@{skill_version} "
            "through the standard analyzer -> composer control path."
        ),
        (
            f"Ensure task type is one of [{task_types}] and required inputs [{required_inputs}] "
            "are present before runtime execution starts."
        ),
        (
            "Run runtime loop execution and confirm emitted planner checkpoints include "
            f"handler binding evidence for {skill_name}@{skill_version}."
        ),
        (
            "Verify all required validators pass and persist non-secret evidence artifacts "
            "for release certification."
        ),
    ]


def _live_run_requirements(skill_name: str) -> list[str]:
    return [
        (
            "Provide a non-secret live gate run URL proving this handler executed in a "
            "production-like runtime flow."
        ),
        (
            "Persist sanitized evidence metadata that references the live run URL and "
            f"explicitly names {skill_name} as executed handler."
        ),
    ]


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ProductionSkillInstructionPackError(
            f"{_repo_path(path)} must contain a JSON object"
        )
    return parsed


def _json_dump(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
