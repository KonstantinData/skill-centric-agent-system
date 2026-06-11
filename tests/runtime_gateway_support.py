from __future__ import annotations

from copy import deepcopy
from typing import Any

from tests.test_runtime_tool_gateway_and_loop import PROFILE_EXAMPLE_PATH, load_json


def write_enabled_profile() -> dict[str, Any]:
    profile = deepcopy(load_json(PROFILE_EXAMPLE_PATH))
    profile["task_type"] = "task-execution"
    profile["risk_level"] = "high"
    profile["skills"] = []
    profile["tools"] = ["filesystem-write"]
    profile["knowledge_scopes"] = []
    profile["data_scopes"] = ["repository-write"]
    profile["memory_scopes"] = []
    profile["policies"] = ["write-approval-required"]
    profile["validators"] = ["task-execution-output-contract"]
    profile["module_versions"].update(
        {
            "filesystem-write": "0.1.0",
            "repository-write": "0.1.0",
            "write-approval-required": "0.1.0",
            "task-execution-output-contract": "0.1.0",
        }
    )
    profile["limits"]["max_data_reads"] = 10
    return profile


def approved_write_payload(*, apply: bool = False) -> dict[str, Any]:
    return {
        "operation": "write_text_file",
        "path": "notes/output.txt",
        "content": "approved content\n",
        "apply": apply,
        "approval": {
            "approval_id": "approval-p5-05-fixture",
            "approved_by": "repository-maintainer",
            "approved_at": "2026-05-24T18:00:00Z",
            "policy_id": "write-approval-required",
        },
        "rollback": {
            "strategy": "delete_created_file",
            "reason": "Delete the newly created file if validation fails.",
        },
    }
