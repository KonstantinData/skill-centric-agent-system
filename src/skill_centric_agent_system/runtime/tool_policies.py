from __future__ import annotations


def tool_required_data_scopes(tool_name: str) -> tuple[str, ...]:
    if tool_name in {"filesystem-read", "filesystem-list", "git-read", "test-runner"}:
        return ("repository-readonly",)
    if tool_name == "filesystem-write":
        return ("repository-write",)
    return ()


def tool_required_policies(tool_name: str) -> tuple[str, ...]:
    if tool_name == "filesystem-write":
        return ("write-approval-required",)
    return ()


def tool_risk_level(tool_name: str) -> str:
    risk_levels = {
        "filesystem-read": "low",
        "filesystem-list": "low",
        "filesystem-write": "high",
        "git-read": "low",
        "test-runner": "medium",
    }
    return risk_levels.get(tool_name, "high")
