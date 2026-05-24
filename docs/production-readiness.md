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
| Repository integrity | `python -m pytest`, `python -m ruff check .`, `npm run worker:typecheck`, `npm run worker:test`, and `npm run worker:check` pass on the release commit. |
| Contract and documentation consistency | README, architecture, contracts, schemas, examples, runbooks, and ADRs are consistent with the release scope. |
| Environment separation | Cloudflare and Hetzner resources are separated for `staging` and `prod`; secrets, databases, artifact roots, queues, indexes, and roles do not share mutable production state with `dev`. |
| Control Plane readiness | Cloudflare Worker, D1, R2, Vectorize, Queues, KV, AI Gateway, bearer auth, endpoint-scoped tokens, migrations, seed state, and rollback path are verified. |
| Runtime Plane readiness | Hetzner PostgreSQL, runtime roles, migrations, artifact root, Flight Recorder writes, retention planning, backup, restore, and disable paths are verified. |
| Live runtime gates | Generic E2E, retrieval and Vectorize smoke, AI Gateway live smoke, Postgres concurrency smoke, and retention dry-run/apply evidence pass for the target environment. |
| Executable skill runtime | Profile-selected skills resolve to version-pinned executable handlers; unknown or mismatched handlers fail closed. |
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
   Initial evidence-only workflow support is present in
   `.github/workflows/production-readiness.yml`; target-environment live gate
   orchestration remains pending.
4. `P5.04 Production Skill Handler Runtime`
   Move from example-only skill metadata and centralized strategies to
   version-pinned executable skill handlers.
5. `P5.05 Controlled Write-Capable Execution Path`
   Add write adapters only behind authorization, approval, policy, audit,
   validation, and rollback gates.
6. `P5.06 Scheduled Runtime Retention Cleanup Automation`
   Automate dry-run-first retention cleanup with reports and failure signals.
7. `P5.07 Production Telemetry and Alerting`
   Add production telemetry for Control Plane and Runtime Plane failure modes.
8. `P5.08 Security Hardening and Threat Model Closure`
   Complete security review, threat model updates, token scope checks, and
   finding remediation.
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
repository and Worker gates in `production-readiness-evidence.json` and uploads
that file as a workflow artifact. `evidence-only` mode supports implementation
progress while staging and production infrastructure are still being prepared.
`certify` mode requires references to matching live runtime and AI Gateway
smoke workflow runs.

This workflow does not write secret values to its evidence artifact. External
live gate URLs must point to workflow runs whose logs also avoid secret output.
