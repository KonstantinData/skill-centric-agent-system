# DKH CRM

Next.js CRM workspace for `es-daskuechenhaus.de`.

The app is the current CRM UI for Das Kuechenhaus. It runs behind Cloudflare
Access in production and proxies CRM reads/writes to the existing Hetzner
runtime API.

## Local Development

```powershell
npm install
npm run dev -- -p 3001 -H 127.0.0.1
```

Open `http://127.0.0.1:3001/`.

Local development accepts the Cloudflare Access email headers when present, but
does not require them. Production requests without a resolved user email return
`401`.

## Required Environment

```env
DKH_ADMIN_API_BASE_URL=https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api
DKH_ADMIN_API_TOKEN=<secret>
```

For production JWT validation, set both Cloudflare Access variables:

```env
CF_ACCESS_TEAM_DOMAIN=<team>.cloudflareaccess.com
CF_ACCESS_AUD=<application-audience-tag>
```

When these variables are present in production, the middleware verifies the
`cf-access-jwt-assertion` audience and issuer before trusting the user email.
`CF_ACCESS_AUD` may contain multiple audience tags separated by spaces, commas,
or newlines. Configure all Cloudflare Access applications that can front the
CRM hostnames, for example both the apex and `www` applications if Cloudflare
keeps them separate.

## Build

Stop any running standalone server before building on Windows. A running
`.next/standalone/server.js` process can keep `.next` files locked and make
`next build` appear to hang.

```powershell
npm run build
```

The build uses `output: "standalone"` and then copies `public/` and
`.next/static/` into `.next/standalone/` via
`scripts/copy-standalone-assets.mjs`.

## Customer Page Behavior

The `/kunden` page follows a search-first duplicate-prevention flow. The
customer creation form is hidden on initial page load, remains hidden while the
search has matches or is unavailable, and is shown only after the customer
search returns no matches for a query with at least three characters.

The customer quick-access card is labeled `Zuletzt verwendet` and shows the
five most recently updated customer records by `updated_at`. It is separate from
any Stammkunden/customer-master-data surface.

## Legacy Route Compatibility

Legacy `.php` entrypoints redirect to the new App Router pages with temporary
redirects during cutover:

- `/index.php` and `/uebersicht.php` -> `/`
- `/termine.php` -> `/termine`
- `/aufgaben.php` -> `/aufgaben`
- `/emails.php` -> `/emails`
- `/kunden.php` -> `/kunden`
- `/vorgaenge.php` -> `/vorgaenge`
- `/admin.php` -> `/admin`
