from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime.capability_gaps import (
    capability_gap_from_enforcement_error,
)
from skill_centric_agent_system.runtime.enforcement import (
    ProfileEnforcementError,
    RuntimeProfileEnforcer,
)
from skill_centric_agent_system.runtime.models import iso_timestamp, slug_id
from skill_centric_agent_system.runtime.storage import FlightRecorder
from skill_centric_agent_system.runtime.tool_adapters import (
    FilesystemListAdapter,
    FilesystemReadAdapter,
    FilesystemWriteAdapter,
    GitReadAdapter,
    TestRunnerAdapter,
    ToolAdapter,
    default_tool_adapters,
)
from skill_centric_agent_system.runtime.tool_policies import (
    tool_required_data_scopes,
    tool_required_policies,
    tool_risk_level,
)

__all__ = [
    "FilesystemListAdapter",
    "FilesystemReadAdapter",
    "FilesystemWriteAdapter",
    "GitReadAdapter",
    "TestRunnerAdapter",
    "ToolAdapter",
    "ToolDeniedError",
    "ToolExecutionError",
    "ToolGateway",
    "ToolInvocationResult",
]


class ToolDeniedError(PermissionError):
    """Raised when the runtime profile does not allow a tool."""

    def __init__(self, message: str, *, stop_reason: str = "policy_denied") -> None:
        super().__init__(message)
        self.stop_reason = stop_reason


class ToolExecutionError(RuntimeError):
    """Raised when an allowed tool fails."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "tool_execution_failed",
        stop_reason: str = "tool_error",
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stop_reason = stop_reason
        self.details = dict(details or {})


@dataclass(frozen=True)
class ToolInvocationResult:
    id: str
    tool_name: str
    status: str
    input_uri: str
    output_uri: str
    output: Mapping[str, Any]


class ToolGateway:
    """Invoke tools only when explicitly allowed by the Runtime Agent Profile."""

    def __init__(
        self,
        *,
        profile: Mapping[str, Any],
        run_id: str,
        step_id: str,
        recorder: FlightRecorder,
        repository_root: str | Path,
        adapters: Mapping[str, ToolAdapter] | None = None,
        enforcer: RuntimeProfileEnforcer | None = None,
        redact_sensitive_data: bool = True,
    ) -> None:
        self.profile = profile
        self.run_id = run_id
        self.step_id = step_id
        self.recorder = recorder
        self.repository_root = Path(repository_root).resolve()
        self.adapters = dict(adapters or default_tool_adapters(self.repository_root))
        self.enforcer = enforcer or RuntimeProfileEnforcer(profile)
        self.redact_sensitive_data = redact_sensitive_data
        self._invocation_index = 0

    def invoke(
        self,
        tool_name: str,
        payload: Mapping[str, Any],
    ) -> ToolInvocationResult:
        try:
            self.enforcer.record_tool_invocation(
                tool_name,
                required_data_scopes=tool_required_data_scopes(tool_name),
                required_policies=tool_required_policies(tool_name),
                tool_risk_level=tool_risk_level(tool_name),
            )
        except ProfileEnforcementError as error:
            self._record_denied_access(tool_name, payload, error)
            raise ToolDeniedError(str(error), stop_reason=error.stop_reason) from error

        adapter = self.adapters.get(tool_name)
        if adapter is None:
            raise ToolExecutionError(
                f"No adapter is registered for tool: {tool_name}",
                code="tool_adapter_missing",
            )

        invocation_id = slug_id(
            f"{self.run_id}-{tool_name}-{self._invocation_index}",
            prefix="tool",
        )
        self._invocation_index += 1
        input_uri = self.recorder.artifacts.write_json(
            ("tool_outputs", self.run_id, f"{invocation_id}-input"),
            {"tool_name": tool_name, "payload": dict(payload)},
            redact=self.redact_sensitive_data,
        )
        started_at = iso_timestamp(self.recorder.clock())
        self.recorder.record_event(
            run_id=self.run_id,
            step_id=self.step_id,
            event_type="access_attempted",
            actor_role="policy_engine",
            planned_action={"tool_name": tool_name, "input_uri": input_uri},
            result={
                "effect": "allow",
                "risk_level": tool_risk_level(tool_name),
                "required_data_scopes": list(tool_required_data_scopes(tool_name)),
                "required_policies": list(tool_required_policies(tool_name)),
            },
            redact_sensitive_data=self.redact_sensitive_data,
        )
        self.recorder.record_event(
            run_id=self.run_id,
            step_id=self.step_id,
            event_type="tool_invocation_started",
            actor_role="executor",
            planned_action={"tool_name": tool_name, "input_uri": input_uri},
            redact_sensitive_data=self.redact_sensitive_data,
        )

        try:
            output = dict(adapter.invoke(payload))
            status = "succeeded"
            stop_reason = None
        except Exception as error:
            output = {"error": str(error), "error_type": type(error).__name__}
            status = "failed"
            stop_reason = "tool_error"

        output_uri = self.recorder.artifacts.write_json(
            ("tool_outputs", self.run_id, f"{invocation_id}-output"),
            {"tool_name": tool_name, "status": status, "output": output},
            redact=self.redact_sensitive_data,
        )
        completed_at = iso_timestamp(self.recorder.clock())
        record = self.recorder.store.insert_tool_invocation(
            {
                "id": invocation_id,
                "run_id": self.run_id,
                "step_id": self.step_id,
                "tool_name": tool_name,
                "status": status,
                "input_uri": input_uri,
                "output_uri": output_uri,
                "started_at": started_at,
                "completed_at": completed_at,
            }
        )
        self.recorder.record_event(
            run_id=self.run_id,
            step_id=self.step_id,
            event_type="tool_invocation_completed",
            actor_role="executor",
            execution={"tool_invocation_id": invocation_id, "status": status},
            result={"tool_name": tool_name, "output_uri": output_uri},
            stop_reason=stop_reason,  # type: ignore[arg-type]
            redact_sensitive_data=self.redact_sensitive_data,
        )

        result = ToolInvocationResult(
            id=str(record["id"]),
            tool_name=tool_name,
            status=status,
            input_uri=input_uri,
            output_uri=output_uri,
            output=output,
        )
        if status != "succeeded":
            raise ToolExecutionError(
                f"Tool {tool_name} failed: {output['error']}",
                details=output,
            )
        return result

    def _record_denied_access(
        self,
        tool_name: str,
        payload: Mapping[str, Any],
        error: ProfileEnforcementError,
    ) -> None:
        result: dict[str, Any] = {"effect": "deny", "reason": error.code}
        evidence_uri = self.recorder.artifacts.uri_for(
            ("events", self.run_id, f"{self.step_id}-{tool_name}-access-denied")
        )
        gap_result = capability_gap_from_enforcement_error(
            artifacts=self.recorder.artifacts,
            run_id=self.run_id,
            profile=self.profile,
            source_step_id=self.step_id,
            requested_tool=tool_name,
            error=error,
            evidence_uris=(evidence_uri,),
            known_tool_ids=self.adapters.keys(),
        )
        if gap_result.captured:
            result["capability_gap_candidate_uri"] = gap_result.artifact_uri
        self.recorder.record_event(
            run_id=self.run_id,
            step_id=self.step_id,
            event_type="access_attempted",
            actor_role="policy_engine",
            planned_action={"tool_name": tool_name, "payload": dict(payload)},
            result=result,
            stop_reason=error.stop_reason,
            redact_sensitive_data=self.redact_sensitive_data,
        )
