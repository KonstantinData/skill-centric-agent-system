# Security Policy

## Supported Branch

Security fixes are maintained on `main`. Production-readiness evidence and
release decisions must refer to a specific commit SHA.

## Reporting Security Issues

Report suspected vulnerabilities, exposed secrets, unsafe workflow changes,
authorization bypasses, data-boundary violations, or dependency risks through a
private repository issue, private maintainer channel, or GitHub private
vulnerability reporting when enabled.

Include:

- affected commit SHA or branch,
- impacted component,
- reproduction steps or observed evidence,
- whether any secret, token, customer data, runtime artifact, or memory record
  may be exposed.

Do not include live secret values, bearer tokens, private keys, raw runtime
artifacts, or confidential data in the report.

## Secret Handling

Secrets must come from GitHub Actions secrets, Cloudflare Worker secrets,
account-level secret bindings, or host environment variables. They must not be
committed, copied into prompts, stored in examples, written to logs, or included
in production-readiness evidence.

Tracked `.env` files are not allowed. Local `.env.example` or `.env.sample`
files may document variable names only and must not contain secret values.

If a secret is committed or logged:

1. Revoke and rotate the secret immediately.
2. Remove the secret from the current tree.
3. Run the repository secret-scan gates again.
4. Record the affected path, remediation, owner, and timestamp in the security
   issue or release evidence.

## Token Scope And Rotation

Production security closure is tracked in
`policies/security/production-security-closure.json` and validated by
`python scripts/security/validate_security_closure.py`.

Release candidates must review these secrets before certification:

- `CLOUDFLARE_API_TOKEN`: scoped to the target account, environment, and
  workflow purpose; Worker script write permission is required only for deploy
  jobs.
- `CONTROL_API_TOKEN`: endpoint-scoped where practical; all-scope automation
  token only for trusted jobs that need all protected endpoints.
- `OPENAI_API_KEY`: provider key stored as a Worker or GitHub Actions secret.
- `AI_GATEWAY_AUTH_TOKEN`: optional Cloudflare Authenticated Gateway token,
  rotated independently from the provider key.
- `HETZNER_SSH_KEY`: environment-specific Runtime Plane host access, validated
  as a private OpenSSH key before use.

Rotate the relevant secret immediately after suspected exposure and before any
production certification that depends on a stale, unknown-owner, or reused
credential.

## Required Security Gates

Production-ready claims require passing:

- repository tests and linting,
- Worker typecheck, tests, and dry-run deploy,
- secret scanning,
- tracked `.env` guard,
- dependency and vulnerability review,
- workflow hardening and pinned-action checks,
- CODEOWNERS and main-branch protection desired-state validation,
- production security closure validation,
- data-governance and quality-contract tests.

Security or governance waivers must include an owner, expiry condition, risk,
and compensating control.
