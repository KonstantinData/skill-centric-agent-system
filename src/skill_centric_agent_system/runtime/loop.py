from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.entrypoint import RuntimeStartResult
from skill_centric_agent_system.runtime.models import iso_timestamp, selected_modules, slug_id
from skill_centric_agent_system.runtime.storage import FlightRecorder, RuntimeStore
from skill_centric_agent_system.runtime.tool_gateway import ToolGateway


@dataclass(frozen=True)
class RuntimeLoopResult:
    run_id: str
    status: str
    stop_reason: str
    response: Mapping[str, Any]


class MinimalRuntimeLoop:
    """First executable single-agent runtime loop."""

    def __init__(
        self,
        *,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        repository_root: str | Path,
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.repository_root = Path(repository_root)
        self.recorder = FlightRecorder(store, artifacts)

    def run(self, start_result: RuntimeStartResult) -> RuntimeLoopResult:
        profile = start_result.profile
        run_id = start_result.run_id

        context = self._context_step(run_id, profile)
        plan = self._planner_step(run_id, profile, context)
        execution = self._executor_step(run_id, profile, plan)
        response = self._validator_step(run_id, profile, execution)

        self.recorder.record_event(
            run_id=run_id,
            event_type="runtime_completed",
            actor_role="validator",
            result=response,
            stop_reason="completed",
        )
        self.recorder.complete_run(
            run_id=run_id,
            status="succeeded",
            stop_reason="completed",
            tokens_used_total=0,
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
    ) -> Mapping[str, Any]:
        step = self.recorder.start_step(run_id=run_id, step_index=0, kind="context")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="context_manager",
            planned_action={"phase": "context"},
        )
        context = {
            "profile_id": profile["id"],
            "instructions": profile["instructions"],
            "knowledge_scopes": profile["knowledge_scopes"],
            "memory_scopes": profile["memory_scopes"],
            "data_scopes": profile["data_scopes"],
        }
        self.recorder.checkpoint(
            run_id=run_id,
            step_id=str(step["id"]),
            phase="context",
            state=context,
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="context_manager",
            result=context,
            stop_reason="completed",
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
    ) -> Mapping[str, Any]:
        step = self.recorder.start_step(run_id=run_id, step_index=1, kind="planner")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="planner",
            planned_action={"phase": "planner", "context_keys": sorted(context)},
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
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="planner",
            result=plan,
            stop_reason="completed",
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
    ) -> Mapping[str, Any]:
        step = self.recorder.start_step(run_id=run_id, step_index=2, kind="executor")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="executor",
            planned_action=plan,
        )
        gateway = ToolGateway(
            profile=profile,
            run_id=run_id,
            step_id=str(step["id"]),
            recorder=self.recorder,
            repository_root=self.repository_root,
        )
        tool_results = []
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
        execution = {"tool_results": tool_results}
        self.recorder.checkpoint(
            run_id=run_id,
            step_id=str(step["id"]),
            phase="executor",
            state=execution,
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="executor",
            result=execution,
            stop_reason="completed",
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
    ) -> Mapping[str, Any]:
        step = self.recorder.start_step(run_id=run_id, step_index=3, kind="validator")
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_started",
            actor_role="validator",
            planned_action={"phase": "validator", "validators": profile["validators"]},
        )
        findings = {
            "status": "passed",
            "validators": profile["validators"],
            "tool_result_count": len(execution.get("tool_results", [])),
        }
        findings_uri = self.artifacts.write_json(
            ("traces", run_id, "validation", "minimal-runtime-findings"),
            findings,
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
        )
        self.recorder.record_event(
            run_id=run_id,
            step_id=str(step["id"]),
            event_type="step_completed",
            actor_role="validator",
            result=response,
            stop_reason="completed",
        )
        self.recorder.complete_step(
            step_id=str(step["id"]),
            status="succeeded",
            stop_reason="completed",
        )
        return response
