from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from skill_centric_agent_system.runtime.models import iso_timestamp, slug_id
from skill_centric_agent_system.runtime.storage import FlightRecorder


class ToolDeniedError(PermissionError):
    """Raised when the runtime profile does not allow a tool."""


class ToolExecutionError(RuntimeError):
    """Raised when an allowed tool fails."""


class ToolAdapter(Protocol):
    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...


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
        redact_sensitive_data: bool = True,
    ) -> None:
        self.profile = profile
        self.run_id = run_id
        self.step_id = step_id
        self.recorder = recorder
        self.repository_root = Path(repository_root).resolve()
        self.adapters = dict(adapters or _default_adapters(self.repository_root))
        self.redact_sensitive_data = redact_sensitive_data
        self._invocation_index = 0

    def invoke(
        self,
        tool_name: str,
        payload: Mapping[str, Any],
    ) -> ToolInvocationResult:
        if tool_name not in self.profile.get("tools", []):
            self.recorder.record_event(
                run_id=self.run_id,
                step_id=self.step_id,
                event_type="access_attempted",
                actor_role="policy_engine",
                planned_action={"tool_name": tool_name, "payload": dict(payload)},
                result={"effect": "deny", "reason": "tool_not_in_runtime_profile"},
                stop_reason="policy_denied",
                redact_sensitive_data=self.redact_sensitive_data,
            )
            raise ToolDeniedError(f"Tool is not allowed by runtime profile: {tool_name}")

        adapter = self.adapters.get(tool_name)
        if adapter is None:
            raise ToolExecutionError(f"No adapter is registered for tool: {tool_name}")

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
            raise ToolExecutionError(f"Tool {tool_name} failed: {output['error']}")
        return result


class FilesystemReadAdapter:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root

    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        relative_path = str(payload.get("path") or "")
        if not relative_path:
            raise ValueError("filesystem-read requires a path.")
        max_bytes = int(payload.get("max_bytes") or 20000)
        target = (self.repository_root / relative_path).resolve()
        target.relative_to(self.repository_root)
        if not target.is_file():
            raise FileNotFoundError(str(target))
        data = target.read_bytes()[:max_bytes]
        return {
            "path": str(target),
            "bytes_read": len(data),
            "content": data.decode("utf-8", errors="replace"),
            "truncated": target.stat().st_size > max_bytes,
        }


class GitReadAdapter:
    ALLOWED_SUBCOMMANDS = {"diff", "log", "show", "status"}

    def __init__(self, repository_root: Path, *, timeout_seconds: int = 20) -> None:
        self.repository_root = repository_root
        self.timeout_seconds = timeout_seconds

    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        args = payload.get("args")
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            raise ValueError("git-read requires args as a string array.")
        if not args or args[0] not in self.ALLOWED_SUBCOMMANDS:
            allowed = ", ".join(sorted(self.ALLOWED_SUBCOMMANDS))
            raise ValueError(f"git-read subcommand must be one of: {allowed}.")
        completed = subprocess.run(
            ["git", *args],
            cwd=self.repository_root,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        return {
            "args": args,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }


class TestRunnerAdapter:
    def __init__(self, repository_root: Path, *, timeout_seconds: int = 120) -> None:
        self.repository_root = repository_root
        self.timeout_seconds = timeout_seconds

    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        pytest_args = payload.get("pytest_args", [])
        if not isinstance(pytest_args, list) or not all(
            isinstance(arg, str) for arg in pytest_args
        ):
            raise ValueError("test-runner requires pytest_args as a string array.")
        completed = subprocess.run(
            ["python", "-m", "pytest", *pytest_args],
            cwd=self.repository_root,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        return {
            "command": ["python", "-m", "pytest", *pytest_args],
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }


def _default_adapters(repository_root: Path) -> Mapping[str, ToolAdapter]:
    return {
        "filesystem-read": FilesystemReadAdapter(repository_root),
        "git-read": GitReadAdapter(repository_root),
        "test-runner": TestRunnerAdapter(repository_root),
    }
