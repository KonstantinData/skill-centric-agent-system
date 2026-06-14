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
    SkillHandler,
    SkillHandlerRegistry,
)

CONTRACT_VERSION = "0.1.0"
GENERATED_BY = "scripts/runtime/skill_handler_coverage.py"
HANDLER_REGISTRY_REF = (
    "skill_centric_agent_system.runtime.skill_handlers.BUILTIN_SKILL_HANDLER_REGISTRY"
)
MODULE_GLOB = "registry/modules/**/module.json"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODULES_DIR = REPO_ROOT / "registry" / "modules"
DEFAULT_OUTPUT = REPO_ROOT / "examples" / "runtime" / "skill-handler-coverage.json"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "skill-handler-coverage.schema.json"


class SkillHandlerCoverageError(ValueError):
    """Raised when the skill handler coverage manifest is invalid or stale."""


def build_coverage_manifest(
    *,
    modules_dir: Path = DEFAULT_MODULES_DIR,
    registry: SkillHandlerRegistry = BUILTIN_SKILL_HANDLER_REGISTRY,
) -> dict[str, Any]:
    skill_modules = _load_skill_modules(modules_dir)
    skills = [
        _coverage_entry(
            module=module,
            module_path=module_path,
            handler=registry.handler_for(str(module["name"]), str(module["version"])),
        )
        for module_path, module in skill_modules
    ]
    missing_count = sum(
        1
        for skill in skills
        if skill["production_required"] and skill["coverage_status"] == "missing_handler"
    )
    covered_count = sum(1 for skill in skills if skill["coverage_status"] == "covered")

    return {
        "contract_version": CONTRACT_VERSION,
        "coverage_status": "passed" if missing_count == 0 else "failed",
        "generated_by": GENERATED_BY,
        "handler_registry": HANDLER_REGISTRY_REF,
        "module_glob": MODULE_GLOB,
        "summary": {
            "covered_skill_count": covered_count,
            "missing_handler_count": missing_count,
            "production_required_skill_count": sum(
                1 for skill in skills if skill["production_required"]
            ),
            "skill_count": len(skills),
        },
        "skills": skills,
    }


def validate_manifest(
    manifest: Mapping[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
) -> None:
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)


def assert_manifest_current(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    modules_dir: Path = DEFAULT_MODULES_DIR,
    registry: SkillHandlerRegistry = BUILTIN_SKILL_HANDLER_REGISTRY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    expected = build_coverage_manifest(modules_dir=modules_dir, registry=registry)
    validate_manifest(expected, schema_path=schema_path)
    if expected["coverage_status"] != "passed":
        missing = [
            f"{skill['skill_name']}@{skill['skill_version']}"
            for skill in expected["skills"]
            if skill["coverage_status"] == "missing_handler"
        ]
        raise SkillHandlerCoverageError(
            "production-required skill handlers are missing: " + ", ".join(missing)
        )

    try:
        committed = _load_json(output_path)
    except FileNotFoundError as exc:
        raise SkillHandlerCoverageError(
            f"skill handler coverage manifest is missing: {_repo_path(output_path)}"
        ) from exc

    validate_manifest(committed, schema_path=schema_path)
    if committed != expected:
        raise SkillHandlerCoverageError(
            "skill handler coverage manifest is stale; run "
            "`python scripts/runtime/skill_handler_coverage.py` and commit the result"
        )
    return expected


def write_manifest(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    modules_dir: Path = DEFAULT_MODULES_DIR,
    registry: SkillHandlerRegistry = BUILTIN_SKILL_HANDLER_REGISTRY,
    schema_path: Path = DEFAULT_SCHEMA,
) -> dict[str, Any]:
    manifest = build_coverage_manifest(modules_dir=modules_dir, registry=registry)
    validate_manifest(manifest, schema_path=schema_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json_dump(manifest), encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate or validate the production skill handler coverage manifest.",
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
            manifest = assert_manifest_current(
                output_path=args.output,
                modules_dir=args.modules_dir,
                schema_path=args.schema,
            )
        else:
            manifest = write_manifest(
                output_path=args.output,
                modules_dir=args.modules_dir,
                schema_path=args.schema,
            )
        if args.print_json:
            print(_json_dump(manifest), end="")
    except SkillHandlerCoverageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _coverage_entry(
    *,
    module: Mapping[str, Any],
    module_path: Path,
    handler: SkillHandler | None,
) -> dict[str, Any]:
    runtime_role = str(module.get("runtime_role", "runtime"))
    production_required = runtime_role in {"runtime", "shared"}
    if handler is None:
        coverage_status = "missing_handler" if production_required else "not_required"
        descriptor: dict[str, Any] = {
            "handler_id": None,
            "runtime_path": None,
            "strategy": None,
            "output_contract": None,
            "test_coverage": [],
            "lifecycle_status": None,
        }
    else:
        coverage_status = "covered"
        descriptor = handler.descriptor()

    return {
        "coverage_status": coverage_status,
        "handler_id": descriptor["handler_id"],
        "lifecycle_status": descriptor["lifecycle_status"],
        "module_path": _repo_path(module_path),
        "module_tests": _module_tests(module),
        "output_contract": descriptor["output_contract"],
        "production_required": production_required,
        "runtime_role": runtime_role,
        "required_tools": list(module["required_tools"]),
        "runtime_path": descriptor["runtime_path"],
        "runtime_tests": descriptor["test_coverage"],
        "skill_name": module["name"],
        "skill_version": module["version"],
        "strategy": descriptor["strategy"],
    }


def _load_skill_modules(modules_dir: Path) -> tuple[tuple[Path, dict[str, Any]], ...]:
    modules: list[tuple[Path, dict[str, Any]]] = []
    for module_path in sorted(modules_dir.rglob("module.json")):
        module = _load_json(module_path)
        if module.get("kind") == "skill":
            modules.append((module_path, module))
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


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise SkillHandlerCoverageError(f"{_repo_path(path)} must contain a JSON object")
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
