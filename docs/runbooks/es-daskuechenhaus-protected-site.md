# es-daskuechenhaus.de Next.js CRM Site

`es-daskuechenhaus.de` and `www.es-daskuechenhaus.de` remain the protected
production entrypoints for the DKH CRM. The legacy Cloudflare Worker UI has been
removed. The protected site now routes through Cloudflare Access to the
Next.js application in `apps/dkh-crm/`.

## Target Path

```text
Browser
  -> Cloudflare DNS proxy
  -> Cloudflare Access self-hosted application for the requested hostname
  -> Hetzner Nginx
  -> apps/dkh-crm .next/standalone/server.js
  -> Hetzner DKH Admin API
  -> PostgreSQL tenant schema
```

## Required Cloudflare State

- DNS keeps `es-daskuechenhaus.de` and `www.es-daskuechenhaus.de` proxied.
- Cloudflare Access protects both hostnames through separate self-hosted Access
  applications. Keep one application per hostname so the Access login callback
  host matches the hostname that started authentication:
  - `es-daskuechenhaus.de`
  - `www.es-daskuechenhaus.de`
- Access authorization is explicit user allow-listing. For the three-person
  portal setup, use one `Allow` policy with `Emails` selectors for the approved
  users. The initial approved user is:
  - `k.milonas@schober-daskuechenhaus.de`
- Cloudflare Access uses e-mail one-time PIN for authentication. Independent
  MFA is explicitly disabled for the DKH Access allow policies so users are not
  prompted for an authenticator application or another second factor.
- The Access application name, Zero Trust organization display name, login
  header/footer text, and identity-denied message are DKH-specific. Keep
  automatic identity-provider redirects disabled so users land on the Access
  login choice page instead of being bounced through an IdP loop.
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
    Because Cloudflare Access uses separate applications for the apex and `www`
    hostnames, include both audience tags in `CF_ACCESS_AUD` separated by
    whitespace or commas.

## Customer Document Storage

Customer documents uploaded through the `Dokumente` card are stored in Hetzner
Object Storage and indexed in the tenant PostgreSQL database. PostgreSQL remains
the access-control and metadata source of truth; object storage stores only the
file bytes.

Production uses:

- bucket: `dkh-crm-documents`
- endpoint: `https://fsn1.your-objectstorage.com`
- region: `fsn1`
- runtime env file: `/etc/daskuechenhaus/object-storage.env`

The Admin API deploy workflow writes the object-storage env file from the
GitHub environment secrets `DKH_OBJECT_STORAGE_ACCESS_KEY_ID` and
`DKH_OBJECT_STORAGE_SECRET_ACCESS_KEY`. Do not commit those values. The same
workflow applies `0011_customer_document_object_storage.sql`, which adds the
document storage backend, bucket, object key, and SHA-256 metadata fields.

The CRM proxy must forward `multipart/form-data` uploads unchanged. The Admin
API validates supported document file types, writes files to object storage,
stores object metadata in `app.customer_case_documents`, serves authorized
downloads through `/customers/cases/{case_id}/documents/{document_id}/download`,
and includes object-storage files in customer-file ZIP exports.

## Access Configuration Workflow

Manage the DKH CRM Cloudflare Access app through:

```powershell
gh workflow run "es-daskuechenhaus.de Access Configuration" `
  --repo KonstantinData/skill-centric-agent-system `
  --ref main `
  -f apply_changes=true `
  -f confirm_production=true `
  -f "hostnames=es-daskuechenhaus.de www.es-daskuechenhaus.de" `
  -f "allowed_emails=k.milonas@schober-daskuechenhaus.de" `
  -f primary_hostname=es-daskuechenhaus.de `
  -f delete_duplicate_apps=true `
  -f reset_user_auth_state=false `
  -f reset_user_email=""
```

When the other two portal users are approved, add them to the
`allowed_emails` input as a whitespace-separated list. Do not add broad domain
allow rules unless all mailboxes in that domain should receive CRM access.

To revoke a DKH user's active Cloudflare Access sessions and remove their active
Access user/seat state, run the same workflow with `reset_user_auth_state=true`
and `reset_user_email` set to that user's approved e-mail address. This does
not re-enable MFA and is only a session/user-state reset.

```powershell
gh workflow run "es-daskuechenhaus.de Access Configuration" `
  --repo KonstantinData/skill-centric-agent-system `
  --ref main `
  -f apply_changes=true `
  -f confirm_production=true `
  -f "hostnames=es-daskuechenhaus.de www.es-daskuechenhaus.de" `
  -f "allowed_emails=k.milonas@schober-daskuechenhaus.de" `
  -f primary_hostname=es-daskuechenhaus.de `
  -f delete_duplicate_apps=true `
  -f reset_user_auth_state=true `
  -f reset_user_email=k.milonas@schober-daskuechenhaus.de
```

Cloudflare's Access login page header/footer and organization name are global
Zero Trust settings. The repository-owned workflow keeps the DKH organization
name, login header/footer text, per-hostname application names, Access allow
policy, MFA-disabled policy state, deny message, cookie scope, and host-specific
Access app split reproducible. Do not leave legacy labels such as unrelated
chatbot names on the Access login page.

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

For document storage, also verify:

- `GET /health` on the Admin API reports `object_storage.configured = true`,
- a document upload in a customer case creates a row with
  `storage_backend = 'object_storage'` and an `object_storage_key`,
- the document download link returns the uploaded file,
- the customer-file ZIP export contains the uploaded document.

## Rollback

Rollback is a Hetzner/Nginx or Next.js process rollback. Do not recreate the
legacy Worker UI. If Access or DNS is misconfigured, restore the previous
Cloudflare Access application policy and DNS record while keeping the origin on
Hetzner.
