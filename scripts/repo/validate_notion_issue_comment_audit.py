from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

COVERED_STATUSES = {"covered", "backfilled"}
TRACKED_FOLLOW_UP = "tracked_follow_up"
REQUIRED_TOP_LEVEL_FIELDS = (
    "audit_version",
    "audited_at",
    "database",
    "scope",
    "criteria",
    "summary",
    "issues",
)


def validate_audit(audit: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in audit:
            failures.append(f"Missing required top-level field: {field}.")

    if audit.get("audit_version") != "1.0":
        failures.append("audit_version must be 1.0.")
    if audit.get("database") != "SCAS - Issues & Open Questions":
        failures.append("database must be SCAS - Issues & Open Questions.")

    criteria = audit.get("criteria", {})
    if isinstance(criteria, Mapping):
        for key in (
            "requires_page_level_comment",
            "requires_task_description",
            "allows_retrospective_backfill",
        ):
            if criteria.get(key) is not True:
                failures.append(f"criteria.{key} must be true.")
    else:
        failures.append("criteria must be an object.")

    issues = audit.get("issues")
    if not isinstance(issues, list) or not issues:
        failures.append("Audit must contain at least one issue entry.")
        return failures

    covered_count = 0
    backfilled_count = 0
    tracked_follow_up_count = 0

    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, Mapping):
            failures.append(f"issues[{index}] must be an object.")
            continue

        topic = str(issue.get("topic", f"issues[{index}]"))
        coverage_status = issue.get("coverage_status")
        has_comment = issue.get("has_task_describing_comment")
        comment_summary = str(issue.get("comment_summary", "")).strip()

        if coverage_status in COVERED_STATUSES:
            covered_count += 1
            if coverage_status == "backfilled":
                backfilled_count += 1
            if has_comment is not True:
                failures.append(f"{topic}: covered issues must have a task-describing comment.")
        elif coverage_status == TRACKED_FOLLOW_UP:
            tracked_follow_up_count += 1
            if not str(issue.get("follow_up", "")).strip():
                failures.append(f"{topic}: tracked follow-up entries must describe the follow-up.")
        else:
            failures.append(f"{topic}: unsupported coverage_status {coverage_status!r}.")

        if not comment_summary:
            failures.append(f"{topic}: comment_summary is required.")

    summary = audit.get("summary", {})
    if isinstance(summary, Mapping):
        expected_pairs = {
            "audited_issue_count": len(issues),
            "comment_covered_count": covered_count,
            "backfilled_count": backfilled_count,
            "tracked_follow_up_count": tracked_follow_up_count,
        }
        for key, expected in expected_pairs.items():
            if summary.get(key) != expected:
                failures.append(f"summary.{key} must be {expected}.")

    return failures


def load_audit(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Audit file must contain a JSON object.")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a SCAS Notion issue comment coverage audit summary."
    )
    parser.add_argument("audit_path", type=Path, help="Path to the audit JSON file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        audit = load_audit(args.audit_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    failures = validate_audit(audit)
    if failures:
        for failure in failures:
            print(f"error: {failure}", file=sys.stderr)
        return 1

    print(f"Validated {len(audit['issues'])} Notion issue comment audit entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
