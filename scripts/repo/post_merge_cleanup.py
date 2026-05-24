from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

PROTECTED_BRANCHES = {"main", "master", "develop", "dev"}


class PostMergeCleanupError(ValueError):
    """Raised when post-merge cleanup would be unsafe."""


@dataclass(frozen=True)
class CleanupStep:
    name: str
    command: tuple[str, ...]
    destructive: bool = False

    def as_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "command": list(self.command),
            "destructive": self.destructive,
        }


def validate_merged_pr(pr_data: dict[str, Any], *, expected_base: str) -> str:
    if pr_data.get("state") != "MERGED":
        raise PostMergeCleanupError("PR must be merged before branch cleanup.")
    base_ref = str(pr_data.get("baseRefName", expected_base))
    if base_ref != expected_base:
        raise PostMergeCleanupError(
            f"PR base branch {base_ref!r} does not match expected base {expected_base!r}."
        )
    head_ref = str(pr_data.get("headRefName", "")).strip()
    validate_topic_branch(head_ref, base_branch=expected_base)
    return head_ref


def validate_topic_branch(branch: str, *, base_branch: str) -> None:
    if not branch:
        raise PostMergeCleanupError("Topic branch must not be empty.")
    if branch == base_branch or branch in PROTECTED_BRANCHES:
        raise PostMergeCleanupError(f"Refusing to delete protected branch: {branch}.")
    if not branch.startswith("codex/"):
        raise PostMergeCleanupError(
            f"Refusing to delete non-codex topic branch without manual review: {branch}."
        )


def build_cleanup_steps(
    *,
    branch: str,
    base_branch: str,
    remote: str,
    local_branch_exists: bool,
    remote_branch_exists: bool,
) -> tuple[CleanupStep, ...]:
    validate_topic_branch(branch, base_branch=base_branch)
    steps = [
        CleanupStep("fetch-prune-before-cleanup", ("git", "fetch", "--prune", remote)),
        CleanupStep("checkout-base", ("git", "checkout", base_branch)),
        CleanupStep("fast-forward-base", ("git", "pull", "--ff-only", remote, base_branch)),
    ]
    if local_branch_exists:
        steps.append(
            CleanupStep(
                "delete-local-topic-branch",
                ("git", "branch", "-d", branch),
                destructive=True,
            )
        )
    if remote_branch_exists:
        steps.append(
            CleanupStep(
                "delete-remote-topic-branch",
                ("git", "push", remote, "--delete", branch),
                destructive=True,
            )
        )
    steps.append(CleanupStep("fetch-prune-after-cleanup", ("git", "fetch", "--prune", remote)))
    return tuple(steps)


def build_report(
    *,
    mode: str,
    pr_number: str,
    pr_url: str,
    branch: str,
    base_branch: str,
    remote: str,
    merge_commit: str,
    steps: tuple[CleanupStep, ...],
) -> dict[str, object]:
    return {
        "status": "planned" if mode == "dry-run" else "completed",
        "mode": mode,
        "pr": pr_number,
        "pr_url": pr_url,
        "branch": branch,
        "base_branch": base_branch,
        "remote": remote,
        "merge_commit": merge_commit,
        "steps": [step.as_json() for step in steps],
        "notion_completion_required": True,
        "notion_completion_fields": [
            "Status = Done",
            "Completed At with datetime",
            "PR URL",
            "merge commit",
            "verification performed",
            "local and remote branch cleanup evidence",
        ],
        "notion_completion_note": (
            "After cleanup, mark the matching Issues & Open Questions and Feature "
            "Backlog entries Done with PR URL, merge commit, verification, and branch "
            "cleanup evidence."
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a merged PR and clean up its local/remote topic branch.",
    )
    parser.add_argument("--pr", required=True, help="Merged pull request number or URL.")
    parser.add_argument("--branch", help="Topic branch to delete. Defaults to PR headRefName.")
    parser.add_argument("--base", default="main", help="Expected base branch.")
    parser.add_argument("--remote", default="origin", help="Git remote name.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run cleanup commands. Without this flag the script only prints the plan.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pr_data = _gh_pr_view(args.pr)
        pr_branch = validate_merged_pr(pr_data, expected_base=args.base)
        branch = args.branch or pr_branch
        validate_topic_branch(branch, base_branch=args.base)
        if branch != pr_branch:
            raise PostMergeCleanupError(
                f"Provided branch {branch!r} does not match PR head {pr_branch!r}."
            )
        if args.apply:
            _ensure_clean_worktree()
            _run(("git", "fetch", "--prune", args.remote))
        local_exists = _local_branch_exists(branch)
        remote_exists = _remote_branch_exists(args.remote, branch)
        steps = build_cleanup_steps(
            branch=branch,
            base_branch=args.base,
            remote=args.remote,
            local_branch_exists=local_exists,
            remote_branch_exists=remote_exists,
        )
        if args.apply:
            for step in steps:
                if step.name == "fetch-prune-before-cleanup":
                    continue
                _run(step.command)
        report = build_report(
            mode="apply" if args.apply else "dry-run",
            pr_number=str(args.pr),
            pr_url=str(pr_data.get("url", "")),
            branch=branch,
            base_branch=args.base,
            remote=args.remote,
            merge_commit=str(pr_data.get("mergeCommit", {}).get("oid", "")),
            steps=steps,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
    except (PostMergeCleanupError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _gh_pr_view(pr: str) -> dict[str, Any]:
    output = _run(
        (
            "gh",
            "pr",
            "view",
            pr,
            "--json",
            "state,mergedAt,mergeCommit,baseRefName,headRefName,url",
        ),
        capture=True,
    )
    parsed = json.loads(output)
    if not isinstance(parsed, dict):
        raise PostMergeCleanupError("gh pr view did not return a JSON object.")
    return parsed


def _ensure_clean_worktree() -> None:
    status = _run(("git", "status", "--short"), capture=True)
    if status.strip():
        raise PostMergeCleanupError("Working tree must be clean before cleanup.")


def _local_branch_exists(branch: str) -> bool:
    output = _run(("git", "branch", "--list", branch), capture=True)
    return bool(output.strip())


def _remote_branch_exists(remote: str, branch: str) -> bool:
    output = _run(("git", "ls-remote", "--heads", remote, branch), capture=True)
    return bool(output.strip())


def _run(command: Sequence[str], *, capture: bool = False) -> str:
    completed = subprocess.run(
        tuple(command),
        check=True,
        text=True,
        capture_output=capture,
    )
    return completed.stdout if capture else ""


if __name__ == "__main__":
    raise SystemExit(main())
