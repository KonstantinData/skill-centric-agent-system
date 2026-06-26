# Liquisto Tenant Admin Bootstrap

Last updated: 2026-06-25 21:12 Europe/Berlin

This runbook defines the non-secret repository contract for bootstrapping the
initial Liquisto tenant owner and tenant-admin access. The actual owner identity
and contact data belong in the approved operational source, not in public
fixtures, examples, workflow logs, or release evidence.

## Scope

```text
tenant_id: liquisto
area_id: liquisto
hostname: liquisto.cloud
admin routes: /admin/users, /admin/roles, /admin/settings
```

The bootstrap path must create the initial membership through the tenant-admin
Control API or an approved one-time operational bootstrap with equivalent
server-side authorization and audit behavior. Do not hardcode the owner in
`examples/tenants/liquisto.json`.

The manual `Tenant Admin Bootstrap` workflow
(`.github/workflows/tenant-admin-bootstrap.yml`) bootstraps staging and
production from environment-scoped GitHub Actions secrets. It writes only
sanitized membership, role, tenant, environment, and workflow evidence.

## Preconditions

- The approved operational source contains the initial owner identity.
- The Control Plane tenant record exists for `liquisto`.
- The tenant admin API is reachable in the target environment.
- The operator has an environment-scoped tenant-admin token.
- Upstream authentication for the UI is approved before any public admin route
  is exposed.

## Bootstrap Procedure

1. Confirm hostname authority resolves server-side to the Liquisto tenant.
2. Load the initial owner identity from the approved operational source.
3. Create or verify exactly one active owner membership for the Liquisto tenant.
4. Assign the `liquisto-owner` role through the tenant-admin API path.
5. Verify the owner session context contains only Liquisto tenant roles.
6. Verify non-admin and cross-tenant access attempts fail closed.
7. Record a sanitized audit summary with membership ID, role ID, target tenant,
   environment, workflow or operator reference, and timestamp.

Do not record email addresses, private keys, bearer tokens, session JSON,
provider user IDs, or raw API responses in repository docs or public evidence.

## Verification

Local contract checks:

```bash
python -m pytest tests/test_tenant_runtime_e2e.py tests/test_tenant_isolation_matrix.py
python -m pytest tests/test_liquisto_workbench_ui.py
```

Target-environment checks:

- Tenant admin context loads for the owner membership.
- `/admin/users`, `/admin/roles`, and `/admin/settings` are visible only for
  the owner/admin session.
- A researcher session does not receive admin workspace areas.
- A mismatched tenant hostname or tenant ID is rejected.

## Evidence

Evidence may include:

- workflow URL or operator ticket,
- target environment,
- tenant ID,
- membership ID,
- role ID,
- sanitized audit event IDs,
- verification commands and pass/fail status.

Evidence must not include secrets, raw session context, personal contact data,
or confidential customer data.

Latest production evidence for the current `liquisto.cloud` authority:

| Date | Environment | GitHub run | Result | Evidence |
| --- | --- | --- | --- | --- |
| pending | prod | pending | pending | Re-run `tenant-admin-bootstrap.yml` or an approved read-only tenant-admin verification after the `liquisto.cloud` seed is deployed. |

The post-seed check must confirm tenant `liquisto`, hostname `liquisto.cloud`,
and assignable roles `liquisto-owner` and `liquisto-researcher`.

## Rollback

If the bootstrap was incorrect:

1. Disable the newly created membership for `liquisto` only.
2. Revoke the tenant role assignment.
3. Keep audit records retained.
4. Re-run the non-admin and cross-tenant denial checks.
5. Re-bootstrap only from the approved operational source.
