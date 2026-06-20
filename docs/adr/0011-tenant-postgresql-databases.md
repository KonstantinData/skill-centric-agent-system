# ADR-0011: Tenant PostgreSQL Databases On Hetzner

## Status

Accepted

## Date

2026-06-19

## Context

SCAS separates Cloudflare Control Plane data from Hetzner Runtime Plane data.
The existing Control Plane D1 database is suitable for tenant authority,
registry metadata, role grants, scope bindings, knowledge metadata, memory
metadata, and bounded audit metadata.

Tenant operational data has different requirements. Customer records, customer
cases, orders, aftersales workflows, email tracking, calendar references, and
runtime business state are tenant-owned business data. They need tenant-local
backup, restore, retention, access control, and future migration paths that are
independent from Cloudflare D1 control metadata.

Daskuechenhaus previously had an experimental Cloudflare D1 customer-case
database path. That path is not the production target.

## Decision

Every production tenant receives its own PostgreSQL database on the Hetzner
runtime server.

Initial production tenant databases are:

- `tenant_condata`
- `tenant_mein_kuechenexperte`
- `tenant_daskuechenhaus`
- `tenant_kinderhaus`
- `tenant_elternkindwelt`

Cloudflare D1 remains the Control Plane database for metadata and authority.
It must not be used as the production store for Daskuechenhaus customer cases
or other tenant customer data.

The experimental Daskuechenhaus Cloudflare D1 customer-case database is
discarded as a source system. Its data is not migrated to Hetzner. The
Daskuechenhaus customer-case product starts with a new PostgreSQL schema in
`tenant_daskuechenhaus`.

This decision is only about tenant operational and customer databases. It does
not change the existing memory architecture, memory feedback loop, knowledge
storage, or Cloudflare memory resources.

## Consequences

- Tenant customer and business data can be backed up, restored, migrated, and
  permissioned independently per tenant.
- Cloudflare D1 stays small and authority-focused instead of becoming a mixed
  control and customer data store.
- Daskuechenhaus customer-case schema design is not constrained by the
  experimental D1 schema.
- Tenant database provisioning, migrations, backup policy, application roles,
  and connection routing need an explicit Hetzner runbook before production
  write paths are enabled.
- Cross-tenant queries across customer data are not supported by default. Any
  future reporting layer must aggregate through explicit, policy-approved
  export or analytics flows.

## Follow-Up

- Add Hetzner tenant database provisioning scripts and runbook steps.
- Define PostgreSQL role and connection naming conventions for tenant
  databases.
- Create the initial `tenant_daskuechenhaus` customer-case schema from the
  German product model.
- Update application data access so Daskuechenhaus customer cases read and
  write only from the tenant PostgreSQL database.
- Keep Cloudflare D1 migrations limited to Control Plane metadata.
