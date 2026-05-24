# SCAS Threat Model

## Purpose

This document records the current production threat model for the
skill-centric agent system. It is part of the production readiness gate and
must stay versioned with code, policies, workflows, and operational runbooks.

## System Boundary

SCAS is a single runtime-agent system with controlled self-composition. The
runtime may assemble a task-specific profile only through task analysis,
registry discovery, scoring, policy filtering, dependency graph validation, and
immutable runtime profile validation.

The main deployment boundary is:

```text
Cloudflare Control Plane -> Hetzner Runtime Plane
```

Cloudflare owns control metadata, module registry records, validated knowledge
records, approved memory records, queues, indexes, and Control API endpoints.
Hetzner owns runtime execution, PostgreSQL runtime records, Flight Recorder
events, checkpoints, and raw runtime artifacts.

## Assets

| Asset | Primary Risk | Required Control |
| --- | --- | --- |
| Runtime agent profile | Overbroad capability grant | Immutable profile validation and profile enforcement. |
| Runtime artifacts and traces | Confidential content exposure | Store raw artifacts on Hetzner only; reference by URI in evidence. |
| Control API bearer tokens | Unauthorized control-plane access | Endpoint-scoped tokens where practical; all-scope token limited to trusted automation. |
| Cloudflare API token | Unauthorized infrastructure mutation | Environment-scoped GitHub secret; least privilege for deploy/smoke jobs. |
| OpenAI provider key | Provider abuse or disclosure | Worker secret only; never written to logs or evidence. |
| AI Gateway auth token | Gateway bypass or disclosure | Optional Worker/GitHub secret; rotate independently from provider key. |
| Hetzner SSH key | Runtime host compromise | GitHub secret only; private-key format checked; no committed copies. |
| Knowledge and memory records | Unapproved data promotion | Data governance, sensitivity, scope, owner, and validation gates. |
| Release evidence | False production-ready claim | Non-secret evidence artifact with explicit gaps and gate results. |

## Trust Boundaries

| Boundary | Direction | Risk | Controls |
| --- | --- | --- | --- |
| User or automation to Control API | External to Cloudflare | Unauthorized protected endpoint access | Bearer auth, endpoint-scoped tokens, CI tests, unauthenticated route checks. |
| Control Plane to Runtime Plane | Cloudflare to Hetzner | Raw runtime data leaving Hetzner | Data governance, aggregate telemetry only, artifact URI references. |
| Runtime to selected tools | Runtime to local adapters | Tool or data-scope escalation | Tool Gateway allowlists, data-scope checks, risk gating, policy denials. |
| Runtime to memory promotion | Hetzner to Cloudflare | Confidential or secret memory ingestion | Memory candidate validation and policy-approved promotion. |
| GitHub Actions to infrastructure | GitHub to Cloudflare/Hetzner | Secret leak or unintended deployment | Pinned Actions, minimal permissions, environment secrets, workflow hardening. |
| Release evidence to repository artifacts | CI to durable evidence | Secret or raw trace disclosure | Secret scanning, evidence minimization, schema and script validation. |

## Threat Scenarios And Closures

| ID | Scenario | Status | Closure Evidence |
| --- | --- | --- | --- |
| T1 | Runtime self-grants unselected tools, data scopes, skills, policies, or validators. | Closed | Profile enforcement tests, immutable recomposition contract, Tool Gateway tests. |
| T2 | Ambiguous tasks receive specialized capabilities instead of review or fallback. | Partially closed | Analyzer ambiguity signaling exists; P5.09 remains open for human-review quality gates. |
| T3 | Raw runtime traces or tool outputs are copied into Cloudflare, Notion, logs, or release evidence. | Closed | Data governance, telemetry aggregate-only policy, evidence scripts, secret scanning. |
| T4 | Control API protected routes can be used without authorization. | Closed | Worker auth tests and runtime preflight route checks. |
| T5 | Broad automation tokens are used where endpoint-scoped tokens are sufficient. | Closed for current release gate | Token-scope review documented in `policies/security/production-security-closure.json`; endpoint-scoped token guidance remains required for production provisioning. |
| T6 | GitHub Actions workflow dependency or supply-chain drift changes trusted CI behavior. | Closed | Pinned Actions, workflow hardening, Actions-BOM, Dependency Review, CodeQL. |
| T7 | Runtime retention cleanup deletes unsafe paths or hides missing artifacts. | Closed | URI resolution rules, dry-run defaults, strict missing mode, cleanup evidence tests. |
| T8 | Write-capable runtime actions mutate repository data without approval or rollback. | Closed for first write slice | `filesystem-write` approval policy, dry-run default, rollback metadata, controlled write tests. |
| T9 | Production release evidence claims readiness while gates are missing. | Closed for repository evidence | Evidence script records open gaps and refuses certification inputs that do not match expected runs. |
| T10 | Secrets appear in committed files, examples, evidence, logs, or Notion comments. | Closed by gate | Secret scanning, `.env` guard, security policy, and evidence minimization. |

## Token Scope Review

Token review is captured in:

```text
policies/security/production-security-closure.json
```

The current closure requires:

- `CLOUDFLARE_API_TOKEN` scoped to the target environment and job purpose.
- `CONTROL_API_TOKEN` used only for trusted automation that needs all protected
  endpoints; endpoint-scoped tokens are preferred for runtime clients.
- `OPENAI_API_KEY` stored only as a provider secret and never copied into
  repository artifacts.
- `AI_GATEWAY_AUTH_TOKEN` rotated independently when Authenticated Gateway is
  enabled.
- `HETZNER_SSH_KEY` stored only as a GitHub Actions secret and validated as a
  private OpenSSH key before use.

## Secret Rotation Closure

Rotation requirements are documented in `SECURITY.md` and
`docs/operations-runbook.md`. A production certification must rotate or verify
the age and owner of infrastructure secrets before final release if any secret
was exposed, logged, copied into a prompt, or used outside its approved
automation path.

## Residual Risks

The following risks are intentionally not closed by P5.08:

- P5.09 must make ambiguous production tasks enter a human-review path instead
  of overgranting.
- Broader production skill handler coverage beyond the current manifest-covered
  fixtures remains a separate backlog item.
- Staging and production resources still need live provisioning and validation
  before a production-ready claim.

## Threat Model Closure

P5.08 is closed when all of the following are true:

- this document is current,
- `policies/security/production-security-closure.json` validates,
- the security-governance workflow runs the closure validator,
- production-readiness evidence includes a passed security closure gate, and
- P5.08 is no longer listed in `open_release_gaps`.
