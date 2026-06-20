# es-daskuechenhaus.de Protected Site

This runbook describes the protected Cloudflare Worker site for
`es-daskuechenhaus.de` and `www.es-daskuechenhaus.de`.

## Security Model

- `es-daskuechenhaus.de` and `www.es-daskuechenhaus.de` are not public websites.
- Cloudflare Access must protect the hostname before the Worker is deployed.
- The Access application uses an allow policy for explicit email identities.
- The deploy workflow refuses production mutation when no allowed email is
  provided.
- The deploy workflow performs an anonymous HTTP check after deploy and fails if
  the site returns `200` without Access.

## Required GitHub Secrets

The workflow reads these repository or environment secrets:

- `DKH_CLOUDFLARE_ACCOUNT_ID`
- `DKH_CLOUDFLARE_ZONE_ID`
- `DKH_CLOUDFLARE_API_TOKEN`

The token must be scoped to the `es-daskuechenhaus.de` zone and must allow
Cloudflare Access app/policy management, DNS record management, and Worker
deployment for the account.

## Local Checks

Run the focused checks before creating a pull request:

```powershell
npm run dkh-site:typecheck
npm run dkh-site:check
python -m pytest tests/test_github_actions_workflows.py tests/test_cloudflare_control_api_scaffold.py
```

## Plan-Only Workflow Run

Use the manual workflow with `apply_deploy=false` to validate secrets and build
the Worker without mutating Cloudflare.

Required input:

- `allowed_emails`: comma-separated list of users who may access the site after
  production apply.

## Production Apply

Only run with production mutation after the allowed user list has been reviewed:

- `allowed_emails`: one or more allowed identities
- `apply_deploy`: `true`
- `confirm_production`: `true`

The workflow configures Cloudflare Access and DNS for both hostnames first,
deploys the Worker second, and then verifies that anonymous access is blocked
on both hostnames.

## Rollback

If the Worker deployment must be removed, delete the Worker route or Worker
deployment in Cloudflare. Keep the Access application in place until the route
is verified as unreachable.
