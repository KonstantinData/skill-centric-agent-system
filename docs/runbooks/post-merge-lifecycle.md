# Post-Merge Lifecycle

## Purpose

This runbook standardizes the repository cleanup sequence after a topic branch
has been merged to `main`.

It is intentionally compatible with the current fast setup workflow and the
active main-branch protection ruleset. It does not replace review, CI, or
Notion lifecycle tracking.

Use `docs/runbooks/notion-issue-tracking.md` for general Notion issue comment
rules and documentation reconciliation. This runbook is the canonical source
for post-merge completion and branch cleanup evidence.

## Required Order

1. Verify the PR is merged and record the PR URL and merge commit.
2. Verify all required PR checks passed.
3. Sync local `main` with `origin/main`.
4. Delete the merged local topic branch.
5. Delete or prune the merged remote topic branch.
6. Verify `git status --short --branch` is clean on `main`.
7. Update the matching Issues & Open Questions page using the post-merge
   Notion completion fields below.
8. Update the matching Feature Backlog entry to `Done` with the same PR URL and
   completion timestamp.

## Script

Use dry-run mode first:

```powershell
python scripts\repo\post_merge_cleanup.py --pr 10
```

Apply cleanup only after reviewing the plan:

```powershell
python scripts\repo\post_merge_cleanup.py --pr 10 --apply
```

The script fails closed unless:

- the PR state is `MERGED`,
- the PR base is the expected base branch, default `main`,
- the topic branch starts with `codex/`,
- the target branch is not a protected branch name, and
- the working tree is clean before `--apply`.

The script prints a JSON cleanup report. That report is safe to summarize in
Notion because it contains branch names, commands, PR references, and merge
commit IDs, not secrets or runtime artifacts.

## Notion

The script cannot update Notion because the Notion connector is not part of the
repository runtime. The agent or maintainer must still write a page-level
comment on the active Issues & Open Questions task and then mark both the issue
and Feature Backlog entry complete.

Every post-merge Notion completion note must include:

- `Status = Done`,
- `Completed At` with datetime,
- PR number and URL,
- merge commit,
- required PR checks result,
- local and remote branch cleanup result,
- local `main` sync and `git status --short --branch` result,
- any remaining follow-up.
