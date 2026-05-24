from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from skill_centric_agent_system.runtime.enforcement import (
    ProfileEnforcementError,
    RuntimeProfileEnforcer,
)

PlanBuilder = Callable[[Mapping[str, Any]], tuple[dict[str, Any], ...]]


@dataclass(frozen=True)
class SkillHandlerPlan:
    skill_name: str
    skill_version: str
    handler_id: str
    strategy: str
    output_contract: str
    actions: tuple[dict[str, Any], ...]

    def handler_ref(self) -> dict[str, str]:
        return {
            "name": self.skill_name,
            "version": self.skill_version,
            "handler_id": self.handler_id,
        }


@dataclass(frozen=True)
class RuntimeSkillPlan:
    strategy: str
    output_contract: str
    actions: tuple[dict[str, Any], ...]
    skill_handlers: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class SkillHandler:
    skill_name: str
    skill_version: str
    strategy: str
    output_contract: str
    build_actions: PlanBuilder

    @property
    def handler_id(self) -> str:
        return f"{self.skill_name}@{self.skill_version}"

    def build_plan(self, profile: Mapping[str, Any]) -> SkillHandlerPlan:
        return SkillHandlerPlan(
            skill_name=self.skill_name,
            skill_version=self.skill_version,
            handler_id=self.handler_id,
            strategy=self.strategy,
            output_contract=self.output_contract,
            actions=self.build_actions(profile),
        )


class SkillHandlerRegistrationError(ValueError):
    """Raised when executable skill handlers are registered inconsistently."""


class SkillHandlerRegistry:
    """Version-pinned executable skill handler registry for runtime planning."""

    def __init__(self, handlers: Iterable[SkillHandler]) -> None:
        by_name_version: dict[tuple[str, str], SkillHandler] = {}
        known_versions: dict[str, set[str]] = {}
        for handler in handlers:
            key = (handler.skill_name, handler.skill_version)
            if key in by_name_version:
                raise SkillHandlerRegistrationError(
                    f"Duplicate skill handler: {handler.handler_id}"
                )
            by_name_version[key] = handler
            known_versions.setdefault(handler.skill_name, set()).add(handler.skill_version)

        self._by_name_version = by_name_version
        self._known_versions = known_versions

    def build_plan(
        self,
        profile: Mapping[str, Any],
        *,
        enforcer: RuntimeProfileEnforcer,
    ) -> RuntimeSkillPlan:
        selected_skill_names = _selected_skill_names(profile)
        if not selected_skill_names:
            return RuntimeSkillPlan(
                strategy="profile-without-executable-skill",
                output_contract=_output_contract_for_task_type(profile),
                actions=(),
                skill_handlers=(),
            )

        plans: list[SkillHandlerPlan] = []
        for skill_name in selected_skill_names:
            enforcer.require_skill(skill_name)
            skill_version = _required_version_pin(profile, skill_name)
            enforcer.require_module_version(skill_name, skill_version)
            plans.append(self._resolve(skill_name, skill_version).build_plan(profile))

        return _aggregate_plans(plans)

    def _resolve(self, skill_name: str, skill_version: str) -> SkillHandler:
        handler = self._by_name_version.get((skill_name, skill_version))
        if handler is not None:
            return handler

        if skill_name in self._known_versions:
            raise ProfileEnforcementError(
                f"No executable skill handler is registered for {skill_name}@{skill_version}.",
                stop_reason="policy_denied",
                code="skill_handler_version_mismatch",
            )

        raise ProfileEnforcementError(
            f"No executable skill handler is registered for selected skill: {skill_name}.",
            stop_reason="policy_denied",
            code="skill_handler_not_registered",
        )


def builtin_skill_handler_registry() -> SkillHandlerRegistry:
    return SkillHandlerRegistry(
        (
            SkillHandler(
                skill_name="git-diff-analysis",
                skill_version="0.1.0",
                strategy="code-review-readonly",
                output_contract="review-findings-contract",
                build_actions=_git_diff_analysis_actions,
            ),
            SkillHandler(
                skill_name="research-context-synthesis",
                skill_version="0.1.0",
                strategy="research-context-synthesis",
                output_contract="research-output-contract",
                build_actions=_no_tool_actions,
            ),
            SkillHandler(
                skill_name="task-execution-planning",
                skill_version="0.1.0",
                strategy="conservative-task-execution",
                output_contract="task-execution-output-contract",
                build_actions=_task_execution_planning_actions,
            ),
            SkillHandler(
                skill_name="general-task-summary",
                skill_version="0.1.0",
                strategy="general-task-summary",
                output_contract="general-output-contract",
                build_actions=_no_tool_actions,
            ),
        )
    )


def _selected_skill_names(profile: Mapping[str, Any]) -> tuple[str, ...]:
    skills = profile.get("skills", [])
    if not isinstance(skills, list):
        return ()
    return tuple(str(skill_name) for skill_name in skills)


def _required_version_pin(profile: Mapping[str, Any], module_name: str) -> str:
    module_versions = profile.get("module_versions", {})
    if not isinstance(module_versions, Mapping) or module_name not in module_versions:
        raise ProfileEnforcementError(
            f"Selected skill is not version-pinned: {module_name}.",
            stop_reason="policy_denied",
            code="selected_skill_version_missing",
        )
    return str(module_versions[module_name])


def _aggregate_plans(plans: list[SkillHandlerPlan]) -> RuntimeSkillPlan:
    strategies = tuple(plan.strategy for plan in plans)
    output_contracts = tuple(dict.fromkeys(plan.output_contract for plan in plans))
    actions = tuple(action for plan in plans for action in plan.actions)
    strategy = strategies[0] if len(strategies) == 1 else "skill-handler-pipeline"
    output_contract = (
        output_contracts[0] if len(output_contracts) == 1 else "composite-output-contract"
    )
    return RuntimeSkillPlan(
        strategy=strategy,
        output_contract=output_contract,
        actions=actions,
        skill_handlers=tuple(plan.handler_ref() for plan in plans),
    )


def _output_contract_for_task_type(profile: Mapping[str, Any]) -> str:
    task_type = str(profile.get("task_type", "general-task"))
    return {
        "code-review": "review-findings-contract",
        "research": "research-output-contract",
        "task-execution": "task-execution-output-contract",
        "general-task": "general-output-contract",
    }.get(task_type, "general-output-contract")


def _git_diff_analysis_actions(profile: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return (
        {"tool": "git-read", "payload": {"args": ["status", "--short"]}},
        {"tool": "filesystem-read", "payload": {"path": "README.md", "max_bytes": 4000}},
    )


def _task_execution_planning_actions(profile: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return (
        {"tool": "git-read", "payload": {"args": ["status", "--short"]}},
        {"tool": "filesystem-list", "payload": {"path": ".", "max_entries": 80}},
        {"tool": "filesystem-read", "payload": {"path": "README.md", "max_bytes": 4000}},
    )


def _no_tool_actions(profile: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return ()


BUILTIN_SKILL_HANDLER_REGISTRY = builtin_skill_handler_registry()
