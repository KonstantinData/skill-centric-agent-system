# Schober Tenant Onboarding

## Tenant Identity

- Tenant ID: `schober-daskuechenhaus`
- Area ID: `schober-daskuechenhaus`
- Display name: `das küchenhaus ralph schober`
- Legal name: `das küchenhaus ralph schober GmbH`
- Registry fixture:
  `examples/tenants/schober-daskuechenhaus.json`
- Status: `setup`

The tenant is not ready for production traffic until DNS/routing, admin
bootstrap, and isolation evidence have passed.

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

- website data source: `schober-daskuechenhaus-website`
- access mode: `read`
- data sensitivity: `public`
- default locale: `de-DE`
- tenant memory: `brain-area-schober-daskuechenhaus`
- tenant knowledge scope: `knowledge-schober-daskuechenhaus`
- shared memory promotion: disabled

No cross-tenant or cross-area access is configured.

## Admin Bootstrap

The registry keeps `admin_model.initial_owner = null` until a concrete SCAS
user identity and owner email are approved.

Default roles are present but not assigned:

- `schober-daskuechenhaus-owner`
- `schober-daskuechenhaus-researcher`

Before activation, bootstrap must define:

1. the initial tenant owner identity,
2. tenant-local membership IDs,
3. admin route access checks,
4. audit evidence for the bootstrap action.

Admin rights remain tenant-local. Email domain knowledge or public website
knowledge must not grant access.

## DNS And Routing Evidence

Public DNS was observed on 2026-06-18:

```powershell
Resolve-DnsName schober-daskuechenhaus.de -Type A
Resolve-DnsName www.schober-daskuechenhaus.de -Type A
```

Observed A records:

| Hostname | TTL | A record |
| --- | ---: | --- |
| `schober-daskuechenhaus.de` | 1800 | `188.40.16.199` |
| `www.schober-daskuechenhaus.de` | 1620 | `188.40.16.199` |

The tenant fixture records `schober-daskuechenhaus.de` as the setup
`primary-ui` hostname with `expected_origin = "188.40.16.199"` and
`cloudflare_proxy_expected = false`.

This records the current public website routing. It does not prove that the
hostname is routed to SCAS UI infrastructure. Before activation, decide whether
SCAS should use the existing customer domain, a delegated subdomain, or a
separate `condata.io` tenant hostname, then re-run DNS/routing evidence.

## Isolation Evidence

Static tenant isolation is covered by focused tests:

```powershell
python -m pytest tests/test_contract_schema_examples.py tests/test_tenant_hostname_resolution.py tests/test_tenant_isolation_matrix.py tests/test_streamlit_business_ui.py
```

The checks verify that:

- the tenant fixture matches the tenant registry schema,
- `schober-daskuechenhaus.de` resolves to exactly one setup tenant authority,
- seeded data-source and role grants do not cross tenant boundaries,
- Schober website and knowledge scopes are distinct from existing and demo
  tenant scopes,
- the tenant UI shell loads Schober tenant metadata from the registry.

This is static setup evidence only. Runtime readiness still requires live
tenant path execution and an isolation audit before marking the tenant active.

## Blocking Follow-Ups

The following items must be completed before changing the tenant status from
`setup` to `active`:

1. DNS/routing decision and evidence for the chosen SCAS tenant hostname.
2. Initial tenant owner bootstrap with tenant-local membership and audit event.
3. Tenant isolation audit across UI, Control API, Composer, runtime profile,
   data-source grants, knowledge retrieval, memory scope, and admin routes.
4. Live tenant path gate against the selected environment.
