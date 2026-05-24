# Review Gates

## Purpose

Review gates protect security, data governance, code quality, and production
evidence without turning every autonomous agent change into a heavyweight
approval process.

## Mandatory Gates

The following gates are mandatory when the changed files affect security,
governance, contracts, workflows, dependencies, authentication, data boundaries,
or production evidence:

- secret scanning and tracked `.env` guard,
- dependency review and vulnerability audit,
- workflow hardening and pinned GitHub Actions,
- CODEOWNERS review for high-impact paths,
- main-branch ruleset desired-state validation,
- schema and contract tests,
- data-governance and quality-policy tests,
- production-readiness evidence for release claims.

## High-Impact Paths

High-impact paths are listed in `.github/CODEOWNERS` and include workflows,
rulesets, policies, schemas, migrations, Control API code, runtime enforcement,
composition logic, ADRs, production readiness documents, and data-governance
documents.

## Supporting Guardrails

These controls guide agent work and should be easy to run locally:

- `python scripts/security/check_no_dotenv_files.py`
- `python scripts/security/validate_ruleset_config.py`
- `python scripts/security/validate_dependency_policy.py`
- `python scripts/security/check_workflow_hardening.py`
- `python scripts/security/generate_actions_bom.py`
- `python scripts/security/validate_actions_bom.py`

Optional pre-commit hooks may run these checks locally, but the authoritative
blocking decision belongs to CI and branch protection.

## Post-Merge Lifecycle

Merged topic branches should be cleaned up with the repository-owned runbook in
`docs/post-merge-lifecycle.md`. The supporting dry-run command is:

```powershell
python scripts\repo\post_merge_cleanup.py --pr <number>
```

The cleanup script verifies that the PR is merged before planning local or
remote branch deletion and records the Notion completion evidence that still
must be written by the agent or maintainer.

## Waivers

A waiver is allowed only when it records:

- affected gate,
- risk,
- owner,
- expiry condition,
- compensating control,
- follow-up task.

Waivers cannot permit committed secrets, unauthorized production access,
unbounded data movement, or unaudited production-ready claims.
