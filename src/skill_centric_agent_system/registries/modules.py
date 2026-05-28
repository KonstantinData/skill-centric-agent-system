from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

MODULE_REFERENCE_KINDS = {
    "required_tools": "tool",
    "optional_tools": "tool",
    "knowledge_scopes": "knowledge_scope",
    "data_scopes": "data_scope",
    "policies": "policy",
    "validators": "validator",
}


class RegistryError(ValueError):
    """Base error for registry contract violations."""


class DuplicateModuleError(RegistryError):
    """Raised when a registry contains duplicate name/version pairs."""


class UnknownModuleError(RegistryError):
    """Raised when a requested module cannot be resolved."""


@dataclass(frozen=True)
class ModuleReference:
    source_name: str
    field: str
    target_name: str
    expected_kind: str


@dataclass(frozen=True)
class ModuleMetadata:
    name: str
    version: str
    kind: str
    description: str
    runtime_role: str | None
    capability_class: str
    domain_tags: frozenset[str]
    task_types: frozenset[str]
    risk_levels: frozenset[str]
    task_domains: frozenset[str]
    required_inputs: frozenset[str]
    phrases: frozenset[str]
    negative_phrases: frozenset[str]
    triggers: frozenset[str]
    inputs: frozenset[str]
    outputs: frozenset[str]
    required_tools: tuple[str, ...]
    optional_tools: tuple[str, ...]
    knowledge_scopes: tuple[str, ...]
    data_scopes: tuple[str, ...]
    policies: tuple[str, ...]
    validators: tuple[str, ...]
    base_score: float
    score_modifiers: tuple[dict[str, Any], ...]
    requires_all_policies: bool
    tests: frozenset[str]
    raw: dict[str, Any]

    @classmethod
    def from_mapping(cls, module: dict[str, Any]) -> ModuleMetadata:
        task_signals = module["task_signals"]
        selection = module["selection"]
        return cls(
            name=module["name"],
            version=module["version"],
            kind=module["kind"],
            description=module["description"],
            runtime_role=(
                str(module["runtime_role"]) if module.get("runtime_role") is not None else None
            ),
            capability_class=module["capability_class"],
            domain_tags=frozenset(module["domain_tags"]),
            task_types=frozenset(task_signals["task_types"]),
            risk_levels=frozenset(task_signals["risk_levels"]),
            task_domains=frozenset(task_signals["domains"]),
            required_inputs=frozenset(task_signals["required_inputs"]),
            phrases=frozenset(_normalize_texts(task_signals["phrases"])),
            negative_phrases=frozenset(_normalize_texts(task_signals["negative_phrases"])),
            triggers=frozenset(_normalize_texts(module["triggers"])),
            inputs=frozenset(module["inputs"]),
            outputs=frozenset(module["outputs"]),
            required_tools=tuple(module["required_tools"]),
            optional_tools=tuple(module["optional_tools"]),
            knowledge_scopes=tuple(module["knowledge_scopes"]),
            data_scopes=tuple(module["data_scopes"]),
            policies=tuple(module["policies"]),
            validators=tuple(module["validators"]),
            base_score=float(selection["base_score"]),
            score_modifiers=tuple(selection["score_modifiers"]),
            requires_all_policies=bool(selection["requires_all_policies"]),
            tests=frozenset(module["tests"]),
            raw=module,
        )

    def references(self) -> tuple[ModuleReference, ...]:
        references: list[ModuleReference] = []
        for field, expected_kind in MODULE_REFERENCE_KINDS.items():
            for target_name in getattr(self, field):
                references.append(
                    ModuleReference(
                        source_name=self.name,
                        field=field,
                        target_name=target_name,
                        expected_kind=expected_kind,
                    )
                )
        return tuple(references)


@dataclass(frozen=True)
class RegistryQuery:
    kinds: frozenset[str] = frozenset()
    capability_classes: frozenset[str] = frozenset()
    domains: frozenset[str] = frozenset()
    task_types: frozenset[str] = frozenset()
    available_inputs: frozenset[str] = frozenset()
    require_available_inputs: bool = False


@dataclass(frozen=True)
class TaskSignals:
    task_type: str
    risk_level: str
    domains: frozenset[str] = frozenset()
    available_inputs: frozenset[str] = frozenset()
    capability_hints: frozenset[str] = frozenset()
    phrases: frozenset[str] = frozenset()
    constraints: frozenset[str] = frozenset()
    error_feedback: frozenset[str] = frozenset()

    def normalized_text_signals(self) -> frozenset[str]:
        return frozenset(_normalize_texts((*self.phrases, *self.constraints)))


@dataclass(frozen=True)
class ScoreResult:
    module: ModuleMetadata
    score: float
    matched_signals: tuple[str, ...]
    negative_signals: tuple[str, ...]
    explanation: tuple[str, ...]


PolicyEffect = Literal["allow", "deny", "needs_clarification"]


@dataclass(frozen=True)
class PolicyContext:
    allowed_policy_ids: frozenset[str] = frozenset()
    denied_module_ids: frozenset[str] = frozenset()
    denied_kinds: frozenset[str] = frozenset()
    denied_capability_classes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PolicyDecision:
    module: ModuleMetadata
    effect: PolicyEffect
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class GraphValidationResult:
    is_valid: bool
    errors: tuple[str, ...]
    reachable_modules: tuple[str, ...]


class InMemoryModuleRegistry:
    def __init__(self, modules: Iterable[ModuleMetadata]) -> None:
        by_name_version: dict[tuple[str, str], ModuleMetadata] = {}
        by_name: dict[str, list[ModuleMetadata]] = {}

        for module in modules:
            key = (module.name, module.version)
            if key in by_name_version:
                raise DuplicateModuleError(
                    f"Duplicate module version: {module.name}@{module.version}"
                )
            by_name_version[key] = module
            by_name.setdefault(module.name, []).append(module)

        self._by_name_version = by_name_version
        self._by_name = {
            name: sorted(versions, key=lambda item: _semver_key(item.version), reverse=True)
            for name, versions in by_name.items()
        }

    @classmethod
    def from_paths(cls, paths: Iterable[Path]) -> InMemoryModuleRegistry:
        modules: list[ModuleMetadata] = []
        for path in paths:
            for module_path in _iter_json_files(path):
                modules.append(
                    ModuleMetadata.from_mapping(
                        json.loads(module_path.read_text(encoding="utf-8"))
                    )
                )
        return cls(modules)

    def all_modules(self) -> tuple[ModuleMetadata, ...]:
        return tuple(
            sorted(
                self._by_name_version.values(),
                key=lambda module: (module.name, _semver_key(module.version)),
            )
        )

    def discover(self, query: RegistryQuery) -> tuple[ModuleMetadata, ...]:
        candidates = [
            module
            for module in self.all_modules()
            if self._matches_query(module=module, query=query)
        ]
        return tuple(candidates)

    def score(self, module: ModuleMetadata, task_signals: TaskSignals) -> ScoreResult:
        score = module.base_score
        matched_signals = set(self._structured_matches(module, task_signals))
        negative_signals: set[str] = set()
        explanation: list[str] = [f"base_score:{module.base_score:.2f}"]

        for modifier in module.score_modifiers:
            signal = modifier["signal"]
            weight = float(modifier["weight"])
            if _signal_matches(signal=signal, module=module, task_signals=task_signals):
                score += weight
                explanation.append(modifier["reason"])
                if weight < 0:
                    negative_signals.add(signal)
                else:
                    matched_signals.add(signal)

        for phrase in module.negative_phrases & task_signals.normalized_text_signals():
            negative_signals.add(f"phrase:{phrase}")

        feedback_penalty, feedback_reason = _error_feedback_penalty(module, task_signals)
        if feedback_penalty > 0:
            score -= feedback_penalty
            negative_signals.add(feedback_reason)
            explanation.append(f"feedback_penalty:{feedback_reason}")

        clamped_score = max(0.0, min(1.0, score))
        return ScoreResult(
            module=module,
            score=round(clamped_score, 4),
            matched_signals=tuple(sorted(matched_signals)),
            negative_signals=tuple(sorted(negative_signals)),
            explanation=tuple(explanation),
        )

    def filter_candidate(self, module: ModuleMetadata, context: PolicyContext) -> PolicyDecision:
        reasons: list[str] = []
        if module.name in context.denied_module_ids:
            return PolicyDecision(module, "deny", ("module is explicitly denied",))
        if module.kind in context.denied_kinds:
            return PolicyDecision(module, "deny", (f"kind is denied: {module.kind}",))
        if module.capability_class in context.denied_capability_classes:
            return PolicyDecision(
                module,
                "deny",
                (f"capability class is denied: {module.capability_class}",),
            )

        if module.requires_all_policies:
            missing_policies = sorted(set(module.policies) - set(context.allowed_policy_ids))
            if missing_policies:
                reasons.append(f"missing required policies: {', '.join(missing_policies)}")
                return PolicyDecision(module, "needs_clarification", tuple(reasons))

        return PolicyDecision(module, "allow", ("policy context allows candidate",))

    def resolve(self, name: str, version: str | None = None) -> ModuleMetadata:
        if version is not None:
            module = self._by_name_version.get((name, version))
            if module is None:
                raise UnknownModuleError(f"Unknown module version: {name}@{version}")
            return module

        versions = self._by_name.get(name)
        if not versions:
            raise UnknownModuleError(f"Unknown module: {name}")
        return versions[0]

    def validate_graph(
        self,
        selected_module_names: Iterable[str],
        policy_context: PolicyContext | None = None,
    ) -> GraphValidationResult:
        selected = tuple(dict.fromkeys(selected_module_names))
        errors: list[str] = []
        reachable: set[str] = set()

        for name in selected:
            if name not in self._by_name:
                errors.append(f"missing selected module: {name}")

        for name in selected:
            self._collect_reachable(name=name, reachable=reachable, errors=errors)

        for module_name in sorted(reachable):
            module = self.resolve(module_name)
            for reference in module.references():
                if reference.target_name not in self._by_name:
                    errors.append(
                        f"{reference.source_name}.{reference.field} references missing "
                        f"{reference.expected_kind}: {reference.target_name}"
                    )
                    continue

                target = self.resolve(reference.target_name)
                if target.kind != reference.expected_kind:
                    errors.append(
                        f"{reference.source_name}.{reference.field} references "
                        f"{reference.target_name} as {reference.expected_kind}, got {target.kind}"
                    )

            if (
                policy_context is not None
                and module.capability_class in policy_context.denied_capability_classes
            ):
                errors.append(
                    f"reachable module {module.name} uses denied capability "
                    f"{module.capability_class}"
                )

        errors.extend(self._cycle_errors(sorted(reachable)))

        return GraphValidationResult(
            is_valid=not errors,
            errors=tuple(dict.fromkeys(errors)),
            reachable_modules=tuple(sorted(reachable)),
        )

    def _matches_query(self, module: ModuleMetadata, query: RegistryQuery) -> bool:
        if query.kinds and module.kind not in query.kinds:
            return False
        if query.capability_classes and module.capability_class not in query.capability_classes:
            return False
        if query.domains and not (module.domain_tags | module.task_domains) & query.domains:
            return False
        if query.task_types and not module.task_types & query.task_types:
            return False
        return not (
            query.require_available_inputs
            and not module.required_inputs <= query.available_inputs
        )

    def _structured_matches(
        self,
        module: ModuleMetadata,
        task_signals: TaskSignals,
    ) -> tuple[str, ...]:
        matches: list[str] = []
        if task_signals.task_type in module.task_types:
            matches.append(f"task_type:{task_signals.task_type}")
        if task_signals.risk_level in module.risk_levels:
            matches.append(f"risk_level:{task_signals.risk_level}")
        for domain in sorted((module.domain_tags | module.task_domains) & task_signals.domains):
            matches.append(f"domain:{domain}")
        for input_name in sorted(module.required_inputs & task_signals.available_inputs):
            matches.append(f"input:{input_name}")
        if module.capability_class in task_signals.capability_hints:
            matches.append(f"capability_class:{module.capability_class}")
        return tuple(matches)

    def _collect_reachable(self, name: str, reachable: set[str], errors: list[str]) -> None:
        if name in reachable or name not in self._by_name:
            return
        reachable.add(name)
        module = self.resolve(name)
        for reference in module.references():
            if reference.target_name not in self._by_name:
                errors.append(
                    f"{reference.source_name}.{reference.field} references missing "
                    f"{reference.expected_kind}: {reference.target_name}"
                )
                continue
            self._collect_reachable(reference.target_name, reachable, errors)

    def _cycle_errors(self, module_names: list[str]) -> tuple[str, ...]:
        graph = {
            name: [reference.target_name for reference in self.resolve(name).references()]
            for name in module_names
        }
        errors: list[str] = []
        visiting: set[str] = set()
        visited: set[str] = set()
        path: list[str] = []

        def visit(name: str) -> None:
            if name in visiting:
                cycle_start = path.index(name)
                errors.append("circular dependency: " + " -> ".join((*path[cycle_start:], name)))
                return
            if name in visited:
                return

            visiting.add(name)
            path.append(name)
            for target_name in graph.get(name, []):
                if target_name in graph:
                    visit(target_name)
            path.pop()
            visiting.remove(name)
            visited.add(name)

        for name in module_names:
            visit(name)

        return tuple(errors)


def _iter_json_files(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    return tuple(sorted(path.rglob("*.json")))


def _normalize_texts(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(value.casefold() for value in values)


def _semver_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _signal_matches(
    signal: str,
    module: ModuleMetadata,
    task_signals: TaskSignals,
) -> bool:
    if ":" not in signal:
        return False

    prefix, value = signal.split(":", 1)
    normalized_value = value.casefold()
    if prefix == "task_type":
        return value == task_signals.task_type
    if prefix == "risk_level":
        return value == task_signals.risk_level
    if prefix == "domain":
        return value in task_signals.domains
    if prefix == "input":
        return value in task_signals.available_inputs
    if prefix == "capability_class":
        return value == module.capability_class or value in task_signals.capability_hints
    if prefix in {"phrase", "trigger"}:
        return normalized_value in task_signals.normalized_text_signals()
    if prefix == "constraint":
        return normalized_value in _normalize_texts(task_signals.constraints)
    return False


def _error_feedback_penalty(module: ModuleMetadata, task_signals: TaskSignals) -> tuple[float, str]:
    penalties = {
        "F1_INEFFICIENCY_PATH": {
            "analysis": 0.12,
            "execution": 0.12,
            "retrieval": 0.06,
        },
        "F2_INTERFACE_CONTRACT_BREAKDOWN": {
            "validation": 0.16,
            "execution": 0.1,
        },
        "R8_POLICY_CONFLICT_CONTEXT_CONTAMINATION": {
            "policy": 0.2,
            "instruction": 0.2,
        },
    }
    max_penalty = 0.0
    reason = ""
    for feedback in task_signals.error_feedback:
        penalty = penalties.get(feedback, {}).get(module.capability_class, 0.0)
        if penalty > max_penalty:
            max_penalty = penalty
            reason = f"error_feedback:{feedback}:{module.capability_class}"
    return max_penalty, reason
