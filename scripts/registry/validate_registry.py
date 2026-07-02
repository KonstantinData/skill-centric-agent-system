from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_ROOT = REPO_ROOT / "registry" / "modules"
DEFAULT_SCHEMA = REPO_ROOT / "schemas" / "module.schema.json"
DEFAULT_ENVIRONMENTS_DIR = REPO_ROOT / "registry" / "environments"

KIND_DIRS = {
    "data_scope": "data-scopes",
    "instruction": "instructions",
    "knowledge_scope": "knowledge-scopes",
    "memory_scope": "memory-scopes",
    "policy": "policies",
    "skill": "skills",
    "tool": "tools",
    "validator": "validators",
}
REFERENCE_FIELDS = {
    "required_tools": "tool",
    "optional_tools": "tool",
    "knowledge_scopes": "knowledge_scope",
    "data_scopes": "data_scope",
    "policies": "policy",
    "validators": "validator",
}
SKILL_SELECTION_METADATA_MARKERS = (
    "base_score",
    "score_modifiers",
    "task_signals",
    "required_tools:",
    "optional_tools:",
    "knowledge_scopes:",
    "data_scopes:",
    "policies:",
    "validators:",
)
SHARED_TEMPLATE_GUIDANCE_LINES = {
    "Use this skill only when it is selected through a sealed SCAS runtime profile. "
    "Do not use this SKILL.md as selection metadata; selection comes from module.json "
    "and Control Plane composition records.",
    "Preserve the profile-selected tools, policies, validators, and scopes declared in "
    "module.json.",
    "Keep outputs aligned with the module validators and runtime skill handler coverage.",
    "Fail closed when required inputs, tools, handler bindings, or validators are missing.",
}


class RegistryValidationError(ValueError):
    """Raised when the governed registry is invalid."""


def validate_registry(
    *,
    registry_root: Path = DEFAULT_REGISTRY_ROOT,
    schema_path: Path = DEFAULT_SCHEMA,
    environments_dir: Path = DEFAULT_ENVIRONMENTS_DIR,
    phase: str = "all",
    environment: str | None = None,
) -> list[str]:
    errors: list[str] = []
    modules = _load_modules(registry_root)
    schema = _load_json(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    if phase in {"3a", "schema", "all"}:
        for module_path, module in modules:
            errors.extend(_schema_errors(validator, module_path, module))
            errors.extend(
                _local_invariant_errors(
                    module_path,
                    module,
                    schema_path,
                    registry_root,
                )
            )

    if phase in {"3b", "graph", "all"}:
        errors.extend(_graph_errors(modules))
        errors.extend(_environment_errors(modules, environments_dir, environment))

    if errors:
        raise RegistryValidationError("\n".join(errors))
    return []


def _load_modules(registry_root: Path) -> tuple[tuple[Path, dict[str, Any]], ...]:
    modules: list[tuple[Path, dict[str, Any]]] = []
    for module_path in sorted(registry_root.rglob("module.json")):
        modules.append((module_path, _load_json(module_path)))
    if not modules:
        raise RegistryValidationError(
            f"no module.json files found under {_repo_path(registry_root)}"
        )
    return tuple(modules)


def _schema_errors(
    validator: Draft202012Validator,
    module_path: Path,
    module: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    for error in sorted(validator.iter_errors(module), key=lambda item: item.json_path):
        errors.append(f"{_repo_path(module_path)} {error.json_path}: {error.message}")
    return errors


def _local_invariant_errors(
    module_path: Path,
    module: Mapping[str, Any],
    schema_path: Path,
    registry_root: Path,
) -> list[str]:
    errors: list[str] = []
    module_dir = module_path.parent

    schema_ref = module.get("$schema")
    if isinstance(schema_ref, str):
        try:
            resolved_schema = _resolve_inside_repo(module_dir / schema_ref)
        except ValueError:
            resolved_schema = (module_dir / schema_ref).resolve()
        if resolved_schema != schema_path.resolve():
            errors.append(
                f"{_repo_path(module_path)} $schema must resolve to {_repo_path(schema_path)}"
            )

    expected_parent = KIND_DIRS.get(str(module.get("kind")))
    relative_module_parts = module_path.parent.relative_to(registry_root).parts
    if expected_parent and (
        len(relative_module_parts) < 2 or relative_module_parts[-2] != expected_parent
    ):
        errors.append(
            f"{_repo_path(module_path)} must live under a "
            f"registry/modules/**/{expected_parent}/ namespace"
        )

    runtime_roles = module.get("runtime_roles", {})
    if isinstance(runtime_roles, Mapping):
        default_role = runtime_roles.get("default")
        allowed_roles = runtime_roles.get("allowed", [])
        if isinstance(allowed_roles, list) and default_role not in allowed_roles:
            errors.append(
                f"{_repo_path(module_path)} runtime_roles.default must be included in allowed"
            )

    entrypoint = module.get("entrypoint")
    if module.get("kind") == "skill":
        if not isinstance(entrypoint, Mapping):
            errors.append(f"{_repo_path(module_path)} skill module requires entrypoint")
        else:
            entrypoint_path = entrypoint.get("path")
            if isinstance(entrypoint_path, str):
                resolved = (module_dir / entrypoint_path).resolve()
                if resolved.parent != module_dir.resolve() or resolved.name != "SKILL.md":
                    errors.append(
                        f"{_repo_path(module_path)} skill entrypoint must be local SKILL.md"
                    )
                elif not resolved.exists():
                    errors.append(f"{_repo_path(module_path)} missing SKILL.md entrypoint")
                else:
                    errors.extend(_skill_entrypoint_errors(resolved, module, entrypoint))

    for path_value in _path_values(module):
        candidate = Path(path_value)
        if candidate.is_absolute() or ":" in candidate.parts[0]:
            errors.append(f"{_repo_path(module_path)} contains absolute path: {path_value}")
            continue
        _resolve_inside_repo(REPO_ROOT / candidate)

    errors.extend(_provenance_errors(module_path, module))
    errors.extend(_selection_evidence_errors(module_path, module))

    return errors


def _provenance_errors(module_path: Path, module: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    provenance = module.get("provenance")
    if not isinstance(provenance, Mapping):
        return [f"{_repo_path(module_path)} provenance is required"]

    source_entries = provenance.get("source_of_truth", [])
    if not isinstance(source_entries, list):
        return errors

    has_repo_source = False
    for source in source_entries:
        if not isinstance(source, Mapping):
            continue
        if source.get("type") != "repo_path":
            continue
        has_repo_source = True
        ref = source.get("ref")
        if not isinstance(ref, str):
            continue
        try:
            resolved = _resolve_inside_repo(REPO_ROOT / ref)
        except ValueError:
            errors.append(
                f"{_repo_path(module_path)} source_of_truth repo_path escapes repository: {ref}"
            )
            continue
        if not resolved.exists():
            errors.append(
                f"{_repo_path(module_path)} source_of_truth repo_path does not exist: {ref}"
            )

    if (
        "prod" in set(str(value) for value in module.get("environments", []))
        and not has_repo_source
    ):
        errors.append(f"{_repo_path(module_path)} prod module requires repo_path source_of_truth")

    return errors


def _selection_evidence_errors(
    module_path: Path,
    module: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    selection = module.get("selection")
    evidence = module.get("selection_evidence")
    if not isinstance(selection, Mapping) or not isinstance(evidence, Mapping):
        return errors

    mode = selection.get("mode")
    tests = module.get("tests", {})
    fixture_paths = set()
    if isinstance(tests, Mapping) and isinstance(tests.get("fixtures"), list):
        fixture_paths = {str(path) for path in tests["fixtures"]}

    if module.get("status") == "active" and not fixture_paths:
        errors.append(f"{_repo_path(module_path)} active module requires tests.fixtures")

    if mode == "direct":
        if not evidence.get("positive_selection"):
            errors.append(f"{_repo_path(module_path)} direct module requires positive evidence")
        if not evidence.get("negative_selection"):
            errors.append(f"{_repo_path(module_path)} direct module requires negative evidence")
        modifiers = selection.get("score_modifiers", [])
        if isinstance(modifiers, list) and not any(
            isinstance(modifier, Mapping) and float(modifier.get("weight", 0)) > 0
            for modifier in modifiers
        ):
            errors.append(f"{_repo_path(module_path)} direct module requires positive scoring")
        task_signals = module.get("task_signals", {})
        negative_phrases = (
            task_signals.get("negative_phrases", [])
            if isinstance(task_signals, Mapping)
            else []
        )
        has_negative_modifier = isinstance(modifiers, list) and any(
            isinstance(modifier, Mapping) and float(modifier.get("weight", 0)) < 0
            for modifier in modifiers
        )
        if not negative_phrases and not has_negative_modifier:
            errors.append(f"{_repo_path(module_path)} direct module requires negative signal")
    elif mode == "dependency_only":
        if "base_score" in selection or "score_modifiers" in selection:
            errors.append(
                f"{_repo_path(module_path)} dependency_only module must not define direct scoring"
            )
        if module.get("triggers"):
            errors.append(
                f"{_repo_path(module_path)} dependency_only module must not define triggers"
            )
        task_signals = module.get("task_signals", {})
        if isinstance(task_signals, Mapping):
            direct_fields = ("task_types", "phrases", "required_inputs")
            for field in direct_fields:
                if task_signals.get(field):
                    errors.append(
                        f"{_repo_path(module_path)} dependency_only module must not define "
                        f"task_signals.{field}"
                    )
        if not evidence.get("dependency_inclusion"):
            errors.append(
                f"{_repo_path(module_path)} dependency_only module requires dependency evidence"
            )
        if not evidence.get("no_direct_selection"):
            errors.append(
                f"{_repo_path(module_path)} dependency_only module requires no-direct evidence"
            )
    else:
        errors.append(f"{_repo_path(module_path)} selection.mode must fail closed: {mode}")

    for entries in evidence.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            fixture = entry.get("fixture")
            if not isinstance(fixture, str):
                continue
            if fixture not in fixture_paths:
                errors.append(
                    f"{_repo_path(module_path)} evidence fixture is not listed in tests.fixtures: "
                    f"{fixture}"
                )
            try:
                resolved = _resolve_inside_repo(REPO_ROOT / fixture)
            except ValueError:
                errors.append(
                    f"{_repo_path(module_path)} evidence fixture escapes repository: {fixture}"
                )
                continue
            if not resolved.exists():
                errors.append(
                    f"{_repo_path(module_path)} evidence fixture does not exist: {fixture}"
                )

    return errors


def _skill_entrypoint_errors(
    skill_path: Path,
    module: Mapping[str, Any],
    entrypoint: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    text = skill_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return [f"{_repo_path(skill_path)} missing YAML frontmatter"]
    end = text.find("\n---", 4)
    if end == -1:
        return [f"{_repo_path(skill_path)} has unterminated YAML frontmatter"]
    frontmatter = text[4:end].splitlines()
    values: dict[str, str] = {}
    for line in frontmatter:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    if values.get("name") != module.get("name"):
        errors.append(f"{_repo_path(skill_path)} frontmatter name must match module name")
    if not values.get("description"):
        errors.append(f"{_repo_path(skill_path)} frontmatter description is required")

    body = text[end + len("\n---") :]
    body_lower = body.casefold()
    for marker in SKILL_SELECTION_METADATA_MARKERS:
        if marker in body_lower:
            errors.append(
                f"{_repo_path(skill_path)} must not contain selection metadata marker: {marker}"
            )

    guidance = entrypoint.get("guidance")
    if guidance == "skill_specific" and not _has_skill_specific_guidance(body):
        errors.append(
            f"{_repo_path(skill_path)} skill_specific entrypoint requires execution guidance "
            "beyond the shared sealed-profile template"
        )
    return errors


def _has_skill_specific_guidance(body: str) -> bool:
    content_lines = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        content_lines.append(line)
    return any(line not in SHARED_TEMPLATE_GUIDANCE_LINES for line in content_lines)


def _graph_errors(modules: Iterable[tuple[Path, Mapping[str, Any]]]) -> list[str]:
    errors: list[str] = []
    by_name_version: dict[tuple[str, str], Path] = {}
    by_name_kind: dict[tuple[str, str], Path] = {}
    module_list = tuple(modules)

    for module_path, module in module_list:
        name = str(module.get("name"))
        version = str(module.get("version"))
        kind = str(module.get("kind"))
        version_key = (name, version)
        kind_key = (name, kind)
        if version_key in by_name_version:
            errors.append(
                f"{_repo_path(module_path)} duplicates {name}@{version} already defined in "
                f"{_repo_path(by_name_version[version_key])}"
            )
        by_name_version[version_key] = module_path
        by_name_kind[kind_key] = module_path

    for module_path, module in module_list:
        for field, expected_kind in REFERENCE_FIELDS.items():
            values = module.get(field, [])
            if not isinstance(values, list):
                continue
            for target_name in values:
                key = (str(target_name), expected_kind)
                if key not in by_name_kind:
                    errors.append(
                        f"{_repo_path(module_path)} {field} references missing "
                        f"{expected_kind}: {target_name}"
                    )

    return errors


def _environment_errors(
    modules: Iterable[tuple[Path, Mapping[str, Any]]],
    environments_dir: Path,
    environment: str | None,
) -> list[str]:
    errors: list[str] = []
    environment_paths = (
        [environments_dir / f"{environment}.json"]
        if environment
        else sorted(environments_dir.glob("*.json"))
    )
    env_configs = [_load_json(path) for path in environment_paths if path.exists()]
    env_by_name = {str(config["name"]): config for config in env_configs}

    for module_path, module in modules:
        module_envs = set(str(value) for value in module.get("environments", []))
        for env_name in module_envs:
            config = env_by_name.get(env_name)
            if config is None:
                errors.append(
                    f"{_repo_path(module_path)} references missing environment {env_name}"
                )
                continue
            if config.get("strategy") != "allowlist":
                environment_path = environments_dir / f"{env_name}.json"
                errors.append(f"{_repo_path(environment_path)} must use allowlist")
            allowed_statuses = set(str(value) for value in config.get("allowed_statuses", []))
            if module.get("status") not in allowed_statuses:
                errors.append(
                    f"{_repo_path(module_path)} status {module.get('status')} "
                    f"is not allowed in {env_name}"
                )
            allowed_capabilities = set(
                str(value) for value in config.get("allowed_capability_classes", [])
            )
            if module.get("capability_class") not in allowed_capabilities:
                errors.append(
                    f"{_repo_path(module_path)} capability_class {module.get('capability_class')} "
                    f"is not allowed in {env_name}"
                )
    return errors


def _path_values(module: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    entrypoint = module.get("entrypoint")
    if isinstance(entrypoint, Mapping) and isinstance(entrypoint.get("path"), str):
        values.append(str(entrypoint["path"]))
    tests = module.get("tests")
    if isinstance(tests, Mapping):
        for field in ("contract", "fixtures"):
            field_values = tests.get(field, [])
            if isinstance(field_values, list):
                values.extend(str(value) for value in field_values)
    return tuple(values)


def _resolve_inside_repo(path: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(REPO_ROOT.resolve())
    return resolved


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise RegistryValidationError(f"{_repo_path(path)} must contain a JSON object")
    return parsed


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the governed SCAS module registry.")
    parser.add_argument("--registry-root", type=Path, default=DEFAULT_REGISTRY_ROOT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--environments-dir", type=Path, default=DEFAULT_ENVIRONMENTS_DIR)
    parser.add_argument(
        "--phase",
        choices=("3a", "schema", "3b", "graph", "all"),
        default="all",
    )
    parser.add_argument("--environment", choices=("dev", "staging", "prod"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        validate_registry(
            registry_root=args.registry_root,
            schema_path=args.schema,
            environments_dir=args.environments_dir,
            phase=args.phase,
            environment=args.environment,
        )
    except (OSError, json.JSONDecodeError, RegistryValidationError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("registry validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
