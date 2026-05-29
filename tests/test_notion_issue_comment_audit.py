from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.repo.validate_notion_issue_comment_audit import validate_audit

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "runbooks" / "notion-issue-tracking.md"
SCHEMA_PATH = REPO_ROOT / "schemas" / "notion-issue-comment-audit.schema.json"
EXAMPLE_PATH = REPO_ROOT / "examples" / "repo" / "notion-issue-comment-audit.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_notion_issue_tracking_standard_is_documented() -> None:
    doc = DOC_PATH.read_text(encoding="utf-8")
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Every `SCAS - Issues & Open Questions` page" in doc
    assert "page-level comment" in doc
    assert "task-describing comment" in agents
    assert "docs/runbooks/notion-issue-tracking.md" in readme


def test_notion_issue_comment_audit_schema_and_example_are_valid() -> None:
    schema = load_json(SCHEMA_PATH)
    example = load_json(EXAMPLE_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(example)
    assert validate_audit(example) == []


def test_notion_issue_comment_audit_rejects_missing_comment() -> None:
    audit = load_json(EXAMPLE_PATH)
    broken = deepcopy(audit)
    broken["issues"][0]["has_task_describing_comment"] = False

    failures = validate_audit(broken)

    assert any("task-describing comment" in failure for failure in failures)


def test_notion_issue_comment_audit_rejects_stale_summary_counts() -> None:
    audit = load_json(EXAMPLE_PATH)
    broken = deepcopy(audit)
    broken["summary"]["comment_covered_count"] = 99

    failures = validate_audit(broken)

    assert any("summary.comment_covered_count" in failure for failure in failures)


def test_notion_issue_comment_audit_requires_follow_up_for_tracked_gap() -> None:
    audit = load_json(EXAMPLE_PATH)
    tracked = deepcopy(audit)
    tracked["issues"][0]["coverage_status"] = "tracked_follow_up"
    tracked["issues"][0]["has_task_describing_comment"] = False
    tracked["summary"]["comment_covered_count"] = 2
    tracked["summary"]["tracked_follow_up_count"] = 1

    failures = validate_audit(tracked)

    assert any("tracked follow-up" in failure for failure in failures)

