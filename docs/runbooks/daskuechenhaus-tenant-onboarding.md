# Daskuechenhaus Tenant Onboarding

## Tenant Identity

- Tenant ID: `daskuechenhaus`
- Area ID: `daskuechenhaus`
- Display name: `das küchenhaus`
- Legal name: `das küchenhaus ralph schober GmbH`
- Registry fixture:
  `examples/tenants/daskuechenhaus.json`
- Status: `setup`

The tenant is not ready for production traffic until isolated UI routing,
admin bootstrap, and isolation evidence have passed.

## Public Source Verification

The supplied legal and contact data was checked against the public website:

- `https://www.schober-daskuechenhaus.de/kontakt/impressum.html`
- `https://www.schober-daskuechenhaus.de/kontakt/kontakt.html`

Verified public details:

- Address: `Blumenstraße 17`, `73728 Esslingen`, Germany
- Phone: `0711/36550747`
- Fax: `0711/36550746`
- Email: `info@schober-daskuechenhaus.de`
- VAT ID: `DE265715198`
- Commercial register: `Amtsgericht Stuttgart`, `HR 730338`
- Managing director: `Ralph Schober`

## Initial Registry Scope

The initial tenant registry entry is deliberately minimal:

- website data source: `daskuechenhaus-website`
- access mode: `read`
- data sensitivity: `public`
- default locale: `de-DE`
- tenant memory: `brain-area-daskuechenhaus`
- tenant knowledge scope: `knowledge-daskuechenhaus`
- shared memory promotion: disabled

No cross-tenant or cross-area access is configured.

## Customer Data Storage

Daskuechenhaus customer cases, customer records, order workflow state, email
communication tracking, calendar references, and aftersales state are
production customer data. They must live in the Hetzner PostgreSQL tenant
database `tenant_daskuechenhaus`.

This storage rule is about the Daskuechenhaus operational/customer database
only. It does not change SCAS memory handling.

Cloudflare D1 remains the Control Plane authority store for tenant metadata,
hostnames, memberships, roles, data-source registrations, scope bindings,
policy bindings, and bounded audit metadata. It is not the production store for
Daskuechenhaus customer cases.

Any experimental Daskuechenhaus customer-case data previously created in
Cloudflare D1 is discarded as a source system. The production customer-case
product starts with a new PostgreSQL schema; no D1-to-Hetzner customer-case
migration is planned.

Provision the empty tenant database on `scas-runtime-prod` with:

```bash
SCAS_TENANT_DB=tenant_daskuechenhaus \
SCAS_TENANT_DB_OWNER=tenant_daskuechenhaus_app \
scripts/hetzner/provision_tenant_database.sh
```

This step creates only the database, owner/application role, and empty
`app` and `audit` schemas. Apply the tenant migrations in
`migrations/hetzner/tenants/daskuechenhaus/` afterwards.

The customer database foundation is versioned in
`0005_customer_database.sql`. It keeps `app.customer_cases` as the
customer-folder/case anchor and adds normalized customer tables:

- `app.customers` for customer master data, tax/invoice flags, primary contact
  channels, ownership, and tags.
- `app.customer_addresses` for billing, delivery, installation, and other
  addresses.
- `app.customer_contacts` for additional contacts under a customer.
- `app.customer_case_status_phases` for phases 1-11 inside the customer
  folder, from Anfrage through Abgeschlossen.
- `app.customer_case_participants` for the customer/contact roles on each case.
- `app.customer_case_project_profiles` for kitchen-project details such as
  budget, room type, measurement date, and target installation date.
- `app.customer_case_notes`, `app.customer_case_documents`, and
  `app.customer_case_audit_events` for the documented customer file.
- `0010_customer_case_document_metadata.sql` extends
  `app.customer_case_documents` for the guided Vorgangsregister document
  workflow: register assignment, category, status, title, note, version label,
  current-version marker, and archival metadata before binary file upload is
  enabled.
- `app.customer_file_sections` and `app.customer_case_sections` for flexible
  customer-file desktop and case-folder sections that will later be promoted to
  stricter tables where the workflow becomes stable.

Customer names and customer emails are deliberately not unique. The system must
allow different customers with the same name and must also allow operational
duplicates where one real person appears in different business roles. Only a
non-empty `customer_number`, when present, is unique.

## Customer Database Reset

Use `.github/workflows/es-daskuechenhaus-customer-database-reset.yml` only for
an explicitly confirmed productive reset of Daskuechenhaus customer data. The
manual workflow requires `apply_reset=true`, `confirm_production=true`, and the
exact confirmation text `Ja, produktive DKH-Kundendatenbank leeren.`.

The reset deletes customer records, customer cases/files, customer contacts and
addresses, case sections, case notes/documents/audit rows, case-linked tasks,
appointments, communication events, email case links, and case assignment
suggestions. It preserves users, roles, permissions, login/access configuration,
task statuses, customer case status phases, mail account configuration, app
code, and deployment configuration.

The workflow writes count-only evidence before and after the reset and verifies
that `/customers/state` returns empty `customers` and `customer_cases` arrays.

## UI Branding

The tenant UI uses Daskuechenhaus-owned branding only:

- logo: `assets/images/daskuechenhaus/logo_daskuechenhaus.png`
- background and surface: `#fff`
- primary text: `#111`
- secondary text: `#333`
- accent and border: `#76b726`

`schober-daskuechenhaus.de` remains a public source and contact domain. It is
not used as the SCAS tenant slug, area ID, hostname, or asset namespace.

## Admin Bootstrap

The registry keeps `admin_model.initial_owner = null` until a concrete SCAS
user identity and owner email are approved.

Default roles are present but not assigned:

- `daskuechenhaus-owner`
- `daskuechenhaus-admin`
- `daskuechenhaus-researcher`

Before activation, bootstrap must define:

1. the initial tenant owner identity,
2. optional additional tenant admin identities,
3. tenant-local membership IDs,
4. admin route access checks,
5. audit evidence for the bootstrap action.

Admin rights remain tenant-local. Email domain knowledge or public website
knowledge must not grant access. The `daskuechenhaus-admin` role has
tenant-admin capability only and does not grant research, data-source, or
filesystem access.

The non-secret bootstrap contract is documented in
`docs/runbooks/daskuechenhaus-tenant-admin-bootstrap.md`. The required
tenant-specific owner principal secrets are:

```text
SCAS_STAGING_DASKUECHENHAUS_OWNER_PRINCIPAL_ID
SCAS_STAGING_DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPAL_IDS_JSON
SCAS_PROD_DASKUECHENHAUS_OWNER_PRINCIPAL_ID
SCAS_PROD_DASKUECHENHAUS_ADDITIONAL_ADMIN_PRINCIPAL_IDS_JSON
```

## DNS And Routing Evidence

Public DNS and Cloudflare evidence were observed on 2026-06-18:

```powershell
Resolve-DnsName daskuechenhaus.condata.io -Type A
Resolve-DnsName daskuechenhaus.condata.io -Type A -Server 1.1.1.1
Resolve-DnsName daskuechenhaus.condata.io -Type A -Server 8.8.8.8
```

Observed A records:

| Hostname | TTL | A record |
| --- | ---: | --- |
| `daskuechenhaus.condata.io` | 300 | `104.21.36.65` |
| `daskuechenhaus.condata.io` | 300 | `172.67.186.195` |

The tenant fixture records `daskuechenhaus.condata.io` as the setup
`primary-ui` hostname with `expected_origin = "178.105.62.169"` and
`cloudflare_proxy_expected = true`.

Authoritative Cloudflare evidence passed with `require_worker_route=false`:

| Environment | GitHub run | Result | Worker route required |
| --- | --- | --- | --- |
| staging | `27763474317` | passed | `false` |
| prod | `27763474282` | passed | `false` |

Runtime inventory run `27763766446` showed a blocking pre-fix condition:
`daskuechenhaus.condata.io` fell through to an existing Streamlit runtime
because no dedicated Daskuechenhaus Nginx server block or UI binding was
present. Before activation, the tenant must run through a dedicated
Daskuechenhaus UI binding or equivalent server-side hostname resolution that
fails closed for mismatched hosts.

The routing fix was deployed after PR #139. Runtime inventory run `27766020716`
observed `daskuechenhaus-app-1` bound separately on `127.0.0.1:8502` and an
Nginx server block for `daskuechenhaus.condata.io` proxying to that port. A
live UI check on 2026-06-18 showed Daskuechenhaus-specific tenant content at
`https://daskuechenhaus.condata.io/` while `https://liquisto.cloud/`
continued to serve Liquisto content.

## Isolation Evidence

Static tenant isolation is covered by focused tests:

```powershell
python -m pytest tests/test_contract_schema_examples.py tests/test_tenant_hostname_resolution.py tests/test_tenant_isolation_matrix.py tests/test_streamlit_business_ui.py
```

The checks verify that:

- the tenant fixture matches the tenant registry schema,
- `daskuechenhaus.condata.io` resolves to exactly one setup tenant authority,
- seeded data-source and role grants do not cross tenant boundaries,
- Daskuechenhaus website and knowledge scopes are distinct from existing and demo
  tenant scopes,
- the tenant UI shell loads Daskuechenhaus tenant metadata from the registry.

This is static setup evidence only. Runtime readiness still requires live
tenant path execution and an isolation audit before marking the tenant active.

## Blocking Follow-Ups

The following items must be completed before changing the tenant status from
`setup` to `active`:

1. Initial tenant owner bootstrap with tenant-local membership and audit event.
2. Tenant isolation audit across UI, Control API, Composer, runtime profile,
   data-source grants, knowledge retrieval, memory scope, and admin routes.
3. Live tenant path gate against the selected environment.
