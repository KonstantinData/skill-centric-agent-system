from __future__ import annotations

import subprocess
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol


class ToolAdapter(Protocol):
    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...


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


class FilesystemWriteAdapter:
    MAX_CONTENT_BYTES = 100_000

    def __init__(self, repository_root: Path) -> None:
        self.repository_root = repository_root

    def invoke(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        if "command" in payload or "shell" in payload:
            raise ValueError("filesystem-write accepts structured write plans, not commands.")

        operation = str(payload.get("operation") or "")
        if operation != "write_text_file":
            raise ValueError("filesystem-write operation must be write_text_file.")

        approval = payload.get("approval")
        if not isinstance(approval, Mapping):
            raise ValueError("filesystem-write requires an approval object.")
        approval_record = _validated_approval(approval)

        rollback = payload.get("rollback")
        if not isinstance(rollback, Mapping):
            raise ValueError("filesystem-write requires rollback metadata.")

        relative_path = str(payload.get("path") or "")
        if not relative_path:
            raise ValueError("filesystem-write requires a path.")
        if "\x00" in relative_path:
            raise ValueError("filesystem-write path must not contain NUL bytes.")
        if Path(relative_path).is_absolute():
            raise ValueError("filesystem-write path must be relative to the repository root.")
        content = payload.get("content")
        if not isinstance(content, str):
            raise ValueError("filesystem-write requires string content.")
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > self.MAX_CONTENT_BYTES:
            raise ValueError("filesystem-write content exceeds the adapter limit.")

        target = (self.repository_root / relative_path).resolve()
        target.relative_to(self.repository_root)
        if target.exists() and not target.is_file():
            raise ValueError("filesystem-write target must be a file path.")

        apply_write_raw = payload.get("apply", False)
        if not isinstance(apply_write_raw, bool):
            raise ValueError("filesystem-write apply must be a boolean.")
        apply_write = apply_write_raw
        previous_bytes = target.read_bytes() if target.exists() else None
        existed_before = previous_bytes is not None
        rollback_strategy = str(rollback.get("strategy") or "")
        expected_strategy = "restore_previous_content" if existed_before else "delete_created_file"
        if rollback_strategy != expected_strategy:
            raise ValueError(
                "filesystem-write rollback strategy must be "
                f"{expected_strategy} for this target."
            )

        if apply_write:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

        return {
            "operation": operation,
            "status": "applied" if apply_write else "planned",
            "path": str(target),
            "bytes_planned": len(content_bytes),
            "content_sha256": sha256(content_bytes).hexdigest(),
            "existed_before": existed_before,
            "previous_content_sha256": (
                sha256(previous_bytes).hexdigest() if previous_bytes is not None else None
            ),
            "approval": approval_record,
            "rollback": {
                "strategy": rollback_strategy,
                "metadata_only": True,
                "reason": str(rollback.get("reason") or ""),
            },
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


def default_tool_adapters(repository_root: Path) -> Mapping[str, ToolAdapter]:
    return {
        "filesystem-read": FilesystemReadAdapter(repository_root),
        "filesystem-list": FilesystemListAdapter(repository_root),
        "filesystem-write": FilesystemWriteAdapter(repository_root),
        "git-read": GitReadAdapter(repository_root),
        "test-runner": TestRunnerAdapter(repository_root),
    }


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


def _validated_approval(approval: Mapping[str, Any]) -> dict[str, str]:
    required_fields = ("approval_id", "approved_by", "approved_at", "policy_id")
    record: dict[str, str] = {}
    for field in required_fields:
        value = str(approval.get(field) or "").strip()
        if not value:
            raise ValueError(f"filesystem-write approval requires {field}.")
        if "\x00" in value:
            raise ValueError("filesystem-write approval values must not contain NUL bytes.")
        record[field] = value
    if record["policy_id"] != "write-approval-required":
        raise ValueError("filesystem-write approval policy_id must be write-approval-required.")
    return record
