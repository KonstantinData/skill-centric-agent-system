"""Validate the GitHub Actions workflow hardening baseline."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>[^\s#]+)")
FULL_SHA_REF = re.compile(r"@[0-9a-f]{40}$")
DISALLOWED_PATTERNS = (
    re.compile(r"\bpull_request_target\b"),
    re.compile(r"permissions:\s*write-all"),
    re.compile(r"permissions:\s*\{\s*\}"),
)


def action_reference_allowed(reference: str) -> bool:
    if reference.startswith("./") or reference.startswith("../"):
        return True
    if reference.startswith("docker://"):
        return "@sha256:" in reference
    return bool(FULL_SHA_REF.search(reference))


def check_workflow_hardening(workflow_dir: Path) -> list[str]:
    failures: list[str] = []
    workflow_files = sorted(workflow_dir.glob("*.yml"))
    if not workflow_files:
        return [f"{workflow_dir}: no workflow files found"]

    for workflow in workflow_files:
        text = workflow.read_text(encoding="utf-8")
        if "permissions:" not in text:
            failures.append(f"{workflow.as_posix()}: missing permissions block")
        if "timeout-minutes:" not in text:
            failures.append(f"{workflow.as_posix()}: missing job timeout")
        if "concurrency:" not in text:
            failures.append(f"{workflow.as_posix()}: missing concurrency control")
        for pattern in DISALLOWED_PATTERNS:
            if pattern.search(text):
                failures.append(
                    f"{workflow.as_posix()}: matched disallowed pattern {pattern.pattern}"
                )
        for line_number, line in enumerate(text.splitlines(), 1):
            match = USES_PATTERN.match(line)
            if not match:
                continue
            reference = match.group("ref").strip().strip('"').strip("'")
            if not action_reference_allowed(reference):
                failures.append(
                    f"{workflow.as_posix()}:{line_number}: action reference must be pinned "
                    f"to a full SHA or Docker digest: {reference}"
                )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-dir", type=Path, default=Path(".github/workflows"))
    args = parser.parse_args()

    failures = check_workflow_hardening(args.workflow_dir)
    if failures:
        print("Workflow hardening validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Workflow hardening validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
