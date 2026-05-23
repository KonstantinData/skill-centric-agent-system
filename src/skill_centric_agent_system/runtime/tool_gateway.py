from __future__ import annotations

import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from skill_centric_agent_system.runtime.enforcement import (
    ProfileEnforcementError,
    RuntimeProfileEnforcer,
)
from skill_centric_agent_system.runtime.models import iso_timestamp, slug_id
from skill_centric_agent_system.runtime.storage import FlightRecorder


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
        enforcer: RuntimeProfileEnforcer | None = None,
        redact_sensitive_data: bool = True,
    ) -> None:
        self.profile = profile
        self.run_id = run_id
        self.step_id = step_id
        self.recorder = recorder
        self.repository_root = Path(repository_root).resolve()
        self.adapters = dict(adapters or _default_adapters(self.repository_root))
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
                required_data_scopes=_tool_required_data_scopes(tool_name),
                tool_risk_level=_tool_risk_level(tool_name),
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
                "risk_level": _tool_risk_level(tool_name),
                "required_data_scopes": list(_tool_required_data_scopes(tool_name)),
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
        self.recorder.record_event(
            run_id=self.run_id,
            step_id=self.step_id,
            event_type="access_attempted",
            actor_role="policy_engine",
            planned_action={"tool_name": tool_name, "payload": dict(payload)},
            result={"effect": "deny", "reason": error.code},
            stop_reason=error.stop_reason,
            redact_sensitive_data=self.redact_sensitive_data,
        )


class FilesystemReadAdapter:
    MAX_FILE_BYTES = 100_000

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root

    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        relative_path = str(payload.get("path") or "")
        if not relative_path:
            raise ValueError("filesystem-read requires a path.")
        requested_max_bytes = int(payload.get("max_bytes") or 20000)
        if requested_max_bytes < 0:
            raise ValueError("filesystem-read max_bytes must be non-negative.")
        max_bytes = min(requested_max_bytes, self.MAX_FILE_BYTES)
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


class FilesystemListAdapter:
    MAX_ENTRIES = 500

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root

    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        relative_path = str(payload.get("path") or ".")
        requested_max_entries = int(payload.get("max_entries") or 100)
        if requested_max_entries < 0:
            raise ValueError("filesystem-list max_entries must be non-negative.")
        max_entries = min(requested_max_entries, self.MAX_ENTRIES)
        target = (self.repository_root / relative_path).resolve()
        target.relative_to(self.repository_root)
        if not target.is_dir():
            raise NotADirectoryError(str(target))

        entries = []
        for child in sorted(target.iterdir(), key=lambda item: item.name.casefold())[:max_entries]:
            stat = child.stat()
            entries.append(
                {
                    "name": child.name,
                    "path": child.relative_to(self.repository_root).as_posix(),
                    "kind": "directory" if child.is_dir() else "file",
                    "size_bytes": stat.st_size if child.is_file() else None,
                }
            )
        return {
            "path": str(target),
            "entry_count": len(entries),
            "entries": entries,
            "truncated": sum(1 for _ in target.iterdir()) > max_entries,
        }


class GitReadAdapter:
    ALLOWED_SUBCOMMANDS = {"diff", "log", "show", "status"}
    BLOCKED_ARGS = {"-c", "--config-env", "--exec-path", "--git-dir", "--work-tree"}
    MAX_OUTPUT_BYTES = 50_000

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
        _reject_blocked_args("git-read", args, self.BLOCKED_ARGS)
        completed = subprocess.run(
            ["git", *args],
            cwd=self.repository_root,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        stdout, stdout_truncated = _limit_text(completed.stdout, self.MAX_OUTPUT_BYTES)
        stderr, stderr_truncated = _limit_text(completed.stderr, self.MAX_OUTPUT_BYTES)
        return {
            "args": args,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


class TestRunnerAdapter:
    BLOCKED_ARGS = {"--override-ini", "--basetemp"}
    MAX_OUTPUT_BYTES = 80_000

    def __init__(self, repository_root: Path, *, timeout_seconds: int = 120) -> None:
        self.repository_root = repository_root
        self.timeout_seconds = timeout_seconds

    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        pytest_args = payload.get("pytest_args", [])
        if not isinstance(pytest_args, list) or not all(
            isinstance(arg, str) for arg in pytest_args
        ):
            raise ValueError("test-runner requires pytest_args as a string array.")
        _reject_blocked_args("test-runner", pytest_args, self.BLOCKED_ARGS)
        completed = subprocess.run(
            ["python", "-m", "pytest", *pytest_args],
            cwd=self.repository_root,
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        stdout, stdout_truncated = _limit_text(completed.stdout, self.MAX_OUTPUT_BYTES)
        stderr, stderr_truncated = _limit_text(completed.stderr, self.MAX_OUTPUT_BYTES)
        return {
            "command": ["python", "-m", "pytest", *pytest_args],
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
        }


def _default_adapters(repository_root: Path) -> Mapping[str, ToolAdapter]:
    return {
        "filesystem-read": FilesystemReadAdapter(repository_root),
        "filesystem-list": FilesystemListAdapter(repository_root),
        "git-read": GitReadAdapter(repository_root),
        "test-runner": TestRunnerAdapter(repository_root),
    }


def _tool_required_data_scopes(tool_name: str) -> tuple[str, ...]:
    if tool_name in {"filesystem-read", "filesystem-list", "git-read", "test-runner"}:
        return ("repository-readonly",)
    return ()


def _tool_risk_level(tool_name: str) -> str:
    risk_levels = {
        "filesystem-read": "low",
        "filesystem-list": "low",
        "git-read": "low",
        "test-runner": "medium",
    }
    return risk_levels.get(tool_name, "high")


def _reject_blocked_args(tool_name: str, args: list[str], blocked_args: set[str]) -> None:
    for arg in args:
        if "\x00" in arg:
            raise ValueError(f"{tool_name} arguments must not contain NUL bytes.")
        for blocked in blocked_args:
            if arg == blocked or arg.startswith(blocked + "="):
                raise ValueError(f"{tool_name} argument is not allowed: {blocked}.")


def _limit_text(value: str, max_bytes: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= max_bytes:
        return value, False
    limited = encoded[:max_bytes].decode("utf-8", errors="replace")
    return limited, True
