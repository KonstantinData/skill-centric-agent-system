from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from skill_centric_agent_system.runtime.enforcement import RuntimeProfileEnforcer
from skill_centric_agent_system.runtime.models import selected_modules
from skill_centric_agent_system.runtime.skill_handlers import SkillHandlerRegistry

SUPPORTED_RUNTIME_TASK_TYPES = {
    "code-review",
    "research",
    "task-execution",
    "general-task",
}


def task_type_for_profile(profile: Mapping[str, Any]) -> str:
    task_type = str(profile.get("task_type", "general-task"))
    if task_type in SUPPORTED_RUNTIME_TASK_TYPES:
        return task_type
    return "general-task"


def build_runtime_plan(
    profile: Mapping[str, Any],
    *,
    enforcer: RuntimeProfileEnforcer,
    skill_handlers: SkillHandlerRegistry,
) -> dict[str, Any]:
    task_type = task_type_for_profile(profile)
    skill_plan = skill_handlers.build_plan(profile, enforcer=enforcer)
    base = {
        "objective": profile["objective"],
        "task_type": task_type,
        "selected_modules": selected_modules(profile),
    }
    return {
        **base,
        "strategy": skill_plan.strategy,
        "output_contract": skill_plan.output_contract,
        "skill_handlers": list(skill_plan.skill_handlers),
        "actions": list(skill_plan.actions),
    }
