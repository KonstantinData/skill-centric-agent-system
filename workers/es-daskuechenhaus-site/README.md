# es-daskuechenhaus.de protected site

Cloudflare Worker serving the internal `es-daskuechenhaus.de` website.

The site is intentionally not designed for public anonymous access. Production
deployment must be paired with a Cloudflare Access self-hosted application and
an Allow policy scoped to explicit Daskuechenhaus operators.

Local checks:

```powershell
npm run dkh-site:typecheck
npm run dkh-site:check
```
