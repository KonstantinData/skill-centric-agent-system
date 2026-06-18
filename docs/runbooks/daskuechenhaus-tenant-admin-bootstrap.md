# Daskuechenhaus Tenant Admin Bootstrap

Last updated: 2026-06-18 18:35 Europe/Berlin

This runbook defines the non-secret repository contract for bootstrapping the
initial Daskuechenhaus tenant owner and tenant-admin access. Actual admin
principals, contact details, and provider identifiers belong in the approved
operational source, not in fixtures, logs, public evidence, or repository docs.

## Scope

```text
tenant_id: daskuechenhaus
area_id: daskuechenhaus
hostname: daskuechenhaus.condata.io
admin routes: /admin/users, /admin/roles, /admin/settings
```

The bootstrap path must create the initial membership through the tenant-admin
Control API or an approved one-time operational bootstrap with equivalent
server-side authorization and audit behavior. Do not hardcode the owner in
`examples/tenants/daskuechenhaus.json`.

The manual `Tenant Admin Bootstrap` workflow
(`.github/workflows/tenant-admin-bootstrap.yml`) bootstraps staging and
production from environment-scoped GitHub Actions secrets. It writes only
sanitized membership, role, tenant, environment, and workflow evidence.

## Required Secrets

Use tenant-specific, environment-scoped GitHub Actions secrets:

```text
SCAS_STAGING_DASKUECHENHAUS_OWNER_PRINCIPAL_ID
SCAS_STAGING_DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPAL_IDS_JSON
SCAS_STAGING_UI_LOGIN_USERS_JSON
SCAS_PROD_DASKUECHENHAUS_OWNER_PRINCIPAL_ID
SCAS_PROD_DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPAL_IDS_JSON
SCAS_PROD_UI_LOGIN_USERS_JSON
```

Principal IDs must be stable non-secret identifiers, not email addresses. The
additional admin secret is an optional JSON string array. The workflow also
requires the existing environment-scoped Control API token for the selected
target environment.

## Approved Role Model

- The initial owner membership uses `tm-daskuechenhaus-initial-owner` and
  `daskuechenhaus-owner`.
- Additional tenant admins use deterministic `tm-daskuechenhaus-admin-NN`
  memberships and `daskuechenhaus-admin`.
- `daskuechenhaus-admin` grants only `tenant-admin`. It has no research
  capability, no data-source grants, and no filesystem tools.
- Repository access is managed outside the SCAS tenant role bundle and is not
  implied by tenant admin access.
- UI local login users are stored only in `SCAS_*_UI_LOGIN_USERS_JSON` with
  PBKDF2 password hashes. Do not store raw passwords, login names, email
  addresses, or provider user IDs in repository files or public evidence.

## Preconditions

- The approved operational source contains the initial owner identity.
- The Control Plane tenant record exists for `daskuechenhaus`.
- The tenant admin API is reachable in the target environment.
- The operator has an environment-scoped tenant-admin or Control API token.
- Public UI routing for `daskuechenhaus.condata.io` resolves to the
  Daskuechenhaus tenant runtime, not the Liquisto runtime.
- Upstream authentication for the UI is approved before any public admin route
  is exposed.

## Bootstrap Procedure

1. Confirm hostname authority resolves server-side to the Daskuechenhaus tenant.
2. Load the initial owner principal from the approved operational source.
3. Create or verify exactly one active owner membership for the Daskuechenhaus
   tenant.
4. Assign the `daskuechenhaus-owner` role through the tenant-admin API path.
5. Create or verify additional admin memberships from the optional additional
   admin principal secret and assign only `daskuechenhaus-admin`.
6. Verify owner and admin session contexts contain only Daskuechenhaus tenant
   roles.
7. Verify non-admin, cross-tenant, and admin-without-research access attempts
   fail closed.
8. Record a sanitized audit summary with membership ID, role ID, target tenant,
   environment, workflow or operator reference, and timestamp.

Do not record email addresses, private keys, bearer tokens, session JSON,
provider user IDs, raw API responses, or confidential customer data in
repository docs or public evidence.

## Workflow Invocation

Plan-only verification:

```bash
gh workflow run tenant-admin-bootstrap.yml \
  -f target_environment=staging \
  -f tenant_id=daskuechenhaus \
  -f hostname=daskuechenhaus.condata.io \
  -f apply_bootstrap=false \
  -f confirm_production=false
```

Production apply requires explicit production confirmation:

```bash
gh workflow run tenant-admin-bootstrap.yml \
  -f target_environment=prod \
  -f tenant_id=daskuechenhaus \
  -f hostname=daskuechenhaus.condata.io \
  -f apply_bootstrap=true \
  -f confirm_production=true
```

## Verification

Local contract checks:

```bash
python -m pytest tests/test_tenant_runtime_e2e.py tests/test_tenant_isolation_matrix.py
python -m pytest tests/test_streamlit_business_ui.py tests/test_streamlit_task_intake_ui.py
```

Target-environment checks:

- Tenant admin context loads for membership `tm-daskuechenhaus-initial-owner`.
- The active owner role is `daskuechenhaus-owner`.
- Additional tenant admin memberships, when configured, use
  `daskuechenhaus-admin`.
- `daskuechenhaus-admin` can see `/admin` but cannot see `/research`.
- `/admin/users`, `/admin/roles`, and `/admin/settings` are visible only for
  the owner/admin session.
- A researcher session does not receive admin workspace areas.
- Liquisto users, roles, data sources, knowledge scopes, and memory scopes are
  not visible or assignable.
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
provider user IDs, raw API responses, or confidential customer data.

Latest production evidence:

| Date | Environment | GitHub run | Result | Evidence |
| --- | --- | --- | --- | --- |
| 2026-06-18 17:10 Europe/Berlin | prod | no bootstrap run yet | pending | Live UI check showed `daskuechenhaus.condata.io` serving Daskuechenhaus tenant content and `Initial owner pending`. |

## Rollback

If the bootstrap was incorrect:

1. Disable the newly created membership for `daskuechenhaus` only.
2. Revoke the tenant role assignment.
3. Keep audit records retained.
4. Re-run the non-admin and cross-tenant denial checks.
5. Re-bootstrap only from the approved operational source.
