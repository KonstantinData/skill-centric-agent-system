# Notion Issue Tracking Standard

## Purpose

SCAS repository work uses Notion as the lifecycle ledger and repository files
as the durable technical truth. Notion records task scope, documentation impact,
decisions, blockers, change facts, PR links, and reconciliation outcomes; it
must not duplicate architecture, contracts, policies, runbooks, schemas,
examples, release criteria, or operational commands that belong in the repo.

Issue properties are not enough for durable handoff. Every
`SCAS - Issues & Open Questions` page created or updated for repository work
must also have a page-level comment that describes the task, decision, blocker,
follow-up, or completion state.

## Lifecycle At A Glance

1. Classify Documentation Impact when a task or backlog item is created.
2. Update Documentation Impact when subtasks, blockers, or follow-ups appear.
3. Record concise change facts while implementation progresses.
4. Reconcile documentation impact, change facts, and branch diff before PR
   creation/update/completion or final handoff.
5. Use `docs/runbooks/post-merge-lifecycle.md` for post-merge completion and
   cleanup evidence.

## Required Issue Comment

Every `SCAS - Issues & Open Questions` page created or updated for repository
work must include a page-level comment.
Every new `SCAS - Feature Backlog` entry must include the full Documentation
Impact block from this runbook in its description or first lifecycle comment.
Every initial issue/backlog comment must cover:

- requested outcome,
- repository or subsystem scope,
- current assumption or known dependency,
- planned next action,
- intended base branch or known base commit when the work is expected to
  produce a pull request,
- Documentation Impact classification.

Use a comment even when the page body already contains a task summary. The body
is useful for structured notes, but comments provide visible lifecycle evidence
and discussion history.

## Progress And Completion Comments

Add another page-level comment when one of these events occurs:

- implementation branch or pull request is created,
- verification result changes the task state,
- scope changes,
- a durable change fact is discovered or completed,
- a subtask, follow-up, blocker, or sub-subtask is discovered,
- a pull request is merged, closed, or superseded,
- the issue is marked `Done`.

Completion comments must include verification performed and any remaining
follow-up. For merged pull requests, the canonical post-merge completion fields
are defined in `docs/runbooks/post-merge-lifecycle.md`.

## Documentation Impact At Task Creation

Classify Documentation Impact when creating any SCAS task, including Feature
Backlog items, Issues & Open Questions entries, subtasks, sub-subtasks,
follow-ups, and blocker tasks.

Use this shape:

```text
Documentation Impact
- Documentation Impact: expected/not expected/unknown
- Reason: <why durable repo documentation is or is not expected to change>
- Candidate documentation files:
  - <README.md, docs/..., schemas/..., examples/..., policies/..., or none>
- Documentation acceptance:
  - <what must be updated, verified, or reclassified before completion>
```

Classification rules:

- Use `expected` when the task may change durable behavior, contracts, setup,
  operations, governance, roadmap status, examples, schemas, policies,
  workflows, or user-facing repository guidance.
- Use `not expected` only when the task is genuinely internal and has no
  expected durable documentation effect; still recheck before PR or handoff.
- Use `unknown` only when the impact cannot yet be determined. Resolve it
  before implementation continues, or treat it as `expected` for planning.

Always recheck Documentation Impact before PR creation/update/completion or
final handoff. This recheck is a rule, not a field to fill out.

This block is task-scope metadata, not durable technical documentation. Keep
the durable explanation in repository files when documentation must change.

## Subtask Documentation Impact

When a subtask is discovered during implementation, classify Documentation
Impact immediately.

If the subtask stays inline within the main task, add a progress comment to the
parent issue:

```text
Subtask Discovered
- Task: <subtask>
- Handling: in scope of current main task
- Documentation Impact: expected/not expected/unknown
- Candidate documentation files:
  - <path or none>
- Parent documentation scope updated: yes/no
```

If the subtask becomes a separate Notion task, give that task its own
Documentation Impact block and reference the parent only when it helps explain
scope or dependency.

Do not leave documentation impact implicit for follow-ups, blockers, or
sub-subtasks. If the impact is unknown, record what must be checked next.

## Change Facts

Use change facts to describe what the PR actually changed without turning
Notion into a second technical documentation site. Keep them short and factual:

- implemented, removed, renamed, newly validated, or still-pending behavior,
- affected subsystem or contract,
- evidence pointer such as commit, PR, test command, or repository file path.

Examples:

- `Runtime skill handler coverage expanded from four to six production-required fixtures.`
- `Cloudflare Control API workflow now validates endpoint-scoped tokens.`
- `New runbook added at docs/runbooks/example.md.`

Durable explanations of how a system works belong in `README.md`, `docs/`,
`schemas/`, `examples/`, or ADRs, not in Notion comments.

## Documentation Reconciliation

Before PR creation/update/completion or final handoff, the docs consistency
governor must reconcile repository documentation against:

1. the initial Documentation Impact classification on the active SCAS issue
   and any related Feature Backlog entry,
2. documentation impact updates from inline or standalone subtasks,
3. recorded change facts,
4. the repository's durable documentation surfaces,
5. the branch diff against the PR base.

Add a page-level reconciliation comment in this shape:

```text
Docs Reconciliation
- Base: <base ref and commit>
- Head: <head ref and commit>
- Topic: <issue/backlog topic>
- Documentation Impact: expected/not expected/unknown
- Initial candidate docs:
  - <path or none>
- Subtask documentation impact changes:
  - <subtask/change or none>
- Change facts:
  - <fact>
- Durable repo docs updated:
  - <path>: <why>
- Reclassified docs:
  - <path>: <from/to + reason>
- Repo docs unchanged:
  - <path>: <specific rationale>
- Blocking docs gaps: none
- Follow-up docs tasks: none
```

Rules:

- `Blocking docs gaps` must be `none` before PR completion or final handoff.
- If a required durable repo doc is stale, update the repo file in the same
  branch instead of deferring the truth to Notion.
- If an initially expected doc does not need an update, record it under
  `Reclassified docs` with a concrete reason.
- Use `Follow-up docs tasks` only for genuinely separate future work, not for
  documentation required to make the current PR truthful.
- A docs-only reconciliation comment is not enough when repository docs need to
  change.

## Worked Example

```text
Documentation Impact
- Documentation Impact: expected
- Reason: endpoint-scoped Control API token handling changes operational
  authentication behavior and workflow setup.
- Candidate documentation files:
  - README.md
  - docs/runbooks/operations-runbook.md
  - docs/reference/cloudflare/control-api.md
- Documentation acceptance:
  - update affected auth/setup instructions or reclassify each candidate with
    a concrete reason before PR completion.
```

```text
Change Fact
- Cloudflare Control API workflow validates endpoint-scoped tokens before live
  runtime gates execute; evidence: .github/workflows/live-runtime-gates.yml and
  docs/runbooks/operations-runbook.md.
```

```text
Docs Reconciliation
- Base: origin/main@abc123
- Head: codex/control-token-scope@def456
- Topic: Add endpoint-scoped Control API token validation
- Documentation Impact: expected
- Initial candidate docs:
  - README.md
  - docs/runbooks/operations-runbook.md
  - docs/reference/cloudflare/control-api.md
- Subtask documentation impact changes:
  - none
- Change facts:
  - live runtime gates validate endpoint-scoped Control API tokens.
- Durable repo docs updated:
  - docs/runbooks/operations-runbook.md: documents required env-specific token
    names and validation behavior.
  - docs/reference/cloudflare/control-api.md: documents protected endpoint
    authorization expectations.
- Reclassified docs:
  - README.md: expected -> not expected; high-level GitHub Actions section
    already points to the detailed runbook and no command changed there.
- Repo docs unchanged:
  - none
- Blocking docs gaps: none
- Follow-up docs tasks: none
```

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
