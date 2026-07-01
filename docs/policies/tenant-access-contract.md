# Tenant Access Contract

## Purpose

This document defines the tenant access model for company-specific SCAS UIs.

The model is intentionally role-centered:

```text
User -> Tenant Membership -> Tenant Role Bundle -> Runtime Capabilities
```

Users must not receive direct assignments to individual skills, workflows, task
areas, tools, validators, policies, or data sources. Those grants are derived
from tenant-local roles.

## Tenant Registry

Each company tenant is described by a tenant registry entry that conforms to:

```text
schemas/tenant-registry.schema.json
```

The registry entry contains:

- stable `tenant_id` and `area_id`,
- legal, contact, commercial-register, and tax metadata,
- tenant hostnames,
- admin model,
- tenant-local memory and knowledge scopes,
- tenant-owned data sources,
- tenant-local role bundles,
- optional tenant UI profile metadata,
- policy bundle and validators.

Tenant legal and contact metadata describes the company. It does not grant
runtime authority.

Tenant UI profile metadata defines the tenant-specific CRM web app surface. A
tenant UI profile that exists must declare the active
`sota-2026-tenant-crm` experience standard, tenant-owned brand assets, theme
tokens, navigation area IDs, command-center surfaces, tenant terminology,
SCAS skill-package bindings, and workspace areas such as `research` or
`tenant-admin`.

UI profile metadata is display, routing, and product-configuration metadata
only. Visibility must be derived from tenant-local role capabilities. Skill
package bindings advertise which tenant-specific CRM workflows may be surfaced
to the user, but they do not grant capabilities, data-source access, skills,
tools, policies, validators, memory scopes, or knowledge scopes. The Composer
must still select executable modules through registry discovery, scoring,
policy filtering, dependency graph validation, and immutable runtime profile
validation.

Tenant asset handling is fail-closed. A tenant may use only assets declared in
its own `ui_profile.brand_assets`. Missing assets may degrade to a neutral
unbranded state, but they must not fall back to another tenant's logo, favicon,
app icon, colors, or copy.

Tenant-facing UIs must present only product capabilities, goals, inputs, and
outputs. Visible copy must not expose SCAS architecture terms, tenant model
details, runtime profile composition, validator names, policy gates, tool
selection, isolation mechanics, or the existence of other tenants. Internal
tenant isolation remains mandatory, but it is not a user-facing product concept.

Tenant UIs that are reachable outside local development must run in an
authenticated session mode. The UI may use repository fixtures only for local
contract verification. In authenticated mode, visible areas and admin access
derive from server-owned tenant session context containing principal,
membership, tenant, and role IDs. Local role override variables such as
`SCAS_UI_ROLE_IDS` are not authority in authenticated mode.

The Cloudflare Control Plane persists the runtime-relevant tenant registry
projection in D1. The storage contract lives in:

```text
schemas/cloudflare-control-plane.schema.json
migrations/cloudflare/d1/0003_tenant_control_plane.sql
```

The D1 projection stores tenants, hostnames, tenant memberships, tenant role
bundles, tenant data sources, role capability grants, and role data-source
grants as separate records. Legal and contact fields are stored for tenant
administration and audit context only; runtime access still comes exclusively
from membership and role-derived grants.

## Hostname Authority

Tenant selection starts with the requested hostname. A configured hostname maps
to exactly one tenant authority record before task analysis or runtime profile
assembly may grant any tenant-local access.

Hostname resolution is fail-closed:

- hostnames are normalized to lowercase host names without scheme, path, port,
  or trailing dot before lookup,
- unknown hostnames are denied,
- disabled or archived tenants are denied,
- duplicate hostname configuration across tenants is invalid,
- prompt text, client UI state, and request body tenant IDs cannot override the
  tenant selected by the hostname.

The resolver returns only tenant authority metadata needed for the next control
path step: tenant ID, area ID, normalized hostname, hostname purpose, tenant
status, expected origin, and Cloudflare proxy expectation. Session authority
must still prove that the authenticated principal belongs to the resolved
tenant before runtime profile assembly proceeds.

## Admin Surface

The tenant admin UI exposes only these first-class administration areas:

```text
/admin/users
/admin/roles
/admin/settings
```

`/admin/roles` is the authority surface for operational access. Tenant admins
assign users to roles; roles contain capability and data-source grants.

The product must not expose normal tenant-admin pages for assigning individual
skills, workflows, validators, policies, or data sources directly to users.

The Control API exposes the tenant admin context and first write-capable
administration contracts at:

```text
GET /tenant-admin/tenants/{tenant_id}
POST /tenant-admin/tenants/{tenant_id}/roles
POST /tenant-admin/tenants/{tenant_id}/memberships
POST /tenant-admin/tenants/{tenant_id}/data-sources
```

All routes require tenant-admin scoped bearer authorization and the
`x-scas-tenant-hostname` header. The read route must return only D1-derived
tenant admin data for the resolved hostname: users, role bundles, role grants,
tenant-owned data sources, tenant settings, and the fixed admin route list
above. Missing or mismatched hostname proof fails closed.

Write routes are deliberately narrow:

- `/roles` creates tenant-local role bundles with capability grants,
  data-source grants, and derived runtime module references.
- `/memberships` creates or updates tenant memberships using role IDs that are
  tenant-local and assignable to users.
- `/data-sources` registers tenant-owned data sources with bounded access modes
  and sensitivity.

Write routes must reject foreign tenant data-source IDs, non-assignable or
foreign role IDs, invalid access modes, and malformed identifiers. Every
successful write emits a bounded `audit_events` row without secrets, raw
provider tokens, raw runtime traces, or confidential customer data.

## Role Bundles

A role bundle is tenant-local. A role named `Researcher` in one tenant is a
different authority object from a role with the same display name in another
tenant.

Role bundles may include:

- capability grants, such as `research` or `tenant-admin`,
- data-source grants, such as read access to `tenant-under-test-website`,
- derived runtime modules:
  - skills,
  - workflows,
  - tools,
  - policies,
  - validators.

The derived runtime modules are platform configuration. Tenant users receive
only roles.

## Data Sources

A data source is a concrete system, storage location, or bounded dataset that
the runtime may read or write when a selected role permits it. Examples include
GitHub repositories, Notion page trees, Google Drive folders, SharePoint sites,
HubSpot accounts, websites, databases, and other tenant-owned systems.

Every data source belongs to exactly one tenant. A source without explicit
tenant ownership is unavailable. A user receives access to data sources only
through tenant roles. D1 enforces tenant-local grants with composite foreign
keys: a role data-source grant is invalid when the role bundle and data source
do not share the same `tenant_id`.

Runtime code must use the tenant data-source connector rather than direct source
lookups. The connector resolves sources only from the sealed runtime
`tenant_authority`, requires the source to be listed in
`tenant_context.allowed_role_data_sources`, checks selected role grants, and
fails closed for global profiles, cross-tenant sources, unavailable sources, or
ungranted access modes.

Production tenant customer and operational business databases are Hetzner
PostgreSQL databases, one database per tenant. The Control Plane may register
those databases as tenant-owned data sources and may grant access through
tenant-local roles, but Cloudflare D1 remains an authority and metadata store
only. It must not become the production store for tenant customer records,
customer cases, order workflows, email tracking, calendar references, or
aftersales state.

## Runtime Profile Context

Every runtime profile includes `tenant_context` and must conform to:

```text
schemas/runtime-profile.schema.json
```

`tenant_context` records:

- the active tenant and area,
- the hostname and membership when available,
- selected tenant role IDs,
- proof that direct user grants are disabled,
- role-derived data-source and capability grants.

For tenant-scoped profiles, the Composer must also receive a
`tenant_authority` snapshot in the Control Plane composition response. That
snapshot is validated before profile emission and includes:

- tenant status,
- active membership for the authenticated principal,
- tenant-local role bundles,
- tenant-owned data sources,
- role-derived capability and data-source grants,
- allowed tenant knowledge, data, and memory scopes,
- proof that direct user grants are disabled.

The Control API builds `tenant_authority` only from D1 tenant tables and the
request `tenant_context`. Prompt text, client-supplied role claims, and direct
user grants are not authority sources.

The Composer seals the validated `tenant_authority` snapshot into the emitted
runtime profile. Global profiles set `tenant_authority = null`. Tenant-scoped
profiles must carry the snapshot so the Runtime Profile Enforcer can validate
the immutable profile independently before execution starts.

Runtime validation must confirm that:

- the profile tenant and area match the sealed authority,
- the active membership matches the profile membership and principal,
- selected role IDs are present in the active membership,
- selected skills, tools, policies, validators, knowledge scopes, data scopes,
  and memory scopes are reachable through tenant role bundles,
- role capability and data-source grants are role-derived,
- no direct user grants are enabled in either `tenant_context` or
  `tenant_authority`.

The runtime profile is invalid when:

- `tenant_context` is missing,
- `tenant_authority` is missing for a non-global tenant,
- `tenant_authority` is present for the global tenant,
- direct user grants are enabled,
- scopes from more than one tenant or area are present,
- selected tools, skills, data sources, memory scopes, or knowledge scopes are
  not reachable through tenant roles,
- the user is not a member of the tenant,
- the tenant is disabled or archived,
- any referenced tenant scope is unknown.

## Isolation Rules

Tenant isolation is fail-closed:

- unknown tenants are denied,
- unknown hostnames are denied,
- unknown scopes are denied,
- mixed-tenant profiles are denied,
- mixed-area profiles are denied,
- cross-tenant and cross-area access are not supported,
- prompt text cannot override tenant identity or role grants.

Every enforcement layer must use the same authority chain:

```text
Tenant Registry
-> Tenant Membership
-> Tenant Role Bundle
-> Control Plane tenant_authority
-> Runtime Profile
-> Validator
-> Tool Gateway / Retrieval / Memory Gate
```

The UI may hide unavailable actions, but server-side validation remains the
authority.
