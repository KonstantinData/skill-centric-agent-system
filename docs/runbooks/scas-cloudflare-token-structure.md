# SCAS Cloudflare Token Structure

SCAS Cloudflare automation uses purpose-scoped GitHub Actions secrets. Account
and zone identifiers may point to the same Cloudflare account or zone across
environments, but management API tokens must be scoped by environment and job
purpose.

Cloudflare API tokens are permissioned separately for Account, Zone, and User
resources. Keep SCAS tokens on the narrowest resource set that can complete the
workflow, and prefer read-only Zone permissions for evidence collection.

## GitHub Secret Matrix

| Secret | Purpose | Expected Resource |
| --- | --- | --- |
| `SCAS_DEV_CLOUDFLARE_ACCOUNT_ID` | Dev Cloudflare account identifier | `info@condata.io` account |
| `SCAS_STAGING_CLOUDFLARE_ACCOUNT_ID` | Staging Cloudflare account identifier | `info@condata.io` account |
| `SCAS_PROD_CLOUDFLARE_ACCOUNT_ID` | Prod Cloudflare account identifier | `info@condata.io` account |
| `CLOUDFLARE_ZONE_ID` | Shared tenant zone identifier | `condata.io` zone |
| `SCAS_DEV_CLOUDFLARE_DEPLOY_TOKEN` | Dev Worker deploys, Worker secret sync, D1 seed operations | Dev SCAS Cloudflare resources |
| `SCAS_STAGING_CLOUDFLARE_DEPLOY_TOKEN` | Staging Worker deploys, Worker secret sync, controlled staging provisioning | Staging SCAS Cloudflare resources |
| `SCAS_PROD_CLOUDFLARE_DEPLOY_TOKEN` | Production Worker deploys and Worker secret sync | Production SCAS Cloudflare resources |
| `SCAS_STAGING_CLOUDFLARE_EVIDENCE_TOKEN` | Read-only tenant DNS, TLS, and Worker route evidence | `condata.io` zone |
| `SCAS_PROD_CLOUDFLARE_EVIDENCE_TOKEN` | Read-only tenant DNS, TLS, and Worker route evidence | `condata.io` zone |
| `AI_GATEWAY_AUTH_TOKEN` | Runtime bearer token for Cloudflare Authenticated Gateway | Worker/runtime secret, not a Cloudflare management token |

Using the same value for all `*_CLOUDFLARE_ACCOUNT_ID` secrets is correct when
all environments run in the same Cloudflare account. Using the same
`CLOUDFLARE_ZONE_ID` is correct while all SCAS tenant hostnames are under
`condata.io`. Keep the environment-prefixed names anyway so a future account or
zone split does not require workflow rewrites.

## Workflow Mapping

| Workflow | GitHub Secrets | Internal Tool Variable |
| --- | --- | --- |
| `.github/workflows/ci.yml` deploy job | `SCAS_{ENV}_CLOUDFLARE_ACCOUNT_ID`, `SCAS_{ENV}_CLOUDFLARE_DEPLOY_TOKEN` | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` for Wrangler |
| `.github/workflows/control-api-worker-secrets.yml` | `SCAS_{ENV}_CLOUDFLARE_ACCOUNT_ID`, `SCAS_{ENV}_CLOUDFLARE_DEPLOY_TOKEN` | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` for Wrangler |
| `.github/workflows/live-runtime-gates.yml` when `seed_control_plane_dev=true` | `SCAS_{ENV}_CLOUDFLARE_ACCOUNT_ID`, `SCAS_{ENV}_CLOUDFLARE_DEPLOY_TOKEN` | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` for Wrangler |
| `.github/workflows/tenant-cloudflare-evidence.yml` | `CLOUDFLARE_ZONE_ID`, `SCAS_{STAGING,PROD}_CLOUDFLARE_EVIDENCE_TOKEN` | `CLOUDFLARE_API_TOKEN` for Cloudflare REST requests |

The internal `CLOUDFLARE_API_TOKEN` environment variable is still used where
Wrangler or the Cloudflare REST client expects that name. It must be populated
only from purpose-scoped SCAS secrets in SCAS workflows.

Production Worker secret syncs are production mutations. The
`control-api-worker-secrets.yml` workflow must bind `target_environment=prod`
to the protected `production` GitHub Environment and requires
`confirm_production=true` before it writes Worker secrets.

## Permission Targets

Deploy tokens:

- Account-scoped to the SCAS Cloudflare account.
- Worker script edit permissions for `wrangler deploy`.
- Worker secret update/list support for `wrangler secret bulk` and
  `wrangler secret list`.
- D1 migration and execute permissions only where the workflow seeds or migrates
  Control Plane data.
- Additional Queues, Vectorize, R2, or AI Gateway permissions only for
  workflows that create or mutate those exact resources.

Evidence tokens:

- Zone-scoped to the `condata.io` zone.
- `Zone DNS: Read`.
- `Zone Settings: Read`.
- `Zone Workers Routes: Read`.
- No Worker script, D1, Queues, Vectorize, R2, AI Gateway, or write permissions.

## Migration Rules

- Do not use `SCAS_{ENV}_CLOUDFLARE_API_TOKEN` for new SCAS workflows.
- Do not use legacy unprefixed `CLOUDFLARE_API_TOKEN` as a fallback for SCAS
  deploy, secret-sync, live-gate, or tenant evidence workflows.
- Keep old generic Cloudflare tokens only long enough to prove the replacement
  workflows green, then remove or rotate them out of the repository secrets.
- Name Cloudflare dashboard tokens after the same purpose, for example
  `scas-staging-deploy`, `scas-prod-deploy`,
  `scas-staging-zone-evidence`, and `scas-prod-zone-evidence`.
- Record evidence artifacts, but never print DNS origin values, token values, or
  raw API responses that may expose hidden infrastructure.

## Validation

After adding or rotating secrets, run the workflow that matches the token
purpose:

```bash
gh workflow run tenant-cloudflare-evidence.yml \
  --repo KonstantinData/skill-centric-agent-system \
  -f target_environment=staging \
  -f hostname=<tenant-hostname>.condata.io \
  -f require_worker_route=true
```

For deployment tokens, run the relevant manual deploy or Worker secret sync
workflow for the same environment. A Zone evidence token must not pass Wrangler
deploy or secret sync jobs; a deploy token must not be required by the evidence
workflow.
