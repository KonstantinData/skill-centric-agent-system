# Kinderhaus Heuschrecken Workbench Deployment

This runbook covers the SCAS-managed UI deployment surface for the Kinderhaus
Heuschrecken workbench.

## Tenant Identity

- Tenant ID: `kinderhaus`
- Area ID: `kinderhaus-heuschrecken`
- Primary hostname: `kinderhaus-heuschrecken.cloud`
- UI app: `khh-workbench`
- Native iOS app: `apps/khh-ios`
- Native proof shell: `apps/khh-mobile-proof`
- Dockerfile: `deploy/khh-workbench/Dockerfile`
- App root: `apps/khh-workbench`

The browser Workbench remains the deployed `kinderhaus-heuschrecken.cloud`
surface. The native iOS app is built and released through Xcode/TestFlight/App
Store workflows and must not change this web deployment path.

`kinderhaus` is the canonical tenant identifier. It intentionally omits the
generic `tenant-` prefix so tenant identity, runtime profile validation, queue
records, and deployment inputs use the same stable ID. Skill, workflow,
capability, policy, and validator IDs continue to use the existing hyphenated
module ID style.

## Product Boundary

The workbench is a leadership, deadline, risk, task, and development cockpit.
It is not a master-data system for children, parents, or staff.

Do not store or display:

- complete child, parent, or staff records
- surnames in standard operational views
- private contact details, addresses, birth dates, or contract data
- diagnosis details, medical plans, personnel files, or full legal files

Allowed person references are limited to first name, initials, role labels, or
internal references where needed for operational follow-up.

## Cloudflare Inputs

The tenant UI deploy workflow supports KHH through:

- `KHH_CLOUDFLARE_API_TOKEN`
- `KHH_CLOUDFLARE_ACCOUNT_ID`
- `KHH_CLOUDFLARE_ZONE_ID`
- `SCAS_STAGING_TENANT_KINDERHAUS_OWNER_PRINCIPAL_ID`
- `SCAS_PROD_TENANT_KINDERHAUS_OWNER_PRINCIPAL_ID`

The workflow allowlist only permits Cloudflare DNS sync for
`kinderhaus:kinderhaus-heuschrecken.cloud`. Token values must never be
written to repository files, Notion, logs, or generated evidence.

When `auth_mode=required`, the deploy workflow fails closed even if the
Cloudflare account-level Access API scope is not available to the tenant deploy
token. The managed Nginx origin only proxies to the KHH container when
`cf-access-authenticated-user-email` is present; requests without the
Cloudflare Access identity header receive `403` at the origin. The public smoke
check still accepts only a Cloudflare Access redirect (`302` or `303`) or
`403`, never public workbench HTML.

Manage the account-level Cloudflare Access application and allow policy through
the manual `KHH Cloudflare Access` workflow. It protects only
`kinderhaus-heuschrecken.cloud` and `www.kinderhaus-heuschrecken.cloud` and
validates the allow-list before any API mutation. After applying changes, the
workflow requires both public hostnames to return a Cloudflare Access login
redirect, not only the origin fallback `403`.

The KHH Cloudflare token must allow account-scoped Cloudflare Access
application, policy, and identity-provider operations for
`KHH_CLOUDFLARE_ACCOUNT_ID`. DNS and Origin CA certificate operations remain
zone-scoped to `KHH_CLOUDFLARE_ZONE_ID`.

The managed reverse-proxy step owns one active Nginx server configuration for
the KHH apex and `www` hostnames. Before `nginx -t`, it disables other active
`sites-enabled` entries that declare the same hostnames and records the disabled
entries in deployment evidence. If Nginx validation fails, the workflow restores
the previous managed config and the disabled entries before failing.

## Dry-Run Build

Use the existing manual `Tenant UI Deploy` GitHub Actions workflow with:

- `tenant_id`: `kinderhaus`
- `hostname`: `kinderhaus-heuschrecken.cloud`
- `ui_app`: `khh-workbench`
- `apply_deploy`: `false`

This builds the image and uploads a deployment plan artifact without mutating a
remote host.

## Local Validation

```powershell
npm --prefix apps/khh-workbench run lint
npm --prefix apps/khh-workbench run build
npm --prefix apps/khh-mobile-proof run check
python -m pytest tests/test_khh_workbench_ui.py tests/test_tenant_hostname_resolution.py tests/test_tenant_isolation_matrix.py tests/test_contract_schema_examples.py
python -m pytest tests/test_tenant_runtime_evidence.py
python -m pytest tests/test_platform_neutral_app_readiness.py
python -m pytest tests/test_security_governance.py tests/test_github_actions_workflows.py
python -m ruff check .
```

For applied deployments with `auth_mode=required`, the public smoke check must
observe a Cloudflare Access redirect (`302` or `303`) or `403`. Publicly serving
the KHH cockpit content is a failed gate unless the workflow is explicitly run
in a non-required auth mode.

KHH tenant runtime readiness also requires Tenant Runtime Evidence for
`kinderhaus`. The committed dev fixture in `examples/runtime-evidence/` proves
schema and gate coverage only. Staging or production readiness requires
target-environment evidence with queue, worker, quota, DLQ, and stale-claim
signals captured from the Hetzner Runtime Plane.

## Cloudflare Access Allow-List

Use the `KHH Cloudflare Access` workflow with:

- `apply_changes`: `true`
- `confirm_production`: `true`
- `hostnames`: `kinderhaus-heuschrecken.cloud www.kinderhaus-heuschrecken.cloud`
- `allowed_emails`: the approved KHH maintainer e-mail addresses for this
  release window
- `primary_hostname`: `kinderhaus-heuschrecken.cloud`
- `confirm_hostname`: `kinderhaus-heuschrecken.cloud`

For the initial maintainer access window, the workflow is pinned to
`kontakt@konstantinmilonas.de` and rejects any different allow-list.
