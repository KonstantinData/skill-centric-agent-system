# Production Readiness Gate

## Purpose

This document defines the evidence gate required before the repository can be
described as production-ready.
Production-ready status requires environment separation, repeatable release
evidence, operational coverage, security closure, and executable runtime
capabilities that match the claimed production scope.

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

## Release Gate

A release may be marked `production-ready` only when every required gate below
is satisfied for the target environment.

| Gate | Required Evidence |
| --- | --- |
| Repository integrity | `python -m pytest`, `python -m ruff check .`, `python scripts/runtime/invariant_check.py`, security governance scripts, `npm run worker:typecheck`, `npm run worker:test`, and `npm run worker:check` pass on the release commit. |
| Contract and documentation consistency | README, architecture, contracts, schemas, examples, runbooks, and ADRs are consistent with the release scope. |
| Repository security and supply chain | Secret scanning, tracked `.env` guard, dependency policy, Dependency Review, CodeQL, workflow hardening, pinned Actions, Actions-BOM, SBOM generation, effective CODEOWNERS ownership coverage, active main-branch protection, main-protection desired-state validation, and scheduled/manual live GitHub governance drift detection pass. |
| Data governance and quality | Data classification, model privacy, audit minimization, and knowledge/data-quality policy fixtures are current and tested. |
| Environment separation | Cloudflare and Hetzner resources are separated for `staging` and `prod`; secrets, databases, artifact roots, queues, indexes, and roles do not share mutable production state with `dev`. |
| Control Plane readiness | Cloudflare Worker, D1, R2, Vectorize, Queues, KV, AI Gateway, bearer auth, endpoint-scoped tokens, migrations, seed state, and rollback path are verified. |
| Runtime Plane readiness | Hetzner PostgreSQL, runtime roles, migrations, artifact root, Flight Recorder writes, retention planning, backup, restore, and disable paths are verified. |
| Live runtime gates | Generic E2E, retrieval and Vectorize smoke, AI Gateway live smoke, Postgres concurrency smoke, and retention dry-run/apply evidence pass for the target environment. |
| Pre-canary safety gate | Invariant replay and shadow regression thresholds pass together with explicit remediation output on failure. |
| Automatic rollback rules | Failed pre-canary gate requires rollback to signed and verified last-known-good descriptor/policy versions. |
| Incident-locked regressions | Incident-linked never-again fixtures pass and remain bound to mandatory invariants per change type. |
| HOOKS usage model | Runtime and composition hook points are versioned in `policies/runtime/hooks-usage-model.json`; unknown or unregistered hooks fail closed; `python scripts/runtime/validate_hooks_usage_model.py --check` proves hooks cannot grant capabilities, mutate active profiles, bypass policies or validators, read unscoped data, execute unregistered tools, write secrets/raw traces, or change module version pins. |
| Recertification cadence and release policy | `policies/runtime/production-recertification-policy.json` defines target-environment evidence age, required certification modes, release-decision fields, waiver limits, and mandatory recertification triggers; `python scripts/release/validate_production_recertification_policy.py --check` proves the policy remains current and fail-closed for stale or trigger-invalidated evidence. |
| Live handler binding evidence | The referenced Live Runtime Gates run uploads `live-runtime-handler-binding-evidence`; certification validates passed live E2E cases and sanitized `skill_handlers` where every `handler_id` equals `name@version`. |
| Executable skill runtime | Profile-selected skills resolve to version-pinned executable handlers; unknown or mismatched handlers fail closed; `python scripts/runtime/skill_handler_coverage.py --check` proves every production-required skill fixture maps to a handler, runtime path, and tests; `python scripts/runtime/production_skill_instruction_packs.py --check` proves instruction packs remain aligned with modules, handlers, and test evidence. |
| Skill handler version policy | Handler upgrades, deprecations, and rollback follow `docs/policies/skill-handler-version-policy.md` and `policies/runtime/skill-handler-version-policy.json`; rollback uses a newly composed profile with the previous registered version pin. |
| Write-capable execution scope | If production scope includes writes, every write adapter has explicit authorization, approval, policy, audit, validation, and rollback coverage. If production scope is read-only, that limitation is stated in the release evidence. |
| Operational telemetry | Retrieval, validation, cleanup, AI Gateway, queue processing, runtime failures, and policy denials have observable signals and runbook-backed diagnostics. |
| Error taxonomy gates | F1/F2/R8 classification contracts, evaluation fixtures, thresholds, and CI enforcement are current and green. |
| Security closure | Threat model is current, security scan findings are closed or explicitly accepted, token scopes are verified, secret rotation is documented, and data-plane boundaries are tested. |
| Human-review quality | Ambiguous analyzer output produces review-required profiles with explicit ambiguity evidence and no selected specialized capabilities before approval. |
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

Implementation sequencing and status tracking are intentionally kept outside
this policy file in `docs/roadmap/production-readiness-backlog.md`.

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
- next review trigger,
- next review due timestamp.

The certification output belongs in the repository or release artifact when it
describes durable release state. Notion may track the task lifecycle, but Notion
does not replace committed release criteria.

## Evidence Workflow

The manual `.github/workflows/production-readiness.yml` workflow records
repository, security governance, and Worker evidence in
`production-readiness-evidence.json` and uploads non-secret evidence as
workflow artifacts. By default, `evidence_source_mode = consume-existing`
consumes matching upstream `CI` and `Security Governance` workflow runs instead
of rerunning the broad repository gates. Intentional reruns must set
`evidence_source_mode = recheck`; that mode reruns the repository governance,
Python, invariant, regression, rollback, tracked-JSON, and Worker gates before
building the evidence artifact.
`evidence-only` mode supports implementation progress while staging and
production infrastructure are still being prepared.
`certify` mode requires references to matching live runtime and AI Gateway
smoke workflow runs.
In `recheck` mode, the workflow also persists
`production-evidence/invariant-check.json` and fails closed unless the report
exists, has `status = "passed"`, `mismatch_count = 0`, and a positive
`total_cases`.
It additionally records
`production-evidence/shadow-regression-threshold-evaluation.json`,
`production-evidence/pre-canary-safety-gate.json`,
`production-evidence/automatic-rollback-evaluation.json`, and
`production-evidence/incident-locked-regressions.json`; certification fails
closed when those reports fail, rollback is required but the target is not
signed and verified, or incident-locked regressions show binding violations or
replay mismatches.
It also validates the HOOKS usage model and fails closed if configured hook
points can grant capabilities, mutate active profiles, bypass policies or
validators, access unscoped data, execute unregistered tools, write secrets or
raw traces, or change module version pins.
It validates the production recertification policy and fails closed if the
target-environment cadence, release-decision requirements, waiver limits, or
mandatory recertification triggers drift from the committed release policy.

The workflow builds the evidence artifact through
`scripts/release/build_production_readiness_evidence.py`. In the default
`consume-existing` evidence mode, the workflow uses `gh run view` to collect
metadata for the referenced `CI` and `Security Governance` runs, downloads the
non-secret `security-evidence` artifact from the security run, records SHA-256
checksums for the downloaded JSON evidence files, and fails closed unless each
upstream run:

- belongs to the same repository,
- uses the same release commit SHA as the evidence workflow,
- completed successfully,
- matches the expected workflow name (`CI` or `Security Governance`),
- uses a canonical `https://github.com/OWNER/REPO/actions/runs/RUN_ID` URL, and
- was created no more than 14 days before the evidence timestamp.

In `certify` mode it also uses `gh run view` to collect metadata for the
referenced live runs and fails closed unless each run:

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

The evidence artifact uses contract version `0.5.0` and includes:

- release commit, target environment, release scope, workflow run ID, and
  generated timestamp,
- `gate_results` with `passed`, `pending`, or `not_required` statuses,
- controlled write-capable execution as a passed repository gate for the first
  `filesystem-write` slice,
- scheduled runtime retention cleanup as a passed repository gate once the
  workflow and workflow tests are present,
- production telemetry and alerting as a passed repository gate once the
  aggregate policy, snapshot, evaluator, and tests are present,
- security hardening and threat-model closure as a passed repository gate once
  the threat model, token-scope review, validator, and tests are present,
- analyzer, composer, and human-review quality as a passed repository gate once
  ambiguous tasks emit review-required profiles without selected runtime
  capabilities,
- validated external run metadata and live handler-binding summaries in
  `external_evidence`,
- `recertification_policy`, `recertification_triggers`, and
  `next_review_due_at`,
- `waivers`, `owner`, and `completed_at`,
- `open_release_gaps` for required production gates that are not yet complete,
- `status` and `final_decision`, and
- a sensitive-data handling statement.

This workflow does not write secret values to its evidence artifact. External
live gate URLs must point to workflow runs whose logs also avoid secret output.
The workflow itself does not override release gates. Gate outcomes still depend
on verified evidence for the target environment.

