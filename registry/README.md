# SCAS Registry

`registry/` is the repository source of truth for selectable SCAS modules.
`examples/` contains fixtures, generated examples, and API samples only.

The state flow is one-way:

```text
registry/modules/**/module.json
  -> registry validation
  -> registry/versions/lockfile.json
  -> generated Control Plane seed SQL
  -> deployed Control Plane state
```

Do not edit generated seed SQL as the durable source of truth. Change the
registry source, validate it, regenerate the lockfile, and then regenerate seed
artifacts.

Each skill module uses two layers:

- `module.json`: machine-readable selection, dependency, policy, environment,
  version, runtime contract, provenance, and fixture evidence metadata.
- Optional `SKILL.md`: agent-readable execution guidance loaded only after a
  sealed runtime profile selects the skill.

Direct modules must include positive and negative selection evidence. Support
modules such as tools, scopes, policies, and validators should normally use
`selection.mode: "dependency_only"` and include dependency-inclusion plus
no-direct-selection evidence.

Skill entrypoints are governed by `registry/modules/common/skills/README.md`.

Common reusable modules live under:

```text
registry/modules/common/skills/
registry/modules/common/validators/
registry/modules/common/policies/
```

Tenant-specific selectable modules stay in the module registry, grouped by
tenant namespace rather than under tenant configuration:

```text
registry/modules/tenants/<tenant-id>/skills/
registry/modules/tenants/<tenant-id>/validators/
registry/modules/tenants/<tenant-id>/policies/
```

Tenant configuration remains under `registry/tenants/`. Tenant-specific CRM
skill-pack contracts are tenant skill authority and live under
`registry/modules/tenants/<tenant-id>/skills/<skill-pack-id>/skill-pack.json`.
