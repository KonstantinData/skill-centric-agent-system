# Skill-Centric Agent System

A repository for building a skill-centric, self-composing single-agent runtime.

The product direction is a single runtime agent that assembles a task-specific `Runtime Agent Profile` before execution. Skills, instructions, tools, knowledge, data scopes, memory scopes, policies, and validators are selected through controlled registries, scoring, policy filtering, and validation.

## Current Status

Initial composition implementation stage. The repository currently defines
durable architecture, contracts, schemas, ADRs, examples, a Python-based
contract-test harness, a local registry implementation, a deployed Cloudflare
Control API Worker, D1 migrations, generated dev registry seed data, and the
first Task Analyzer/Profile Composer implementation. The Hetzner Runtime Plane
also has an initial Flight Recorder storage contract for runtime events,
checkpoints, stop reasons, token budgets, idempotency keys, and atomic
run-local event indexing. The first runtime entry point can now start a run
from task intake, compose the runtime profile, emit Flight Recorder events,
write artifact-backed trace payloads, and run the first minimal
context/planner/executor/validator loop through a
profile-scoped Tool Gateway. The runtime CLI can now use either in-memory
storage for local fixtures or PostgreSQL storage for the Hetzner Runtime Plane
through `SCAS_RUNTIME_DATABASE_URL`. Runtime profile enforcement now fail-closes
unselected tools/scopes and exhausted tool, token, duration, data-read,
memory-op, and recomposition budgets. The Tool Gateway now applies per-tool
allowlists, risk gating, blocked argument checks, timeouts, output limits, and
access audit events. It also exposes the first controlled write adapter,
`filesystem-write`, which requires a profile-selected `repository-write` data
scope, `write-approval-required` policy, high-risk gating, structured approval,
rollback metadata, relative paths, and dry-run-by-default execution. The Runtime
Context Manager now calls the Control API retrieval endpoint for
profile-bounded knowledge/memory context and rejects scope-expanded responses.
The Validator phase now runs the validator IDs
selected by the active profile and fail-closes unknown or failed validators.
Controlled recomposition now emits `recomposition_requested`, stops the current
run with `needs_recomposition`, asks the Composer for a new immutable profile
generation, and can continue through a new run attempt without mutating the
active profile. A manual live dev E2E gate now exists for the Cloudflare-to-Hetzner
runtime path, and the operations runbook defines migrations, smoke tests,
diagnostics, and disable paths. Runtime artifact writes now honor the profile's
`observability.redact_sensitive_data` flag and expose a retention planner,
safe URI resolver, cleanup executor, cleanup report, and dry-run-first CLI for
runtime artifact cleanup jobs. Scheduled runtime retention cleanup now runs
through a dry-run-first GitHub Actions workflow against the Hetzner Runtime
Plane and uploads non-secret cleanup evidence for review. The Cloudflare
Control API also exposes initial knowledge and validated-memory ingestion
endpoints that write R2 objects, D1 metadata, ingestion jobs, and audit events.
It now also exposes a
D1-gated `POST /retrieval/context` endpoint with Vectorize bindings and
post-validation, plus a fail-closed AI Gateway route for OpenAI chat
completions. Ingestion now queues deterministic `embedding_update` jobs through
Cloudflare Queues; the queue consumer creates embeddings through AI Gateway and
upserts scoped vectors into Vectorize. Every non-health Control API route now
requires bearer authentication and supports endpoint-scoped authorization
tokens. Hetzner can
now extract memory candidates from completed runtime steps, validate their
scope/sensitivity/provenance/policy status, and submit only approved candidates
through the Memory Feedback Pipeline client. Analyzer and composition-scoring
evaluation fixtures now cover code-review, research, task-execution, general
tasks, and positive/negative scoring evidence. The Analyzer now emits
classification confidence, ambiguity, and human-review signals so mixed tasks
fall back to `general-task` instead of silently dispatching to the wrong
specialized strategy. The Composer now turns those review-required ambiguous
tasks into runtime profiles with explicit `human_review` evidence and no
selected specialized skills, tools, knowledge scopes, data scopes, or memory
scopes before approval. Runtime artifact persistence now chunks large string
payloads into manifest-referenced text chunks.

The current dev Control Plane can answer `POST /composition/context` with real
D1-backed module candidates such as `git-diff-analysis`. The Python composer can
consume that Control Plane response and emit a version-pinned runtime profile.
The Python runtime now resolves profile-selected skills to exact
`name@version` executable handlers for the first runtime slice, including
`git-diff-analysis`, `research-context-synthesis`, `task-execution-planning`,
and `general-task-summary`. Unknown selected skills and handler version
mismatches fail closed before tool execution, and each run still emits a
task-class-specific `runtime_output` validated by the active profile. A
review-required profile can now carry machine-readable ambiguity evidence
without selecting executable runtime capabilities. A
committed skill handler coverage manifest now maps every production-required
skill module fixture to its executable handler, runtime path, module tests,
and runtime tests; CI fails if the manifest is stale or a required handler is
missing.

The repository is currently `not-production-ready` for a full production
launch. It has an initial productive runtime core, but production-ready status
requires the release evidence gate in `docs/policies/production-readiness.md`, including
staging/prod environment separation, broader production handler coverage, and a
certification run against the target environment. The first environment
separation manifest is now recorded in
`examples/infrastructure/environment-manifest.json`, and production telemetry
policy fixtures now define aggregate Control Plane and Runtime Plane alert
signals without moving raw runtime traces out of Hetzner. The production
threat model and token-scope closure policy are now versioned and validated by
the security-governance gate. Staging/prod resources still need to be
provisioned and validated before any production-ready claim. The manual
Production Readiness Evidence workflow records repository and Worker gate
results as a non-secret artifact. Certification mode verifies external live
runtime and AI Gateway smoke run metadata against the same repository, same
release commit, expected workflow names, and successful conclusions before
writing release evidence.

## Core Flow

```text
UI/API -> Task Intake -> Task Analyzer -> Agent Composer
Agent Composer -> Runtime Agent Profile
Runtime Agent Profile -> Single Agent Runtime
Single Agent Runtime -> Context Manager / Planner / Executor / Validator
Executor -> Selected Skills / Allowed Tools / Scoped Data / Retrieved Knowledge
```

## Repository Map

- `docs/README.md`: documentation index and folder intent (`policies`, `runbooks`, `reference`, `adr`).
- `docs/reference/architecture.md`: system architecture and component responsibilities.
- `docs/policies/contracts.md`: durable contracts for modules and runtime profiles.
- `docs/policies/module-contracts.md`: detailed field semantics for selectable module metadata.
- `docs/policies/infrastructure-boundary.md`: Cloudflare Control Plane, Hetzner Runtime Plane, and memory feedback boundary.
- `docs/policies/environment-separation.md`: staging and production environment separation rules and resource naming manifest.
- `docs/policies/data-governance.md`: data classification, model privacy, audit minimization, and knowledge/data-quality rules.
- `docs/policies/review-gates.md`: review, waiver, and governance-gate rules for high-impact changes.
- `docs/policies/threat-model.md`: production threat model, token-scope closure, and residual security risks.
- `docs/policies/formal-safety-invariants.md`: authoritative profile-sealing invariant catalog with pass/fail semantics.
- `docs/policies/formal-safety-change-type-matrix.md`: machine-readable invariant-to-change-type validator matrix.
- `docs/runbooks/runtime-preflight.md`: productive Runtime Phase entry gate, naming rules, validation scenarios, risk boundaries, and Phase 1 implementation order.
- `docs/policies/production-readiness.md`: production-ready release gate, evidence rules, status vocabulary, and prioritized production backlog.
- `docs/policies/runtime-contract.md`: generic runtime lifecycle, failure, observability, result, and recomposition contract.
- `docs/reference/runtime-api.md`: runtime start/status/result/cancel/retry API and CLI contract.
- `docs/runbooks/runtime-live-dev-e2e.md`: manual live dev E2E gate for Cloudflare and Hetzner.
- `docs/policies/skill-handler-version-policy.md`: executable skill handler versioning, deprecation, and rollback policy.
- `docs/runbooks/notion-issue-tracking.md`: Notion Issues & Open Questions comment and audit standard.
- `docs/runbooks/post-merge-lifecycle.md`: post-merge cleanup and Notion completion runbook.
- `docs/runbooks/operations-runbook.md`: operations baseline for migrations, smoke tests, diagnostics, and disable paths.
- `docs/policies/error-taxonomy.md`: runtime error taxonomy, class playbooks, and CI gate metrics for F1/F2/R8.
- `docs/roadmap/scas-execution-queue.md`: operational execution order for open SCAS backlog/issues work.
- `docs/roadmap/production-readiness-backlog.md`: prioritized production-readiness implementation backlog.
- `docs/reference/registries.md`: registry implementation semantics for discovery, scoring, filtering, resolution, and graph validation.
- `docs/reference/cloudflare/control-api.md`: Cloudflare Control API bootstrap, validation, and dev deployment runbook.
- `docs/adr/`: architecture decision records.
- `SECURITY.md`: security reporting, secret handling, remediation, and required security gates.
- `AGENTS.md`: repository rules for autonomous agent work and SCAS-specific governance.
- `schemas/module.schema.json`: JSON Schema for selectable module metadata.
- `schemas/runtime-profile.schema.json`: JSON Schema for runtime agent profiles.
- `schemas/runtime-api.schema.json`: JSON Schema for runtime API request and response examples.
- `schemas/runtime-output.schema.json`: JSON Schema for task-class-specific runtime outputs.
- `schemas/write-approval-policy.schema.json`: JSON Schema for controlled write approval policy.
- `schemas/notion-issue-comment-audit.schema.json`: JSON Schema for Notion issue comment audit summaries.
- `schemas/environment-manifest.schema.json`: JSON Schema for the environment separation manifest.
- `schemas/composition-context.schema.json`: JSON Schema for `POST /composition/context`.
- `schemas/retrieval-context.schema.json`: JSON Schema for `POST /retrieval/context`.
- `schemas/error-classification.schema.json`: JSON Schema for runtime error taxonomy classification payloads.
- `schemas/cloudflare-control-plane.schema.json`: JSON Schema for Cloudflare control-plane storage records.
- `schemas/hetzner-runtime-plane.schema.json`: JSON Schema for Hetzner runtime-plane storage records.
- `schemas/knowledge-quality-policy.schema.json`: JSON Schema for generic knowledge/data-quality policy metadata.
- `schemas/skill-handler-coverage.schema.json`: JSON Schema for the production skill handler coverage manifest.
- `schemas/skill-handler-version-policy.schema.json`: JSON Schema for executable skill handler version policy.
- `schemas/production-telemetry-policy.schema.json`: JSON Schema for production alerting policy.
- `schemas/production-telemetry-snapshot.schema.json`: JSON Schema for aggregate telemetry snapshots.
- `schemas/production-security-closure.schema.json`: JSON Schema for production security closure evidence.
- `migrations/cloudflare/d1/`: Cloudflare D1 SQL migrations for control-plane metadata.
- `migrations/hetzner/postgres/`: PostgreSQL migrations for Hetzner runtime-plane storage.
- `policies/`: repository dependency, license, risk-exception, and CI supply-chain policies.
- `policies/security/`: production security closure and token-scope review policy.
- `policies/runtime/`: runtime policy fixtures for skill handler versioning, rollback, and controlled write approval.
- `src/skill_centric_agent_system/composition/`: Task Analyzer, Control Plane client, and Runtime Profile Composer.
- `src/skill_centric_agent_system/runtime/`: Runtime Entry Point, controlled recomposition continuation, Context Manager, executable skill handlers, Flight Recorder writer, profile enforcement, runtime storage ports, PostgreSQL storage session, and JSON artifact store.
- `src/skill_centric_agent_system/registries/`: local deterministic registry implementation.
- `src/skill_centric_agent_system/control_plane/`: control-plane seed generation utilities.
- `workers/control-api/`: Cloudflare Control API Worker with composition, ingestion, queue-backed indexing, retrieval, and AI Gateway routes.
- `scripts/cloudflare/`: Cloudflare bootstrap and D1 seed scripts.
- `scripts/hetzner/`: Hetzner bootstrap and maintenance scripts.
- `scripts/repo/`: repository lifecycle utilities such as post-merge branch cleanup and Notion issue-comment audit validation.
- `scripts/runtime/`: live runtime gate scripts.
- `scripts/operations/`: operations evidence and telemetry evaluation scripts.
- `scripts/security/`: secret, workflow, ruleset, dependency, Actions-BOM, and SBOM governance scripts.
- `docs/runbooks/github-governance-drift.md`: recovery path for scheduled/manual live GitHub governance drift findings.
- `examples/modules/`: representative selectable module metadata.
- `examples/tasks/`: representative task inputs.
- `examples/profiles/`: representative composed profiles.
- `examples/control-plane/`: representative Cloudflare control-plane storage records and generated dev D1 seed SQL.
- `examples/control-api/`: representative Control API request and response payloads.
- `examples/runtime-api/`: representative Runtime API request and response payloads.
- `examples/runtime-outputs/`: representative validated runtime output payloads.
- `examples/runtime/`: deterministic runtime governance manifests and action-plan examples.
- `examples/infrastructure/`: environment separation manifest for dev, staging, and prod.
- `examples/governance/`: representative knowledge/data-quality policy fixtures.
- `examples/operations/`: production telemetry policy and aggregate snapshot fixtures.
- `examples/evaluations/`: analyzer, scoring, and controlled-learning evaluation fixtures.
- `examples/runtime-plane/`: representative Hetzner runtime-plane storage records.
- `tests/`: executable contract tests for schemas, examples, and cross-field invariants.

## Local Validation

Install development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run contract tests:

```powershell
python -m pytest
```

Run linting:

```powershell
python -m ruff check .
```

Validate the production skill handler coverage manifest:

```powershell
python scripts\runtime\skill_handler_coverage.py --check
```

Run security and governance checks:

```powershell
python scripts\security\check_no_dotenv_files.py
python scripts\security\validate_ruleset_config.py
python scripts\security\validate_dependency_policy.py
python scripts\security\check_workflow_hardening.py
python scripts\security\generate_actions_bom.py --output security-evidence\actions-bom.json
python scripts\security\validate_actions_bom.py security-evidence\actions-bom.json
python scripts\security\generate_sbom.py --output security-evidence\release-sbom.json
python scripts\security\validate_sbom.py security-evidence\release-sbom.json
python scripts\operations\evaluate_error_classification_gates.py `
  --policy examples\operations\error-classification-gate-policy.json `
  --snapshot examples\operations\error-classification-gate-snapshot.json `
  --fail-on-failed
```

Start a local fixture-backed runtime run:

```powershell
scas-runtime-start `
  --task-file examples\tasks\code-review-task.json `
  --composition-context-file examples\control-api\composition-context-response.json `
  --artifact-root .scas-runtime `
  --repository-root . `
  --run-minimal-loop
```

The command starts the Analyzer -> Composer -> Runtime Entry Point path without
external services. With `--run-minimal-loop`, it also runs the first
Context/Planner/Executor/Validator loop, invokes only profile-allowed read
tools, writes tool input/output artifacts under the artifact root, and prints
the run/profile summary.

Start the same path against Hetzner PostgreSQL storage when the database URL is
available in the environment:

```powershell
scas-runtime-start `
  --task-file examples\tasks\code-review-task.json `
  --control-plane-url $env:SCAS_CONTROL_API_URL `
  --control-plane-token $env:SCAS_CONTROL_API_TOKEN `
  --artifact-root /opt/scas/runtime `
  --repository-root . `
  --storage-mode postgres `
  --database-url $env:SCAS_RUNTIME_DATABASE_URL `
  --run-minimal-loop
```

Plan runtime artifact retention cleanup without deleting anything:

```powershell
scas-runtime retention plan `
  --storage-mode postgres `
  --database-url $env:SCAS_RUNTIME_DATABASE_URL `
  --artifact-root /opt/scas/runtime
```

Run the same cleanup in dry-run apply mode. This writes an auditable cleanup
report but still does not delete artifacts:

```powershell
scas-runtime retention apply `
  --storage-mode postgres `
  --database-url $env:SCAS_RUNTIME_DATABASE_URL `
  --artifact-root /opt/scas/runtime
```

Delete expired artifacts only after reviewing the dry-run output:

```powershell
scas-runtime retention apply `
  --storage-mode postgres `
  --database-url $env:SCAS_RUNTIME_DATABASE_URL `
  --artifact-root /opt/scas/runtime `
  --confirm
```

Generate the Cloudflare D1 dev seed from module contracts:

```powershell
python scripts\cloudflare\generate_control_plane_seed.py --output examples\control-plane\dev-seed.sql
```

Install Worker dependencies:

```powershell
npm install
```

Run Worker checks:

```powershell
npm run worker:types
npm run worker:typecheck
npm run worker:test
npm run worker:check
```

## GitHub Actions

`.github/workflows/ci.yml` runs contract tests, linting, skill handler coverage
manifest validation, JSON syntax checks, Worker type checks, and Worker Vitest
tests on pushes to `main` and pull requests.

`.github/workflows/security-governance.yml` runs repository governance,
secret-scanning, dependency-audit, workflow-hardening, Actions-BOM, and
release-SBOM gates. `.github/workflows/dependency-review.yml` runs GitHub
Dependency Review for pull requests. `.github/workflows/codeql.yml` runs CodeQL
analysis for Python and Worker code. External GitHub Actions in workflows are
pinned to full commit SHAs and checked by `scripts/security/check_workflow_hardening.py`.

The same workflow also has a manual `workflow_dispatch` infrastructure smoke
test. Run it with `run_infra_smoke = true` after the required GitHub Actions
secrets are configured:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ZONE_ID`
- `HETZNER_HOST`
- `HETZNER_SSH_KEY`
- `HETZNER_USER`
- `OPENAI_API_KEY`
- `AI_GATEWAY_AUTH_TOKEN` when Cloudflare Authenticated Gateway is enabled
- `CONTROL_API_TOKEN`

`CLOUDFLARE_API_TOKEN` must be scoped for the Cloudflare account and allow
Worker script writes. The AI Gateway rollout deploys Worker code and uploads
Worker secrets through Wrangler, so a token that only reads account resources
or validates Cloudflare connectivity is not sufficient.

`CONTROL_API_TOKEN` is used by the manual dev Worker deployment job to
configure the Worker secret. Endpoint-scoped Worker secrets can be configured
manually with Wrangler when the single automation token is too broad.

`HETZNER_SSH_KEY` must contain the complete private OpenSSH key block, including
the private OpenSSH key header and footer lines. Do not use the public
`ssh-ed25519 ...` line or the `SHA256:...` fingerprint as this secret.

Cloudflare Control API dev deployment is manual in the same workflow. Run it
with `deploy_control_api_dev = true` or locally with `npm run worker:deploy:dev`
when Wrangler is authenticated.

Run the AI Gateway dev deployment and live LLM smoke with:

```powershell
gh workflow run ci.yml `
  -f deploy_control_api_dev=false `
  -f run_ai_gateway_live_smoke=true `
  -f run_infra_smoke=false
```

That workflow uploads `OPENAI_API_KEY`, optional `AI_GATEWAY_AUTH_TOKEN`, and
`CONTROL_API_TOKEN` as Worker secrets during the Worker deploy, injects
`AI_GATEWAY_ACCOUNT_ID` from the GitHub `CLOUDFLARE_ACCOUNT_ID` secret at
deploy time, keeps `AI_GATEWAY_ID` at `default` unless the repository variable
overrides it, deploys the dev Worker, and calls
`POST /ai-gateway/openai/chat/completions`.

`OPENAI_API_KEY` remains the OpenAI provider key. `AI_GATEWAY_AUTH_TOKEN` is
sent separately as `cf-aig-authorization` when the Cloudflare AI Gateway has
Authenticated Gateway enabled. The live-smoke workflow requires
`AI_GATEWAY_AUTH_TOKEN` as a GitHub Actions secret because the workflow deploys
Worker code and secrets from GitHub; setting it only on the Worker is not
enough for repeatable deploys.

Live runtime gates are manual in `.github/workflows/live-runtime-gates.yml`.
Run the live dev E2E gate with:

```powershell
gh workflow run live-runtime-gates.yml `
  -f run_live_dev_e2e=true `
  -f run_postgres_concurrency_smoke=false `
  -f run_live_retrieval_vectorize_smoke=false `
  -f seed_control_plane_dev=true `
  -f live_task_suite=generic
```

Run the live Postgres concurrency smoke with:

```powershell
gh workflow run live-runtime-gates.yml `
  -f run_live_dev_e2e=false `
  -f run_postgres_concurrency_smoke=true `
  -f run_live_retrieval_vectorize_smoke=false
```

Run the live retrieval and Vectorize smoke with:

```powershell
gh workflow run live-runtime-gates.yml `
  -f run_live_dev_e2e=false `
  -f run_postgres_concurrency_smoke=false `
  -f run_live_retrieval_vectorize_smoke=true `
  -f seed_control_plane_dev=true
```

The workflow uses GitHub Actions secrets, uploads the checked-out commit to the
Hetzner host, runs the selected live gate scripts there, and writes runtime
artifacts below `/opt/scas/runtime/dev/live-gates/<github-run-id>`.
When `run_live_dev_e2e=true`, the workflow also uploads a non-secret
`live-runtime-handler-binding-evidence` artifact containing the resolved
`skill_handlers` from the planner checkpoint for each live case.

Runtime retention cleanup is scheduled in
`.github/workflows/runtime-retention-cleanup.yml`. The scheduled run is
dry-run only against the dev Hetzner artifact root. Manual dispatch can target
`dev`, `staging`, or `prod`; destructive deletion requires choosing
`cleanup_mode=confirmed-delete` and remains disabled for scheduled runs. Each
run uploads `runtime-retention-cleanup-evidence` with the cleanup report and
exit status.

Production readiness evidence is manual in
`.github/workflows/production-readiness.yml`. Run evidence-only mode while
staging and production resources are still being prepared:

```powershell
gh workflow run production-readiness.yml `
  -f target_environment=dev `
  -f release_scope=initial-productive-core `
  -f certification_mode=evidence-only
```

Certification mode requires references to matching live runtime and AI Gateway
smoke workflow runs from the same repository and release commit:

```powershell
gh workflow run production-readiness.yml `
  -f target_environment=prod `
  -f release_scope=production-runtime `
  -f certification_mode=certify `
  -f live_runtime_gates_run_url=https://github.com/OWNER/REPO/actions/runs/RUN_ID `
  -f ai_gateway_smoke_run_url=https://github.com/OWNER/REPO/actions/runs/RUN_ID
```

The current dev Worker is:

```text
https://scas-control-api-dev.still-butterfly-bbff.workers.dev
```

## Build Rules

- Keep the runtime single-agent unless the product direction changes explicitly.
- Do not grant every tool, data source, memory scope, or knowledge source by default.
- Use registries, scoring, policies, and validators for self-assembly.
- Version durable decisions in `docs/adr/`.
- Track repository tasks in Notion through `$notion-repo-work-tracker`.
- Follow `AGENTS.md`, `SECURITY.md`, `docs/policies/data-governance.md`, and
  `docs/policies/review-gates.md` for autonomous repository changes.

## Next Steps

1. Provision and validate staging/prod resources from the environment manifest.
2. Expand production skill handler coverage beyond the current manifest-covered fixture set.
3. Run the final certification after live infrastructure and handler coverage gates are complete.

