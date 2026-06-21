# SCAS CRM Skill Pack Contract

## Purpose

CRM skill packs bind tenant CRM UI entry points to SCAS-controlled task
support. They are product contracts, not runtime grants.

The tenant UI may show a skill-pack entry point in search, quick actions,
notifications, saved views, or SCAS action surfaces. The UI binding must never
grant tools, data scopes, memory scopes, knowledge scopes, policies, validators,
or execution authority by itself.

## Required Control Path

Every CRM skill-pack execution must follow the normal SCAS composition path:

```text
task analysis
-> registry discovery
-> scoring
-> policy filtering
-> dependency graph validation
-> immutable runtime profile validation
-> execution with validators and audit evidence
```

The contract is encoded in `schemas/crm-skill-pack.schema.json`.

## Required Fields

A CRM skill pack declares:

- package identity, tenant, status, task types, and required tenant
  capabilities,
- UI binding surfaces and human-readable entry point label,
- `confirmation_required = true`,
- `grants_runtime_authority = false`,
- candidate SCAS modules, policies, and validators,
- `requires_immutable_runtime_profile = true`,
- audit evidence fields retained on the Hetzner Runtime Plane.

## Tenant Boundary

A tenant may declare skill-pack IDs in `ui_profile.scas_skill_packs`, but the
full package contract remains a separate validated artifact. Tenant UI config
may make a package visible only when the tenant role grants the required
capabilities. It does not bypass module registry selection or runtime
validation.

## Acceptance

The CRM skill-pack contract is acceptable when:

1. The JSON schema rejects UI bindings that grant runtime authority.
2. The JSON schema rejects packages that do not require human confirmation.
3. The JSON schema rejects packages that do not require immutable runtime
   profile validation.
4. Examples validate against the schema.
5. Tenant-specific packages reference tenant-local capabilities and policies.
