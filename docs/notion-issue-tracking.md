# Notion Issue Tracking Standard

## Purpose

SCAS repository work is tracked in the `SCAS - Issues & Open Questions`
database. Issue properties are not enough for durable handoff: every issue must
also have a page-level comment that describes the task, decision, blocker, or
follow-up.

This standard keeps Notion useful for lifecycle tracking while durable
architecture, security, data-governance, release, and workflow criteria remain
in repository files.

## Required Issue Comment

Every `SCAS - Issues & Open Questions` page created or updated for repository
work must include a page-level comment. The initial comment must cover:

- requested outcome,
- repository or subsystem scope,
- current assumption or known dependency,
- planned next action.

Use a comment even when the page body already contains a task summary. The body
is useful for structured notes, but comments provide visible lifecycle evidence
and discussion history.

## Progress And Completion Comments

Add another page-level comment when one of these events occurs:

- implementation branch or pull request is created,
- verification result changes the task state,
- scope changes,
- a blocker or follow-up is discovered,
- a pull request is merged, closed, or superseded,
- the issue is marked `Done`.

Completion comments must include the pull request URL when available, merge
commit when available, verification performed, branch cleanup status when
applicable, and any remaining follow-up.

## Safety

Do not place secrets, provider tokens, private keys, raw runtime traces, raw
tool outputs, confidential customer data, or release evidence payloads in
Notion comments. Summarize evidence by URL, commit, workflow name, status, and
sanitized result only.

## Audit Workflow

Audit the Issues database periodically and before broad backlog handoffs:

1. Fetch the current `SCAS - Issues & Open Questions` records.
2. For every in-scope issue, check whether a page-level task-describing comment
   exists.
3. Backfill concise retrospective comments for missing historical records.
4. Record the audit result on the active audit issue.
5. Validate any exported audit summary with:

```powershell
python scripts\repo\validate_notion_issue_comment_audit.py examples\repo\notion-issue-comment-audit.json
```

When structured Notion database querying is unavailable, use Notion search plus
page fetch/comment fetch for the active and recent issue set, then record the
coverage limitation in the active audit issue.
