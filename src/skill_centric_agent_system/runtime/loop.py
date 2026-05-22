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
from skill_centric_agent_system.runtime.entrypoint import RuntimeStartResult
from skill_centric_agent_system.runtime.models import iso_timestamp, selected_modules, slug_id
from skill_centric_agent_system.runtime.policies import profile_redacts_sensitive_data
from skill_centric_agent_system.runtime.storage import FlightRecorder, RuntimeStore
from skill_centric_agent_system.runtime.tool_gateway import (
    ToolDeniedError,
    ToolExecutionError,
    ToolGateway,
)


@dataclass(frozen=True)
class RuntimeLoopResult:
    run_id: str
    status: str
    stop_reason: str
    response: Mapping[str, Any]


class RuntimeLoopError(RuntimeError):
    """Raised when the runtime loop fails closed."""


class MinimalRuntimeLoop:
    """First executable single-agent runtime loop."""

    def __init__(
        self,
        *,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        repository_root: str | Path,
        control_plane_client: RetrievalContextClient | None = None,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.repository_root = Path(repository_root)
        self.control_plane_client = control_plane_client
        self.recorder = FlightRecorder(store, artifacts)

    def run(self, start_result: RuntimeStartResult) -> RuntimeLoopResult:
        profile = start_result.profile
        run_id = start_result.run_id
        redact_sensitive_data = profile_redacts_sensitive_data(profile)
        enforcer = RuntimeProfileEnforcer(profile)

        try:
            enforcer.validate_profile_for_runtime()
            context = self._context_step(run_id, profile, redact_sensitive_data, enforcer)
            plan = self._planner_step(run_id, profile, context, redact_sensitive_data, enforcer)
            execution = self._executor_step(run_id, profile, plan, redact_sensitive_data, enforcer)
            response = self._validator_step(
                run_id,
                profile,
                execution,
                redact_sensitive_data,
                enforcer,
            )
        except (ProfileEnforcementError, ToolDeniedError, ToolExecutionError) as error:
            stop_reason = str(getattr(error, "stop_reason", "tool_error"))
            self.recorder.record_event(
                run_id=run_id,
                event_type="runtime_failed",
                actor_role="policy_engine" if stop_reason != "tool_error" else "executor",
                result={
                    "error": str(error),
                    "error_type": type(error).__name__,
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
            raise RuntimeLoopError(str(error)) from error

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
        )

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
        plan = {
            "objective": profile["objective"],
            "selected_modules": selected_modules(profile),
            "actions": [
                {"tool": "git-read", "payload": {"args": ["status", "--short"]}},
                {"tool": "filesystem-read", "payload": {"path": "README.md", "max_bytes": 4000}},
            ],
        }
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
        execution = {"tool_results": tool_results}
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
        profile: Mapping[str, Any],
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
        findings = {
            "status": "passed",
            "validators": profile["validators"],
            "tool_result_count": len(execution.get("tool_results", [])),
        }
        findings_uri = self.artifacts.write_json(
            ("traces", run_id, "validation", "minimal-runtime-findings"),
            findings,
            redact=redact_sensitive_data,
        )
        validation_id = slug_id(f"{run_id}-minimal-runtime", prefix="validation")
        self.store.insert_validation_result(
            {
                "id": validation_id,
                "run_id": run_id,
                "step_id": str(step["id"]),
                "validator_id": "review-findings-contract",
                "status": "passed",
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
            result={"status": "passed", "findings_uri": findings_uri},
            redact_sensitive_data=redact_sensitive_data,
        )
        response = {
            "run_id": run_id,
            "profile_id": profile["id"],
            "status": "succeeded",
            "summary": "Minimal runtime loop completed with read-only tool execution.",
            "tool_result_count": len(execution.get("tool_results", [])),
        }
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
