# Liquisto Tenant Rollback And Deprovisioning

Last updated: 2026-06-17 23:10 Europe/Berlin

This runbook defines the safe rollback and deprovisioning dry-run path for the
Liquisto tenant. It is tenant-local: no other tenant data, memory, knowledge,
DNS, users, roles, or logs may be changed.

## Scope

```text
tenant_id: liquisto
hostname: liquisto.condata.io
default mode: suspend dry-run
production mutation: requires explicit owner approval
```

Use this runbook before a production release decision and whenever a tenant UI
deployment must be rolled back.

## Dry-Run Checklist

1. Confirm the exact tenant ID, hostname, target environment, requester, and
   intended mode: `suspend`, `archive`, `export`, `delete`, or `recover`.
2. Inventory current tenant state: status, hostnames, memberships, roles, data
   sources, knowledge scope, memory scope, recent runtime profiles, and audit
   log location.
3. Confirm no other tenant references are present in the planned action set.
4. Verify tenant login, task intake, runtime profile creation, retrieval, and
   tool execution can be disabled independently for `liquisto`.
5. Verify Cloudflare/DNS changes are planned only for `liquisto.condata.io`.
6. Verify retained evidence paths do not contain secrets, raw traces, or
   confidential customer data.
7. Verify rollback to the previous Streamlit image is available through
   `.github/workflows/tenant-ui-deploy.yml` evidence or the remote Compose
   override.
8. Run tenant isolation tests locally and record the commit SHA.

## Latest UI Rollback Evidence

Production UI apply run `27719099324` recorded the rollback-relevant state for
the current production deployment:

- target environment: `prod`,
- compose project: `liquisto`,
- compose file: `/opt/liquisto/scas-streamlit-business-ui.override.yml`,
- current image after apply:
  `scas-streamlit-business-ui:655beba1faba6763120198857d1c8aef075d4921`,
- previous image available for rollback:
  `scas-streamlit-business-ui:916b7d87295d685c7ab4c2c8ffc3049297ed9d56`,
- post-deploy Streamlit health check: passed.

Sanitized inventory run `27719494125` confirmed the current container is
healthy and running the applied image. The inventory evidence records only
SCAS-managed configuration keys with redacted values.

## Local Verification

```bash
python -m pytest tests/test_tenant_hostname_resolution.py tests/test_tenant_isolation_matrix.py
python -m pytest tests/test_tenant_runtime_e2e.py tests/test_streamlit_business_ui.py
```

If any test fails, keep the tenant below production-ready and do not execute a
live deprovisioning mutation.

## Suspend Dry Run

For a dry run, prepare but do not apply the following state transitions:

- tenant status: `setup` or `active` to `disabled`,
- hostnames: `liquisto.condata.io` denied by server-side tenant resolution,
- memberships: disabled or blocked from new sessions,
- runtime profiles: no new profiles can be composed,
- data sources: connector access disabled for the tenant,
- knowledge/memory: retained but unavailable to new runtime profiles,
- admin API: audit read remains available to authorized platform operators.

Expected denial behavior:

- unknown hostnames fail closed,
- disabled tenant hostnames fail closed,
- prompt-supplied tenant IDs cannot override hostname authority,
- cross-tenant admin API calls are rejected.

## Apply Rules

Apply mode is allowed only when all are true:

- owner approval is recorded in the approved tracking location,
- target environment is explicit,
- backups or retained evidence have been confirmed,
- dry-run checklist passed,
- rollback target is known,
- the action affects only `liquisto`.

Deletion is irreversible and remains out of scope unless a separate explicit
approval and retention review exists.

## Evidence

Record only sanitized evidence:

- target environment,
- tenant ID and hostname,
- requested mode,
- dry-run status,
- affected object counts,
- audit event IDs,
- workflow URLs,
- commit SHA,
- follow-up blockers.

Do not record tokens, private keys, session JSON, provider credentials, raw
runtime traces, personal contact details, or confidential tenant records.
