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
- policy bundle and validators.

Tenant legal and contact metadata describes the company. It does not grant
runtime authority.

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

## Role Bundles

A role bundle is tenant-local. A role named `Researcher` in one tenant is a
different authority object from a role with the same display name in another
tenant.

Role bundles may include:

- capability grants, such as `research` or `tenant-admin`,
- data-source grants, such as read access to `demo-tenant-website`,
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

The runtime profile is invalid when:

- `tenant_context` is missing,
- `tenant_authority` is missing for a non-global tenant,
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
