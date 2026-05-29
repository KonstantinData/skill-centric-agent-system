from __future__ import annotations

from pathlib import Path

import pytest

from scripts.repo.post_merge_cleanup import (
    PostMergeCleanupError,
    build_cleanup_steps,
    build_report,
    validate_merged_pr,
    validate_topic_branch,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "post-merge-lifecycle.md"
SCRIPT_PATH = REPO_ROOT / "scripts" / "repo" / "post_merge_cleanup.py"


def test_post_merge_cleanup_runbook_and_script_exist() -> None:
    assert RUNBOOK_PATH.exists()
    assert SCRIPT_PATH.exists()


def test_post_merge_cleanup_rejects_unmerged_pr() -> None:
    with pytest.raises(PostMergeCleanupError, match="must be merged"):
        validate_merged_pr(
            {
                "state": "OPEN",
                "baseRefName": "main",
                "headRefName": "codex/example",
            },
            expected_base="main",
        )


def test_post_merge_cleanup_refuses_protected_or_non_codex_branches() -> None:
    with pytest.raises(PostMergeCleanupError, match="protected"):
        validate_topic_branch("main", base_branch="main")

    with pytest.raises(PostMergeCleanupError, match="non-codex"):
        validate_topic_branch("feature/example", base_branch="main")


def test_post_merge_cleanup_plan_deletes_branch_only_after_sync_steps() -> None:
    branch = validate_merged_pr(
        {
            "state": "MERGED",
            "baseRefName": "main",
            "headRefName": "codex/example",
        },
        expected_base="main",
    )

    steps = build_cleanup_steps(
        branch=branch,
        base_branch="main",
        remote="origin",
        local_branch_exists=True,
        remote_branch_exists=True,
    )

    assert [step.name for step in steps] == [
        "fetch-prune-before-cleanup",
        "checkout-base",
        "fast-forward-base",
        "delete-local-topic-branch",
        "delete-remote-topic-branch",
        "fetch-prune-after-cleanup",
    ]
    assert steps[3].destructive is True
    assert steps[4].destructive is True


def test_post_merge_cleanup_report_requires_notion_completion() -> None:
    report = build_report(
        mode="dry-run",
        pr_number="10",
        pr_url="https://github.com/KonstantinData/skill-centric-agent-system/pull/10",
        branch="codex/example",
        base_branch="main",
        remote="origin",
        merge_commit="a" * 40,
        steps=(),
    )

    assert report["notion_completion_required"] is True
    assert "PR URL" in report["notion_completion_fields"]
    assert "Feature Backlog" in str(report["notion_completion_note"])
    assert "Issues & Open Questions" in RUNBOOK_PATH.read_text(encoding="utf-8")
