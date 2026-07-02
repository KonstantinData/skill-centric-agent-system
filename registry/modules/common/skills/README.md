# Skill Entrypoints

`module.json` is the normative discovery and selection contract for every SCAS
skill. It owns task signals, scoring, required inputs, tools, scopes, policies,
validators, provenance, and fixture evidence.

`SKILL.md` is execution guidance only. It is loaded after registry discovery,
scoring, policy filtering, dependency graph validation, and immutable runtime
profile validation select the skill. The Composer must not search `SKILL.md`
text to select skills or grant capabilities.

Skill modules may omit `entrypoint` until they have execution guidance that is
useful after selection. When an entrypoint exists, `entrypoint.guidance` must be
one of:

- `shared_template`: the file carries only the shared sealed-profile execution
  template below.
- `skill_specific`: the file adds concrete execution behavior for the selected
  skill beyond the shared template.

Shared template:

```markdown
## Runtime Contract

Use this skill only when it is selected through a sealed SCAS runtime profile.
Do not use this SKILL.md as selection metadata; selection comes from module.json
and Control Plane composition records.

## Execution Guidance

- Preserve the profile-selected tools, policies, validators, and scopes declared
  in module.json.
- Keep outputs aligned with the module validators and runtime skill handler
  coverage.
- Fail closed when required inputs, tools, handler bindings, or validators are
  missing.
```

Registry validation fails if a `SKILL.md` contains structured selection metadata
such as `task_signals`, `base_score`, `score_modifiers`, direct tool/scope
grant lists, policy lists, or validator lists. Those fields belong in
`module.json`.
