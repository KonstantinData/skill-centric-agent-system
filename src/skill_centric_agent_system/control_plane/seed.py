from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

DEFAULT_CREATED_AT = "2026-05-22T00:00:00Z"
DEFAULT_PRINCIPAL_KIND = "role"
DEFAULT_PRINCIPAL_ID = "repository-maintainer"
DEFAULT_VERSION = "0.1.0"

REFERENCE_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("required_tools", "tool", True),
    ("optional_tools", "tool", False),
    ("knowledge_scopes", "knowledge_scope", True),
    ("data_scopes", "data_scope", True),
    ("policies", "policy", True),
    ("validators", "validator", True),
)

SCOPE_KINDS = {"knowledge_scope", "data_scope", "memory_scope"}

CAPABILITY_CLASS_BY_KIND = {
    "instruction": "instruction",
    "skill": "analysis",
    "tool": "tool_access",
    "knowledge_scope": "knowledge_access",
    "data_scope": "data_access",
    "memory_scope": "memory_access",
    "policy": "policy",
    "validator": "validation",
}

SEED_TABLE_COLUMNS = {
    "modules": (
        "id",
        "name",
        "kind",
        "status",
        "current_version_id",
        "created_at",
        "updated_at",
    ),
    "module_versions": (
        "id",
        "module_id",
        "version",
        "source_uri",
        "checksum",
        "selection_base_score",
        "created_at",
    ),
    "module_selection_metadata": (
        "id",
        "module_version_id",
        "description",
        "capability_class",
        "domain_tags_json",
        "task_types_json",
        "risk_levels_json",
        "task_domains_json",
        "required_inputs_json",
        "phrases_json",
        "negative_phrases_json",
        "triggers_json",
        "inputs_json",
        "outputs_json",
        "score_modifiers_json",
        "requires_all_policies",
    ),
    "module_dependencies": (
        "id",
        "module_version_id",
        "dependency_kind",
        "dependency_id",
        "is_required",
    ),
    "policy_bindings": (
        "id",
        "policy_id",
        "target_kind",
        "target_id",
        "effect",
        "priority",
    ),
    "scope_bindings": (
        "id",
        "scope_id",
        "scope_kind",
        "principal_kind",
        "principal_id",
        "policy_id",
        "effect",
    ),
}


@dataclass(frozen=True)
class ControlPlaneSeedRecords:
    modules: tuple[dict[str, Any], ...]
    module_versions: tuple[dict[str, Any], ...]
    module_selection_metadata: tuple[dict[str, Any], ...]
    module_dependencies: tuple[dict[str, Any], ...]
    policy_bindings: tuple[dict[str, Any], ...]
    scope_bindings: tuple[dict[str, Any], ...]

    def table_records(self) -> dict[str, tuple[dict[str, Any], ...]]:
        return {
            "modules": self.modules,
            "module_versions": self.module_versions,
            "module_selection_metadata": self.module_selection_metadata,
            "module_dependencies": self.module_dependencies,
            "policy_bindings": self.policy_bindings,
            "scope_bindings": self.scope_bindings,
        }


def build_seed_records(
    module_paths: list[Path],
    *,
    created_at: str = DEFAULT_CREATED_AT,
    principal_kind: str = DEFAULT_PRINCIPAL_KIND,
    principal_id: str = DEFAULT_PRINCIPAL_ID,
) -> ControlPlaneSeedRecords:
    module_inputs = [_load_module(path) for path in sorted(module_paths)]
    actual_modules = [module for _, module, _ in module_inputs]
    dependencies = _module_dependencies(actual_modules)
    stub_modules = _stub_modules(actual_modules, dependencies)
    all_modules = [*actual_modules, *stub_modules]
    policy_names = sorted(module["name"] for module in all_modules if module["kind"] == "policy")
    default_policy_name = policy_names[0] if policy_names else None

    modules: list[dict[str, Any]] = []
    module_versions: list[dict[str, Any]] = []
    metadata: list[dict[str, Any]] = []
    module_dependencies: list[dict[str, Any]] = []
    policy_bindings: list[dict[str, Any]] = []
    scope_bindings: list[dict[str, Any]] = []

    for path, module, checksum in module_inputs:
        modules.append(_module_record(module, created_at))
        module_versions.append(
            _module_version_record(
                module,
                source_uri=f"repo://{_repo_relative_path(path)}",
                checksum=checksum,
                created_at=created_at,
            )
        )
        metadata.append(_selection_metadata_record(module))

    for module in stub_modules:
        modules.append(_module_record(module, created_at))
        module_versions.append(
            _module_version_record(
                module,
                source_uri=f"generated://{module['kind']}/{module['name']}",
                checksum=f"sha256:generated-{module['name']}",
                created_at=created_at,
            )
        )
        metadata.append(_selection_metadata_record(module))

    for module in actual_modules:
        module_version_id = _module_version_id(module["name"], module["version"])
        for field, dependency_kind, is_required in REFERENCE_FIELDS:
            for dependency_name in module[field]:
                module_dependencies.append(
                    {
                        "id": _dependency_id(module["name"], field, dependency_name),
                        "module_version_id": module_version_id,
                        "dependency_kind": dependency_kind,
                        "dependency_id": _module_id(dependency_name),
                        "is_required": int(is_required),
                    }
                )

        for policy_name in module["policies"]:
            policy_bindings.append(
                {
                    "id": _policy_binding_id(policy_name, module["name"]),
                    "policy_id": _module_id(policy_name),
                    "target_kind": "module",
                    "target_id": _module_id(module["name"]),
                    "effect": "allow",
                    "priority": 100,
                }
            )

    if default_policy_name is not None:
        scope_modules = {
            (dependency["name"], dependency["kind"]): dependency
            for dependency in dependencies.values()
            if dependency["kind"] in SCOPE_KINDS
        }
        for module in all_modules:
            if module["kind"] in SCOPE_KINDS:
                scope_modules[(module["name"], module["kind"])] = {
                    "name": module["name"],
                    "kind": module["kind"],
                }
        for dependency in scope_modules.values():
            scope_bindings.append(
                {
                    "id": _scope_binding_id(dependency["name"], principal_id),
                    "scope_id": _module_id(dependency["name"]),
                    "scope_kind": dependency["kind"],
                    "principal_kind": principal_kind,
                    "principal_id": principal_id,
                    "policy_id": _module_id(default_policy_name),
                    "effect": "allow",
                }
            )

    return ControlPlaneSeedRecords(
        modules=tuple(sorted(modules, key=lambda item: item["id"])),
        module_versions=tuple(sorted(module_versions, key=lambda item: item["id"])),
        module_selection_metadata=tuple(sorted(metadata, key=lambda item: item["id"])),
        module_dependencies=tuple(sorted(module_dependencies, key=lambda item: item["id"])),
        policy_bindings=tuple(sorted(policy_bindings, key=lambda item: item["id"])),
        scope_bindings=tuple(sorted(scope_bindings, key=lambda item: item["id"])),
    )


def generate_seed_sql(records: ControlPlaneSeedRecords) -> str:
    statements = [
        "-- Generated by scripts/cloudflare/generate_control_plane_seed.py.",
        "-- Source: registry/modules/**/module.json.",
    ]
    for table, table_records in records.table_records().items():
        columns = SEED_TABLE_COLUMNS[table]
        for record in table_records:
            statements.append(_upsert_statement(table, columns, record))
    return "\n\n".join(statements) + "\n"


def _load_module(path: Path) -> tuple[Path, dict[str, Any], str]:
    raw_text = path.read_text(encoding="utf-8")
    checksum = "sha256:" + hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    module = json.loads(raw_text)
    return path, _normalize_module(module), checksum


def _repo_relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_module(module: dict[str, Any]) -> dict[str, Any]:
    normalized = cast(dict[str, Any], json.loads(json.dumps(module)))
    normalized["tests"] = _module_tests(normalized)
    normalized["task_signals"]["task_types"] = [
        _normalize_task_type(task_type)
        for task_type in normalized["task_signals"]["task_types"]
    ]
    normalized["selection"]["score_modifiers"] = [
        {
            **modifier,
            "signal": _normalize_signal(modifier["signal"]),
        }
        for modifier in normalized["selection"]["score_modifiers"]
    ]
    return normalized


def _normalize_task_type(task_type: str) -> str:
    return task_type.replace("_", "-")


def _normalize_signal(signal: str) -> str:
    if signal.startswith("task_type:"):
        prefix, value = signal.split(":", 1)
        return f"{prefix}:{_normalize_task_type(value)}"
    return signal


def _module_tests(module: dict[str, Any]) -> list[str]:
    tests = module.get("tests", [])
    if isinstance(tests, dict):
        flattened: list[str] = []
        for field in ("contract", "runtime", "fixtures"):
            values = tests.get(field, [])
            if isinstance(values, list):
                flattened.extend(str(value) for value in values)
        return flattened
    if isinstance(tests, list):
        return [str(value) for value in tests]
    return []


def _module_dependencies(modules: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    dependencies: dict[tuple[str, str], dict[str, Any]] = {}
    for module in modules:
        task_types = module["task_signals"]["task_types"]
        risk_levels = module["task_signals"]["risk_levels"]
        task_domains = module["task_signals"]["domains"]
        for field, dependency_kind, _is_required in REFERENCE_FIELDS:
            for dependency_name in module[field]:
                key = (dependency_name, dependency_kind)
                existing = dependencies.get(key)
                if existing is None:
                    dependencies[key] = {
                        "name": dependency_name,
                        "kind": dependency_kind,
                        "task_types": set(),
                        "risk_levels": set(),
                        "task_domains": set(),
                    }
                    existing = dependencies[key]
                existing["task_types"].update(task_types)
                existing["risk_levels"].update(risk_levels)
                existing["task_domains"].update(task_domains)
    return dependencies


def _stub_modules(
    modules: list[dict[str, Any]],
    dependencies: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    existing = {(module["name"], module["kind"]) for module in modules}
    stubs: list[dict[str, Any]] = []
    for dependency in dependencies.values():
        if (dependency["name"], dependency["kind"]) in existing:
            continue
        kind = dependency["kind"]
        is_scope = kind in SCOPE_KINDS
        stubs.append(
            {
                "name": dependency["name"],
                "version": DEFAULT_VERSION,
                "kind": kind,
                "description": f"Generated {kind} module for {dependency['name']}.",
                "capability_class": CAPABILITY_CLASS_BY_KIND[kind],
                "domain_tags": sorted(dependency["task_domains"]) if is_scope else [],
                "task_signals": {
                    "task_types": sorted(dependency["task_types"]) if is_scope else [],
                    "risk_levels": sorted(dependency["risk_levels"]) if is_scope else [],
                    "domains": sorted(dependency["task_domains"]) if is_scope else [],
                    "required_inputs": [],
                    "phrases": [dependency["name"]],
                    "negative_phrases": [],
                },
                "triggers": [dependency["name"]],
                "inputs": [],
                "outputs": [f"{dependency['name']}-output"],
                "required_tools": [],
                "optional_tools": [],
                "knowledge_scopes": [],
                "data_scopes": [],
                "policies": [],
                "validators": [],
                "selection": {
                    "base_score": 1.0 if kind == "policy" else 0.5,
                    "score_modifiers": [],
                    "requires_all_policies": False,
                },
                "tests": [f"{dependency['name']}-seed-contract"],
            }
        )
    return stubs


def _module_record(module: dict[str, Any], created_at: str) -> dict[str, Any]:
    return {
        "id": _module_id(module["name"]),
        "name": module["name"],
        "kind": module["kind"],
        "status": "active",
        "current_version_id": _module_version_id(module["name"], module["version"]),
        "created_at": created_at,
        "updated_at": created_at,
    }


def _module_version_record(
    module: dict[str, Any],
    *,
    source_uri: str,
    checksum: str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "id": _module_version_id(module["name"], module["version"]),
        "module_id": _module_id(module["name"]),
        "version": module["version"],
        "source_uri": source_uri,
        "checksum": checksum,
        "selection_base_score": module["selection"]["base_score"],
        "created_at": created_at,
    }


def _selection_metadata_record(module: dict[str, Any]) -> dict[str, Any]:
    task_signals = module["task_signals"]
    return {
        "id": _selection_metadata_id(module["name"], module["version"]),
        "module_version_id": _module_version_id(module["name"], module["version"]),
        "description": module["description"],
        "capability_class": module["capability_class"],
        "domain_tags_json": _json_array(module["domain_tags"]),
        "task_types_json": _json_array(task_signals["task_types"]),
        "risk_levels_json": _json_array(task_signals["risk_levels"]),
        "task_domains_json": _json_array(task_signals["domains"]),
        "required_inputs_json": _json_array(task_signals["required_inputs"]),
        "phrases_json": _json_array(task_signals["phrases"]),
        "negative_phrases_json": _json_array(task_signals["negative_phrases"]),
        "triggers_json": _json_array(module["triggers"]),
        "inputs_json": _json_array(module["inputs"]),
        "outputs_json": _json_array(module["outputs"]),
        "score_modifiers_json": json.dumps(
            module["selection"]["score_modifiers"],
            separators=(",", ":"),
            sort_keys=True,
        ),
        "requires_all_policies": int(module["selection"]["requires_all_policies"]),
    }


def _json_array(values: list[str]) -> str:
    return json.dumps(sorted(values), separators=(",", ":"))


def _upsert_statement(table: str, columns: tuple[str, ...], record: dict[str, Any]) -> str:
    column_sql = ", ".join(columns)
    value_sql = ", ".join(_sql_literal(record[column]) for column in columns)
    update_columns = [column for column in columns if column != "id"]
    update_sql = ", ".join(f"{column} = excluded.{column}" for column in update_columns)
    return (
        f"INSERT INTO {table} ({column_sql})\n"
        f"VALUES ({value_sql})\n"
        f"ON CONFLICT(id) DO UPDATE SET {update_sql};"
    )


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int | float):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _module_id(name: str) -> str:
    return f"mod-{name}"


def _module_version_id(name: str, version: str) -> str:
    return f"mv-{name}-{version.replace('.', '-')}"


def _selection_metadata_id(name: str, version: str) -> str:
    return f"msm-{name}-{version.replace('.', '-')}"


def _dependency_id(source_name: str, field: str, dependency_name: str) -> str:
    return f"dep-{source_name}-{field.replace('_', '-')}-{dependency_name}"


def _policy_binding_id(policy_name: str, module_name: str) -> str:
    return f"pb-{policy_name}-{module_name}"


def _scope_binding_id(scope_name: str, principal_id: str) -> str:
    return f"sb-{principal_id}-{scope_name}"
