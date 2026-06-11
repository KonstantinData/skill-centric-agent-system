from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from skill_centric_agent_system.runtime.planning import task_type_for_profile
from skill_centric_agent_system.runtime.validation import RUNTIME_OUTPUT_CONTRACT_VERSION


def runtime_response(
    *,
    run_id: str,
    task_id: str,
    profile: Mapping[str, Any],
    context: Mapping[str, Any],
    plan: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    task_type = task_type_for_profile(profile)
    runtime_output = runtime_output_for_task(
        task_type=task_type,
        context=context,
        plan=plan,
        execution=execution,
    )
    return {
        "run_id": run_id,
        "task_id": task_id,
        "profile_id": profile["id"],
        "task_type": task_type,
        "status": "succeeded",
        "summary": runtime_output["summary"],
        "tool_result_count": len(execution.get("tool_results", [])),
        "runtime_output": runtime_output,
    }


def runtime_output_for_task(
    *,
    task_type: str,
    context: Mapping[str, Any],
    plan: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    tool_artifacts = tool_artifacts_from_execution(execution)
    if task_type == "code-review":
        return {
            "contract_version": RUNTIME_OUTPUT_CONTRACT_VERSION,
            "task_type": "code-review",
            "status": "completed",
            "summary": "Code review completed with profile-scoped read-only tools.",
            "artifacts": tool_artifacts,
            "details": {
                "findings": [],
                "reviewed_artifacts": tool_artifacts,
            },
        }

    if task_type == "research":
        retrieval_artifacts = retrieval_artifacts_from_context(context)
        knowledge_count = len(context.get("knowledge_chunks", []))
        memory_count = len(context.get("memory_records", []))
        open_questions = []
        if knowledge_count == 0 and memory_count == 0:
            open_questions.append(
                "No profile-authorized knowledge or memory records were returned."
            )
        return {
            "contract_version": RUNTIME_OUTPUT_CONTRACT_VERSION,
            "task_type": "research",
            "status": "completed",
            "summary": "Research completed from profile-bounded retrieval context.",
            "artifacts": retrieval_artifacts,
            "details": {
                "key_points": [
                    (
                        "Loaded "
                        f"{knowledge_count} knowledge chunk(s) and {memory_count} memory "
                        "record(s) through the Control API retrieval boundary."
                    )
                ],
                "sources": retrieval_artifacts,
                "open_questions": open_questions,
            },
        }

    if task_type == "task-execution":
        executed_actions = [
            f"{result['tool_name']}:{result['status']}"
            for result in execution.get("tool_results", [])
            if isinstance(result, Mapping)
        ]
        return {
            "contract_version": RUNTIME_OUTPUT_CONTRACT_VERSION,
            "task_type": "task-execution",
            "status": "completed",
            "summary": "Task execution completed in conservative read-only mode.",
            "artifacts": tool_artifacts,
            "details": {
                "planned_changes": [
                    "Inspect repository state and produce a bounded execution summary."
                ],
                "executed_actions": executed_actions,
                "blocked_actions": [
                    "Repository writes are outside the first productive runtime slice."
                ],
            },
        }

    return {
        "contract_version": RUNTIME_OUTPUT_CONTRACT_VERSION,
        "task_type": "general-task",
        "status": "completed",
        "summary": "General task completed with the generic runtime strategy.",
        "artifacts": [],
        "details": {
            "notes": [
                f"Runtime strategy: {plan.get('strategy', 'general-task-summary')}.",
            ],
        },
    }


def tool_artifacts_from_execution(execution: Mapping[str, Any]) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for result in execution.get("tool_results", []):
        if not isinstance(result, Mapping):
            continue
        output_uri = result.get("output_uri")
        if isinstance(output_uri, str) and output_uri:
            artifacts.append({"kind": "tool-output", "uri": output_uri})
    return artifacts


def retrieval_artifacts_from_context(context: Mapping[str, Any]) -> list[dict[str, str]]:
    response = context.get("retrieval_response")
    if not isinstance(response, Mapping):
        return []
    artifacts: list[dict[str, str]] = []
    for field in ("knowledge_chunks", "memory_records"):
        values = response.get(field, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if not isinstance(value, Mapping):
                continue
            content_uri = value.get("content_uri")
            if isinstance(content_uri, str) and content_uri.startswith("hetzner://runtime/"):
                artifacts.append({"kind": "retrieval-context", "uri": content_uri})
    return artifacts
