from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.context import (
    RetrievalContextClient,
    RuntimeContextManager,
)
from skill_centric_agent_system.runtime.enforcement import (
    ProfileEnforcementError,
    RuntimeProfileEnforcer,
)
from skill_centric_agent_system.runtime.entrypoint import RuntimeEntryPoint, RuntimeStartResult
from skill_centric_agent_system.runtime.error_taxonomy import (
    ErrorClassificationJudge,
    apply_optional_llm_judge,
    classify_runtime_failure,
    classify_runtime_success,
)
from skill_centric_agent_system.runtime.models import (
    RecompositionRequest,
    iso_timestamp,
    selected_modules,
    slug_id,
)
from skill_centric_agent_system.runtime.policies import profile_redacts_sensitive_data
from skill_centric_agent_system.runtime.skill_handlers import (
    BUILTIN_SKILL_HANDLER_REGISTRY,
    SkillHandlerRegistry,
)
from skill_centric_agent_system.runtime.storage import FlightRecorder, RuntimeStore
from skill_centric_agent_system.runtime.tool_gateway import (
    ToolDeniedError,
    ToolExecutionError,
    ToolGateway,
)
from skill_centric_agent_system.runtime.validation import (
    RUNTIME_OUTPUT_CONTRACT_VERSION,
    RuntimeValidationError,
    RuntimeValidatorFramework,
    assert_validation_passed,
)

SUPPORTED_RUNTIME_TASK_TYPES = {
    "code-review",
    "research",
    "task-execution",
    "general-task",
}


@dataclass(frozen=True)
class RuntimeLoopResult:
    run_id: str
    status: str
    stop_reason: str
    response: Mapping[str, Any]
    attempt_run_ids: tuple[str, ...] = ()
    recomposed_profile_ids: tuple[str, ...] = ()


class RuntimeLoopError(RuntimeError):
    """Raised when the runtime loop fails closed."""

    def __init__(
        self,
        message: str,
        *,
        stop_reason: str | None = None,
        recomposition_request: RecompositionRequest | None = None,
    ) -> None:
        super().__init__(message)
        self.stop_reason = stop_reason
        self.recomposition_request = recomposition_request


class MinimalRuntimeLoop:
    """First executable single-agent runtime loop."""

    def __init__(
        self,
        *,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        repository_root: str | Path,
        control_plane_client: RetrievalContextClient | None = None,
        skill_handlers: SkillHandlerRegistry | None = None,
        enable_llm_error_judge: bool = False,
        llm_error_judge: ErrorClassificationJudge | None = None,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.repository_root = Path(repository_root)
        self.control_plane_client = control_plane_client
        self.skill_handlers = skill_handlers or BUILTIN_SKILL_HANDLER_REGISTRY
        self.enable_llm_error_judge = enable_llm_error_judge
        self.llm_error_judge = llm_error_judge
        self.recorder = FlightRecorder(store, artifacts)

    def run(self, start_result: RuntimeStartResult) -> RuntimeLoopResult:
        profile = start_result.profile
        run_id = start_result.run_id
        task_id = start_result.analyzed_task.task_id
        redact_sensitive_data = profile_redacts_sensitive_data(profile)
        enforcer = RuntimeProfileEnforcer(profile)

        try:
            enforcer.validate_profile_for_runtime()
            context = self._context_step(run_id, profile, redact_sensitive_data, enforcer)
            plan = self._planner_step(run_id, profile, context, redact_sensitive_data, enforcer)
            execution = self._executor_step(run_id, profile, plan, redact_sensitive_data, enforcer)
            response = self._validator_step(
                run_id,
                task_id,
                profile,
                context,
                plan,
                execution,
                redact_sensitive_data,
                enforcer,
            )
        except (
            ProfileEnforcementError,
            RuntimeValidationError,
            ToolDeniedError,
            ToolExecutionError,
        ) as error:
            stop_reason, recomposition_request = self._handle_runtime_error(
                run_id=run_id,
                start_result=start_result,
                error=error,
                enforcer=enforcer,
                redact_sensitive_data=redact_sensitive_data,
            )
            raise RuntimeLoopError(
                str(error),
                stop_reason=stop_reason,
                recomposition_request=recomposition_request,
            ) from error

        success_classification = classify_runtime_success(
            plan=plan,
            execution=execution,
            enforcer_counters={
                "tool_calls": enforcer.tool_calls,
                "tokens_used": enforcer.tokens_used,
            },
            profile_limits=profile.get("limits", {}),
        )
        success_classification = apply_optional_llm_judge(
            success_classification,
            enabled=self.enable_llm_error_judge,
            judge=self.llm_error_judge,
            context={
                "run_id": run_id,
                "task_type": profile.get("task_type"),
                "status": "succeeded",
            },
        )
        response = {
            **response,
            "error_classification": success_classification.as_dict(),
        }

        self.recorder.record_event(
            run_id=run_id,
            event_type="runtime_completed",
            actor_role="validator",
            result=response,
            stop_reason="completed",
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.complete_run(
            run_id=run_id,
            status="succeeded",
            stop_reason="completed",
            tokens_used_total=enforcer.tokens_used,
        )
        return RuntimeLoopResult(
            run_id=run_id,
            status="succeeded",
            stop_reason="completed",
            response=response,
            attempt_run_ids=(run_id,),
        )

    def run_with_recomposition(
        self,
        start_result: RuntimeStartResult,
        *,
        task: Mapping[str, Any],
        entrypoint: RuntimeEntryPoint,
        composition_context_response: Mapping[str, Any] | None = None,
    ) -> RuntimeLoopResult:
        attempt_run_ids: list[str] = []
        recomposed_profile_ids: list[str] = []
        current_start_result = start_result

        while True:
            attempt_run_ids.append(current_start_result.run_id)
            try:
                result = self.run(current_start_result)
            except RuntimeLoopError as error:
                if error.recomposition_request is None:
                    raise
                current_start_result = entrypoint.continue_recomposition(
                    task,
                    recomposition_request=error.recomposition_request,
                    composition_context_response=composition_context_response,
                )
                recomposed_profile_ids.append(current_start_result.profile["id"])
                continue

            response = dict(result.response)
            response["attempt_run_ids"] = list(attempt_run_ids)
            response["recomposed_profile_ids"] = list(recomposed_profile_ids)
            return RuntimeLoopResult(
                run_id=result.run_id,
                status=result.status,
                stop_reason=result.stop_reason,
                response=response,
                attempt_run_ids=tuple(attempt_run_ids),
                recomposed_profile_ids=tuple(recomposed_profile_ids),
            )

    def _handle_runtime_error(
        self,
        *,
        run_id: str,
        start_result: RuntimeStartResult,
        error: Exception,
        enforcer: RuntimeProfileEnforcer,
        redact_sensitive_data: bool,
    ) -> tuple[str, RecompositionRequest | None]:
        profile = start_result.profile
        recomposition_reason = _recomposition_reason(error)
        if recomposition_reason is not None and _profile_allows_recomposition(profile, error):
            try:
                enforcer.record_recomposition_request()
            except ProfileEnforcementError as budget_error:
                return (
                    self._fail_run(
                        run_id=run_id,
                        error=budget_error,
                        enforcer=enforcer,
                        redact_sensitive_data=redact_sensitive_data,
                    ),
                    None,
                )
            recomposition_request = RecompositionRequest(
                source_run_id=run_id,
                task_id=start_result.analyzed_task.task_id,
                parent_profile_id=profile["id"],
                requested_profile_generation=int(profile["profile_generation"]) + 1,
                recomposition_reason=recomposition_reason,
            )
            self.recorder.record_event(
                run_id=run_id,
                event_type="recomposition_requested",
                actor_role="composer",
                result=recomposition_request.as_event_result(),
                stop_reason="needs_recomposition",
                redact_sensitive_data=redact_sensitive_data,
            )
            self.recorder.complete_run(
                run_id=run_id,
                status="failed",
                stop_reason="needs_recomposition",
                tokens_used_total=enforcer.tokens_used,
            )
            return "needs_recomposition", recomposition_request

        return (
            self._fail_run(
                run_id=run_id,
                error=error,
                enforcer=enforcer,
                redact_sensitive_data=redact_sensitive_data,
            ),
            None,
        )

    def _fail_run(
        self,
        *,
        run_id: str,
        error: Exception,
        enforcer: RuntimeProfileEnforcer,
        redact_sensitive_data: bool,
    ) -> str:
        stop_reason = str(getattr(error, "stop_reason", "tool_error"))
        error_code = getattr(error, "code", None)
        classification = classify_runtime_failure(
            error=error,
            stop_reason=stop_reason,
            error_code=str(error_code) if isinstance(error_code, str) else None,
            enforcer_counters={
                "tool_calls": enforcer.tool_calls,
                "tokens_used": enforcer.tokens_used,
            },
        )
        classification = apply_optional_llm_judge(
            classification,
            enabled=self.enable_llm_error_judge,
            judge=self.llm_error_judge,
            context={
                "run_id": run_id,
                "status": "failed",
                "stop_reason": stop_reason,
                "error_type": type(error).__name__,
            },
        )
        self.recorder.record_event(
            run_id=run_id,
            event_type="runtime_failed",
            actor_role="policy_engine" if stop_reason != "tool_error" else "executor",
            result={
                "error": str(error),
                "error_type": type(error).__name__,
                "error_classification": classification.as_dict(),
            },
            stop_reason=stop_reason,  # type: ignore[arg-type]
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.complete_run(
            run_id=run_id,
            status="failed",
            stop_reason=stop_reason,  # type: ignore[arg-type]
            tokens_used_total=enforcer.tokens_used,
        )
        return stop_reason

    def _context_step(
        self,
        run_id: str,
        profile: Mapping[str, Any],
        redact_sensitive_data: bool,
        enforcer: RuntimeProfileEnforcer,
    ) -> Mapping[str, Any]:
        enforcer.check_duration()
        step = self.recorder.start_step(run_id=run_id, step_index=0, kind="context")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="context_manager",
            planned_action={"phase": "context"},
            redact_sensitive_data=redact_sensitive_data,
        )
        context = RuntimeContextManager(
            enforcer=enforcer,
            control_plane_client=self.control_plane_client,
        ).load(profile, query=str(profile["objective"]))
        self.recorder.checkpoint(
            run_id=run_id,
            step_id=str(step["id"]),
            phase="context",
            state=context,
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="context_manager",
            result=context,
            stop_reason="completed",
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.complete_step(
            step_id=str(step["id"]),
            status="succeeded",
            stop_reason="completed",
        )
        return context

    def _planner_step(
        self,
        run_id: str,
        profile: Mapping[str, Any],
        context: Mapping[str, Any],
        redact_sensitive_data: bool,
        enforcer: RuntimeProfileEnforcer,
    ) -> Mapping[str, Any]:
        enforcer.check_duration()
        step = self.recorder.start_step(run_id=run_id, step_index=1, kind="planner")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="planner",
            planned_action={"phase": "planner", "context_keys": sorted(context)},
            redact_sensitive_data=redact_sensitive_data,
        )
        plan = _plan_for_profile(
            profile,
            enforcer=enforcer,
            skill_handlers=self.skill_handlers,
        )
        self.recorder.checkpoint(
            run_id=run_id,
            step_id=str(step["id"]),
            phase="planner",
            state=plan,
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="planner",
            result=plan,
            stop_reason="completed",
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.complete_step(
            step_id=str(step["id"]),
            status="succeeded",
            stop_reason="completed",
        )
        return plan

    def _executor_step(
        self,
        run_id: str,
        profile: Mapping[str, Any],
        plan: Mapping[str, Any],
        redact_sensitive_data: bool,
        enforcer: RuntimeProfileEnforcer,
    ) -> Mapping[str, Any]:
        enforcer.check_duration()
        step = self.recorder.start_step(run_id=run_id, step_index=2, kind="executor")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="executor",
            planned_action=plan,
            redact_sensitive_data=redact_sensitive_data,
        )
        gateway = ToolGateway(
            profile=profile,
            run_id=run_id,
            step_id=str(step["id"]),
            recorder=self.recorder,
            repository_root=self.repository_root,
            enforcer=enforcer,
            redact_sensitive_data=redact_sensitive_data,
        )
        tool_results = []
        try:
            for action in plan.get("actions", []):
                if not isinstance(action, Mapping):
                    continue
                tool_name = str(action["tool"])
                payload = action.get("payload", {})
                if not isinstance(payload, Mapping):
                    payload = {}
                result = gateway.invoke(tool_name, payload)
                tool_results.append(
                    {
                        "id": result.id,
                        "tool_name": result.tool_name,
                        "status": result.status,
                        "output_uri": result.output_uri,
                    }
                )
        except (ToolDeniedError, ToolExecutionError) as error:
            stop_reason = str(getattr(error, "stop_reason", "tool_error"))
            self.recorder.record_event(
                run_id=run_id,
                step_id=str(step["id"]),
                event_type="step_completed",
                actor_role="executor",
                result={"status": "failed", "error": str(error)},
                stop_reason=stop_reason,  # type: ignore[arg-type]
                redact_sensitive_data=redact_sensitive_data,
            )
            self.recorder.complete_step(
                step_id=str(step["id"]),
                status="failed",
                stop_reason=stop_reason,  # type: ignore[arg-type]
            )
            raise
        execution = {
            "strategy": plan.get("strategy", "generic"),
            "tool_results": tool_results,
        }
        self.recorder.checkpoint(
            run_id=run_id,
            step_id=str(step["id"]),
            phase="executor",
            state=execution,
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="executor",
            result=execution,
            stop_reason="completed",
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.complete_step(
            step_id=str(step["id"]),
            status="succeeded",
            stop_reason="completed",
        )
        return execution

    def _validator_step(
        self,
        run_id: str,
        task_id: str,
        profile: Mapping[str, Any],
        context: Mapping[str, Any],
        plan: Mapping[str, Any],
        execution: Mapping[str, Any],
        redact_sensitive_data: bool,
        enforcer: RuntimeProfileEnforcer,
    ) -> Mapping[str, Any]:
        enforcer.check_duration()
        step = self.recorder.start_step(run_id=run_id, step_index=3, kind="validator")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="validator",
            planned_action={"phase": "validator", "validators": profile["validators"]},
            redact_sensitive_data=redact_sensitive_data,
        )
        response = _runtime_response(
            run_id=run_id,
            task_id=task_id,
            profile=profile,
            context=context,
            plan=plan,
            execution=execution,
        )
        outcomes = RuntimeValidatorFramework().validate(
            profile=profile,
            execution=execution,
            response=response,
        )
        for outcome in outcomes:
            findings_uri = self.artifacts.write_json(
                ("traces", run_id, "validation", outcome.validator_id),
                outcome.findings,
                redact=redact_sensitive_data,
            )
            validation_id = slug_id(f"{run_id}-{outcome.validator_id}", prefix="validation")
            self.store.insert_validation_result(
                {
                    "id": validation_id,
                    "run_id": run_id,
                    "step_id": str(step["id"]),
                    "validator_id": outcome.validator_id,
                    "status": outcome.status,
                    "findings_uri": findings_uri,
                    "created_at": iso_timestamp(self.recorder.clock()),
                }
            )
            self.recorder.record_event(
                run_id=run_id,
                step_id=str(step["id"]),
                event_type="validator_executed",
                actor_role="validator",
                execution={"validation_result_id": validation_id},
                result={"status": outcome.status, "findings_uri": findings_uri},
                stop_reason="validator_failed" if outcome.status == "failed" else None,
                redact_sensitive_data=redact_sensitive_data,
            )
        try:
            assert_validation_passed(outcomes)
        except RuntimeValidationError:
            self.recorder.record_event(
                run_id=run_id,
                step_id=str(step["id"]),
                event_type="step_completed",
                actor_role="validator",
                result={"status": "failed"},
                stop_reason="validator_failed",
                redact_sensitive_data=redact_sensitive_data,
            )
            self.recorder.complete_step(
                step_id=str(step["id"]),
                status="failed",
                stop_reason="validator_failed",
            )
            raise
        self.recorder.checkpoint(
            run_id=run_id,
            step_id=str(step["id"]),
            phase="validator",
            state=response,
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="validator",
            result=response,
            stop_reason="completed",
            redact_sensitive_data=redact_sensitive_data,
        )
        self.recorder.complete_step(
            step_id=str(step["id"]),
            status="succeeded",
            stop_reason="completed",
        )
        return response


def _profile_allows_recomposition(profile: Mapping[str, Any], error: Exception) -> bool:
    failure_policy = profile.get("failure_policy", {})
    if not isinstance(failure_policy, Mapping):
        return False
    policy_field = _failure_policy_field(error)
    if policy_field is None:
        return False
    return failure_policy.get(policy_field) == "recompose_once"


def _failure_policy_field(error: Exception) -> str | None:
    stop_reason = str(getattr(error, "stop_reason", ""))
    if isinstance(error, RuntimeValidationError):
        return "on_validator_failure"
    if stop_reason == "policy_denied":
        return "on_policy_denial"
    if stop_reason.startswith("max_"):
        return "on_budget_exhausted"
    return None


def _recomposition_reason(error: Exception) -> str | None:
    stop_reason = str(getattr(error, "stop_reason", ""))
    if isinstance(error, RuntimeValidationError):
        return "validator_failure"
    if stop_reason == "policy_denied":
        return "missing_capability"
    if stop_reason.startswith("max_"):
        return "budget_exhausted"
    return None


def _task_type(profile: Mapping[str, Any]) -> str:
    task_type = str(profile.get("task_type", "general-task"))
    if task_type in SUPPORTED_RUNTIME_TASK_TYPES:
        return task_type
    return "general-task"


def _plan_for_profile(
    profile: Mapping[str, Any],
    *,
    enforcer: RuntimeProfileEnforcer,
    skill_handlers: SkillHandlerRegistry,
) -> dict[str, Any]:
    task_type = _task_type(profile)
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


def _runtime_response(
    *,
    run_id: str,
    task_id: str,
    profile: Mapping[str, Any],
    context: Mapping[str, Any],
    plan: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    task_type = _task_type(profile)
    runtime_output = _runtime_output(
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


def _runtime_output(
    *,
    task_type: str,
    context: Mapping[str, Any],
    plan: Mapping[str, Any],
    execution: Mapping[str, Any],
) -> dict[str, Any]:
    tool_artifacts = _tool_artifacts(execution)
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
        retrieval_artifacts = _retrieval_artifacts(context)
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


def _tool_artifacts(execution: Mapping[str, Any]) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for result in execution.get("tool_results", []):
        if not isinstance(result, Mapping):
            continue
        output_uri = result.get("output_uri")
        if isinstance(output_uri, str) and output_uri:
            artifacts.append({"kind": "tool-output", "uri": output_uri})
    return artifacts


def _retrieval_artifacts(context: Mapping[str, Any]) -> list[dict[str, str]]:
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
