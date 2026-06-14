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
  version, and runtime contract metadata.
- `SKILL.md`: agent-readable execution guidance loaded only after a sealed
  runtime profile selects the skill.
