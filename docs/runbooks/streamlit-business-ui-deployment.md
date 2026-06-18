# Streamlit Business UI Deployment

Last updated: 2026-06-18 09:39 Europe/Berlin

This runbook defines the repository-owned deployment path for the SCAS
Streamlit Business UI. It is intentionally manual and fail-closed. Building an
image is safe as a planning step; changing a remote service requires explicit
workflow inputs, target-environment secrets, and upstream authentication
evidence.

## Scope

Primary current tenant:

```text
tenant_id: liquisto
hostname: liquisto.condata.io
service path: apps/streamlit_business_ui/app.py
container definition: deploy/streamlit-business-ui/Dockerfile
workflow: .github/workflows/tenant-ui-deploy.yml
```

The workflow builds a SCAS-owned image from the repository snapshot and, when
`apply_deploy=true`, loads it onto the target Hetzner host and writes a complete
SCAS-managed Docker Compose file for the Streamlit service. It intentionally
does not read the legacy host Compose file, host `.env` files, or legacy Compose
interpolation state. It does not create DNS records, change Cloudflare
configuration, or bypass tenant authentication.

Production deployments must bind the shared UI implementation to exactly one
server-controlled tenant by writing `SCAS_UI_TENANT_ID=<tenant_id>` into the
SCAS-managed environment file. For Liquisto this is `SCAS_UI_TENANT_ID=liquisto`.
In this mode the app loads only that tenant and does not render a tenant
selector.

## Latest Production Inventory

Read-only runtime inventory run
`https://github.com/KonstantinData/skill-centric-agent-system/actions/runs/27719494125`
passed on 2026-06-17 after production apply. It observed:

- `liquisto.condata.io` is served by Nginx and proxied to `127.0.0.1:8501`.
- Container `liquisto-app-1` is healthy and runs
  `streamlit run apps/streamlit_business_ui/app.py`.
- The running image is
  `scas-streamlit-business-ui:655beba1faba6763120198857d1c8aef075d4921`.
- The deployed source revision is
  `655beba1faba6763120198857d1c8aef075d4921`.
- SCAS-managed runtime config keys are present, but values are redacted from
  the evidence artifact.

This verifies the repository-owned Streamlit Business UI is deployed behind the
tenant hostname with the production launch image. Production launch readiness is
certified separately by Production Readiness Evidence run `27719854597`.

Intermediate inventory artifacts from runs `27719268407` and `27719390153` were
deleted because they exposed over-specific server-side session context. Use
`27719494125` or later inventory evidence for production release records.

## Required Secrets

Use environment-specific GitHub Actions secrets. Do not use unprefixed legacy
secrets for staging or production deployment.

Staging:

```text
SCAS_STAGING_HETZNER_HOST
SCAS_STAGING_HETZNER_USER
SCAS_STAGING_HETZNER_SSH_KEY
SCAS_STAGING_UI_SESSION_CONTEXT_JSON
SCAS_STAGING_TENANT_ADMIN_TOKEN
SCAS_STAGING_LIQUISTO_OWNER_PRINCIPAL_ID
```

Production:

```text
SCAS_PROD_HETZNER_HOST
SCAS_PROD_HETZNER_USER
SCAS_PROD_HETZNER_SSH_KEY
SCAS_PROD_UI_SESSION_CONTEXT_JSON
SCAS_PROD_TENANT_ADMIN_TOKEN
SCAS_PROD_LIQUISTO_OWNER_PRINCIPAL_ID
```

`SCAS_*_UI_SESSION_CONTEXT_JSON` must be server-owned session context for the
tenant and must be valid only behind an approved upstream authentication layer.
Do not use fixture role IDs or user-supplied tenant IDs for public deployment.
If an environment-specific session context is not configured, the deploy
workflow can derive a minimal owner session from
`SCAS_*_LIQUISTO_OWNER_PRINCIPAL_ID` after the owner membership has been
bootstrapped through `tenant-admin-bootstrap.yml`. If
`SCAS_*_TENANT_ADMIN_TOKEN` is absent, the workflow falls back to the
environment-scoped Control API token, which carries the Control API `all` scope.

## Build-Only Plan

Run the workflow in plan mode first:

```bash
gh workflow run tenant-ui-deploy.yml \
  -f target_environment=staging \
  -f tenant_id=liquisto \
  -f hostname=liquisto.condata.io \
  -f control_api_url=https://<staging-control-api-url> \
  -f apply_deploy=false \
  -f confirm_production=false
```

Expected result:

- Docker image builds from `deploy/streamlit-business-ui/Dockerfile`.
- Image archive artifact is uploaded.
- Deployment plan artifact states the fixed tenant ID and that no remote host
  was changed.

## Staging Deployment

Only run staging apply after the staging Control Plane and Runtime Plane are
available and the upstream authentication evidence exists:

```bash
gh workflow run tenant-ui-deploy.yml \
  -f target_environment=staging \
  -f tenant_id=liquisto \
  -f hostname=liquisto.condata.io \
  -f control_api_url=https://<staging-control-api-url> \
  -f upstream_auth_evidence_url=https://github.com/<owner>/<repo>/actions/runs/<run-id> \
  -f apply_deploy=true \
  -f confirm_production=false
```

The workflow validates the SCAS-managed Compose path, validates the SSH key,
uploads the image archive, writes a root-owned environment file on the target
host, writes the complete Compose file under `/opt`, starts only that Compose
file with the configured project and service name, runs the Streamlit health
check on `127.0.0.1:<local_health_port>` with a bounded 90-second readiness
wait, and uploads sanitized deployment evidence. The environment file includes
`SCAS_UI_TENANT_ID=liquisto`, so the deployed hostname cannot switch to another
tenant through UI state.

## Production Deployment

Production deploys require all staging and launch gates to pass first. Then run:

```bash
gh workflow run tenant-ui-deploy.yml \
  -f target_environment=prod \
  -f tenant_id=liquisto \
  -f hostname=liquisto.condata.io \
  -f control_api_url=https://<prod-control-api-url> \
  -f upstream_auth_evidence_url=https://github.com/<owner>/<repo>/actions/runs/<run-id> \
  -f apply_deploy=true \
  -f confirm_production=true
```

Do not use production apply when any of these are missing:

- Cloudflare DNS/TLS/proxy evidence for `liquisto.condata.io`; Worker route
  evidence is required only if the UI hostname is intentionally moved behind a
  Cloudflare Worker route.
- Approved upstream authentication/session evidence.
- Staging tenant launch gate evidence.
- Rollback/deprovisioning dry-run evidence.
- Owner-approved production release decision.

Latest production apply evidence:

| Date | GitHub run | Result | Evidence |
| --- | --- | --- | --- |
| 2026-06-17 22:56 Europe/Berlin | `27719099324` | passed | Applied `scas-streamlit-business-ui:655beba1faba6763120198857d1c8aef075d4921` to compose project `liquisto` using `/opt/liquisto/scas-streamlit-business-ui.override.yml`; previous image was `scas-streamlit-business-ui:916b7d87295d685c7ab4c2c8ffc3049297ed9d56`; post-deploy health check passed. |

## Rollback Behavior

During apply, the workflow records the currently running Compose service image
from Docker Compose labels before starting the new image. If the post-deploy
Streamlit health check fails, the SCAS-managed Compose file is changed back to
the previous image and the service is restarted.

Manual rollback uses the same override file:

```bash
ssh "$SCAS_PROD_HETZNER_USER@$SCAS_PROD_HETZNER_HOST"
docker compose \
  -p liquisto \
  -f /opt/liquisto/scas-streamlit-business-ui.override.yml \
  ps
```

Then set the SCAS-managed Compose image to the last-known-good image and run:

```bash
docker compose \
  -p liquisto \
  -f /opt/liquisto/scas-streamlit-business-ui.override.yml \
  up -d app
```

Do not delete the prior image or SCAS-managed Compose file until the production
release decision is closed and evidence has been retained. Legacy host `.env`
files are not deployment inputs for this workflow and may be removed by the
runtime owner after confirming no unrelated service depends on them.

## Launch Gate Mapping

This deployment path closes the repository-owned portion of
`Liquisto Tenant UI 06`. It supports but does not replace the launch gates:

- Launch 01: run the live tenant gate and attach the workflow evidence.
- Launch 02: verify Cloudflare DNS, TLS, hidden origin handling, and the
  selected routing path. The current UI path is Cloudflare-proxied
  Hetzner/Nginx/Streamlit with Worker route count `0`.
- Launch 03: bootstrap tenant owner/admin through
  `docs/runbooks/liquisto-tenant-admin-bootstrap.md`.
- Launch 04: keep real legal/contact/register data in the approved source of
  truth; public fixtures may contain only non-secret sentinel values.
- Launch 05: deploy and validate against staging first.
- Launch 06: run production gate and record owner release decision.
- Launch 07: dry-run rollback/deprovisioning through
  `docs/runbooks/liquisto-tenant-rollback-deprovisioning.md` before production
  readiness.

## Evidence Rules

Evidence may include workflow URLs, commit SHAs, image references, compose
paths, health-check results, and non-secret routing observations. Evidence must
not include private keys, bearer tokens, session JSON, raw runtime traces,
customer data, or confidential tenant records.
