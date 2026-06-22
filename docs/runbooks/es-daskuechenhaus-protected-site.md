# es-daskuechenhaus.de Next.js CRM Site

`es-daskuechenhaus.de` and `www.es-daskuechenhaus.de` remain the protected
production entrypoints for the DKH CRM. The legacy Cloudflare Worker UI has been
removed. The protected site now routes through Cloudflare Access to the
Next.js application in `apps/dkh-crm/`.

## Target Path

```text
Browser
  -> Cloudflare DNS proxy
  -> Cloudflare Access self-hosted application
  -> Hetzner Nginx
  -> apps/dkh-crm .next/standalone/server.js
  -> Hetzner DKH Admin API
  -> PostgreSQL tenant schema
```

## Required Cloudflare State

- DNS keeps `es-daskuechenhaus.de` and `www.es-daskuechenhaus.de` proxied.
- Cloudflare Access protects both hostnames as the same CRM entrypoint.
- No Cloudflare Worker route should exist for either hostname.
- The Access application must pass the authenticated user email to the origin
  through the Access JWT/header flow.

## Required Hetzner State

- Build the app from `apps/dkh-crm/`:

```powershell
npm --prefix apps/dkh-crm install
npm --prefix apps/dkh-crm run build
```

- Run the standalone server from `apps/dkh-crm/.next/standalone/server.js`.
- Configure Nginx for both hostnames to proxy to the local Next.js port.
- Set runtime environment values outside Git:
  - `DKH_ADMIN_API_BASE_URL`
  - `DKH_ADMIN_API_TOKEN`
  - `CF_ACCESS_TEAM_DOMAIN` and `CF_ACCESS_AUD` when JWT validation is enforced.
    If Cloudflare Access uses separate applications for the apex and `www`
    hostnames, include both audience tags in `CF_ACCESS_AUD` separated by
    whitespace or commas. Prefer a single Access application covering both
    hostnames when possible.

## Validation

```powershell
npm run dkh-crm:check
Resolve-DnsName es-daskuechenhaus.de -Type A -Server 1.1.1.1
Resolve-DnsName www.es-daskuechenhaus.de -Type A -Server 1.1.1.1
```

Then verify in Cloudflare:

- anonymous access redirects to Cloudflare Access,
- authenticated access lands on the Next.js CRM,
- `es-daskuechenhaus.de` and `www.es-daskuechenhaus.de` do not route to a
  Worker,
- Access logs show the expected authenticated email and application audience.

## Rollback

Rollback is a Hetzner/Nginx or Next.js process rollback. Do not recreate the
legacy Worker UI. If Access or DNS is misconfigured, restore the previous
Cloudflare Access application policy and DNS record while keeping the origin on
Hetzner.
