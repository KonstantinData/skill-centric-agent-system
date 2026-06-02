# GitHub Governance Drift Runbook

## Purpose

This runbook defines how to interpret and recover from live GitHub governance
drift without granting scheduled automation write access to repository rules.

The scheduled/manual workflow is
`.github/workflows/github-governance-drift.yml`. It compares the live
`main-protection` ruleset with `.github/rulesets/main-protection.json` and
uploads `github-governance-drift-evidence`.

## Evidence

The workflow writes:

```text
security-evidence/github-governance-drift.json
```

The artifact includes:

- `severity` - impact of the drift,
- `confidence` - certainty of the finding,
- `remediation_class` - permitted recovery path,
- `desired` - committed desired-state summary,
- `live` - live GitHub ruleset summary, and
- `recommended_action` - next operator action.

## Severity Model

| Severity | Meaning |
| --- | --- |
| `critical` | Live GitHub protection is weaker than desired state. |
| `high` | Enforcement, review, or permission posture is materially different. |
| `medium` | Live and desired state differ without immediate weakening evidence. |
| `low` | Live state is stronger or has extra checks that should be reviewed. |

## Recovery Classes

| Class | Recovery |
| --- | --- |
| `manual_github_fix` | Maintainer updates live GitHub settings to match desired state, then reruns the workflow. |
| `repo_pr_fix` | Desired state is updated by PR because live state is intentionally stronger or newer. |
| `permission_setup` | Configure a read-only GitHub App or token with repository Administration read permission. |
| `escalate` | Stop and open a tracked issue; no safe remediation is available. |

## Current Expected Drift Example

If live `required_approving_review_count` is `0` while desired state is `1`,
the workflow must fail with:

- `severity = critical`,
- `confidence = confirmed`,
- `remediation_class = manual_github_fix`.

Recovery is to set the live `main-protection` pull-request rule to require one
approval, then rerun `GitHub Governance Drift`.

## Token Policy

The drift workflow is read-only. Prefer a dedicated GitHub App installation
token with:

- `Metadata: read`,
- `Administration: read`.

Do not use scheduled workflows with `Administration: write`. A future repair
workflow, if added, must be `workflow_dispatch` only and protected by manual
approval.
