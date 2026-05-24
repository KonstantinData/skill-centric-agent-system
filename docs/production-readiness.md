# Production Readiness Gate

## Purpose

This document defines the evidence gate required before the repository can be
described as production-ready.

The current system has an initial productive runtime core. That is not the same
as a production-ready release. Production-ready status requires environment
separation, repeatable release evidence, operational coverage, security closure,
and executable runtime capabilities that match the claimed production scope.

## Status Vocabulary

Use these status values consistently in repository documentation, Notion, and
release handoffs:

- `initial-productive-core`: the runtime can execute the first bounded
  productive path against real development infrastructure.
- `staging-ready`: the release gate passes against staging infrastructure with
  no unresolved high-risk gaps.
- `production-ready`: the release gate passes against production
  infrastructure, all required evidence is recorded, and any waiver has explicit
  owner-approved risk acceptance.
- `not-production-ready`: one or more required release gates are missing,
  failing, or unevidenced.

The repository is currently `not-production-ready` for a full production launch.
It may be described as having an `initial-productive-core`.

## Release Gate

A release may be marked `production-ready` only when every required gate below
is satisfied for the target environment.

| Gate | Required Evidence |
| --- | --- |
| Repository integrity | `python -m pytest`, `python -m ruff check .`, security governance scripts, `npm run worker:typecheck`, `npm run worker:test`, and `npm run worker:check` pass on the release commit. |
| Contract and documentation consistency | README, architecture, contracts, schemas, examples, runbooks, and ADRs are consistent with the release scope. |
| Repository security and supply chain | Secret scanning, tracked `.env` guard, dependency policy, Dependency Review, CodeQL, workflow hardening, pinned Actions, Actions-BOM, SBOM generation, CODEOWNERS, and main-protection desired-state validation pass. |
| Data governance and quality | Data classification, model privacy, audit minimization, and knowledge/data-quality policy fixtures are current and tested. |
| Environment separation | Cloudflare and Hetzner resources are separated for `staging` and `prod`; secrets, databases, artifact roots, queues, indexes, and roles do not share mutable production state with `dev`. |
| Control Plane readiness | Cloudflare Worker, D1, R2, Vectorize, Queues, KV, AI Gateway, bearer auth, endpoint-scoped tokens, migrations, seed state, and rollback path are verified. |
| Runtime Plane readiness | Hetzner PostgreSQL, runtime roles, migrations, artifact root, Flight Recorder writes, retention planning, backup, restore, and disable paths are verified. |
| Live runtime gates | Generic E2E, retrieval and Vectorize smoke, AI Gateway live smoke, Postgres concurrency smoke, and retention dry-run/apply evidence pass for the target environment. |
| Live handler binding evidence | The referenced Live Runtime Gates run uploads `live-runtime-handler-binding-evidence`; certification validates passed live E2E cases and sanitized `skill_handlers` where every `handler_id` equals `name@version`. |
| Executable skill runtime | Profile-selected skills resolve to version-pinned executable handlers; unknown or mismatched handlers fail closed; `python scripts/runtime/skill_handler_coverage.py --check` proves every production-required skill fixture maps to a handler, runtime path, and tests. |
| Skill handler version policy | Handler upgrades, deprecations, and rollback follow `docs/skill-handler-version-policy.md` and `policies/runtime/skill-handler-version-policy.json`; rollback uses a newly composed profile with the previous registered version pin. |
| Write-capable execution scope | If production scope includes writes, every write adapter has explicit authorization, approval, policy, audit, validation, and rollback coverage. If production scope is read-only, that limitation is stated in the release evidence. |
| Operational telemetry | Retrieval, validation, cleanup, AI Gateway, queue processing, runtime failures, and policy denials have observable signals and runbook-backed diagnostics. |
| Security closure | Threat model is current, security scan findings are closed or explicitly accepted, token scopes are verified, secret rotation is documented, and data-plane boundaries are tested. |
| Release decision | The release evidence records commit, target environment, gate results, unresolved risks, waivers, owner, timestamp, and final decision. |

## Evidence Rules

- Evidence must be reproducible from committed commands, scripts, workflows, or
  runbooks.
- Evidence must not include secret values, raw runtime artifacts, raw tool
  outputs, private keys, bearer tokens, or provider credentials.
- A failed gate cannot be replaced by a narrative statement.
- A waiver must name the gate, risk, owner, expiry condition, and compensating
  control.
- Dev evidence can support implementation confidence, but it cannot certify
  staging or production.

## Prioritized Implementation Backlog

The production readiness backlog is ordered by dependency and release risk:

1. `P5.01 Production Release Readiness Gate`
   Define this gate, add repository documentation, and make the gate testable.
2. `P5.02 Staging and Production Environment Separation`
   Add explicit Cloudflare and Hetzner staging/prod configuration and validation.
   Initial resource manifest and documentation are present; provisioning and
   live validation remain pending.
3. `P5.03 Production Release Evidence Workflow`
   Run required checks and live gates through a release workflow that writes a
   non-secret evidence summary.
   Complete: `.github/workflows/production-readiness.yml` writes a
   machine-readable evidence artifact in `evidence-only` mode and verifies
   same-repository, same-commit, successful external live gate runs in
   `certify` mode.
4. `P5.04 Production Skill Handler Runtime`
   Initial code-backed handler registry complete. The runtime now resolves
   profile-selected skills to exact `name@version` executable handlers and
   fail-closes unknown or mismatched handlers before tool execution.
   Handler coverage is now machine-readable in
   `examples/runtime/skill-handler-coverage.json` and validated by CI.
   Handler version upgrade and rollback policy is now defined in
   `docs/skill-handler-version-policy.md` and tested by
   `tests/test_skill_handler_version_policy.py`.
5. `P5.05 Controlled Write-Capable Execution Path`
   Add write adapters only behind authorization, approval, policy, audit,
   validation, and rollback gates.
   Complete: the first controlled write path is `filesystem-write`, guarded by
   profile-selected `repository-write` data scope, `write-approval-required`
   policy, high-risk gating, structured approval payloads, rollback metadata,
   dry-run-by-default behavior, and tests. Planners still emit read-only actions
   until a later composition slice explicitly selects write profiles.
6. `P5.06 Scheduled Runtime Retention Cleanup Automation`
   Automate dry-run-first retention cleanup with reports and failure signals.
   Complete: `.github/workflows/runtime-retention-cleanup.yml` runs scheduled
   dry-run retention cleanup on the Hetzner Runtime Plane, supports manual
   environment-targeted dry-run or confirmed-delete dispatch, uploads
   non-secret cleanup evidence, and prevents scheduled destructive cleanup.
7. `P5.07 Production Telemetry and Alerting`
   Add production telemetry for Control Plane and Runtime Plane failure modes.
   Complete: aggregate telemetry policy and snapshot schemas, fixtures, CLI
   evaluator, runbook-backed alert metadata, and release-evidence gate coverage
   are implemented. Alert evidence records aggregate metadata only; raw runtime
   traces remain on Hetzner.
8. `P5.08 Security Hardening and Threat Model Closure`
   Complete security review, threat model updates, token scope checks, and
   finding remediation.
   Initial repository security and governance gates now cover secret scanning,
   `.env` guard, CODEOWNERS, main-protection desired-state validation,
   dependency policy, workflow hardening, Actions-BOM, release SBOM, data
   governance, and quality-policy tests.
9. `P5.09 Analyzer, Composer, and Human Review Quality Gate`
   Expand evaluation coverage and make ambiguous production tasks enter a
   human-review path instead of overgranting.
10. `P5.10 Production Readiness Certification Run`
    Run the complete gate against the target environment and record the release
    decision.

## Certification Output

Every production certification must record:

- release commit,
- target environment,
- release scope,
- production status value,
- gate result table,
- command or workflow evidence references,
- unresolved risks,
- approved waivers,
- owner,
- completion timestamp,
- next review trigger.

The certification output belongs in the repository or release artifact when it
describes durable release state. Notion may track the task lifecycle, but Notion
does not replace committed release criteria.

## Evidence Workflow

The manual `.github/workflows/production-readiness.yml` workflow records
repository, security governance, and Worker gates in
`production-readiness-evidence.json`, generates non-secret
`security-evidence/*.json` artifacts, and uploads those files as workflow
artifacts. `evidence-only` mode supports implementation progress while staging
and production infrastructure are still being prepared.
`certify` mode requires references to matching live runtime and AI Gateway
smoke workflow runs.

The workflow builds the evidence artifact through
`scripts/release/build_production_readiness_evidence.py`. In `certify` mode it
uses `gh run view` to collect metadata for the referenced runs and fails closed
unless each run:

- belongs to the same repository,
- uses the same release commit SHA as the evidence workflow,
- completed successfully,
- matches the expected workflow name (`Live Runtime Gates` for runtime gates
  and `CI` for the AI Gateway smoke), and
- uses a canonical `https://github.com/OWNER/REPO/actions/runs/RUN_ID` URL.

The workflow also downloads the `live-runtime-handler-binding-evidence`
artifact from the referenced Live Runtime Gates run. Certification fails closed
unless that artifact contains passed live E2E results with sanitized
`skill_handlers` where every `handler_id` equals `name@version`.

The evidence artifact uses contract version `0.3.0` and includes:

- release commit, target environment, release scope, workflow run ID, and
  generated timestamp,
- `gate_results` with `passed`, `pending`, or `not_required` statuses,
- controlled write-capable execution as a passed repository gate for the first
  `filesystem-write` slice,
- scheduled runtime retention cleanup as a passed repository gate once the
  workflow and workflow tests are present,
- production telemetry and alerting as a passed repository gate once the
  aggregate policy, snapshot, evaluator, and tests are present,
- validated external run metadata and live handler-binding summaries in
  `external_evidence`,
- `open_release_gaps` for required production gates that are not yet complete,
- `status` and `final_decision`, and
- a sensitive-data handling statement.

This workflow does not write secret values to its evidence artifact. External
live gate URLs must point to workflow runs whose logs also avoid secret output.
The workflow alone does not bypass incomplete production gates: staging and
production certification remain `not-production-ready` while required follow-up
gates such as threat-model closure, human-review quality gates, and broader
production handler coverage are still open.
