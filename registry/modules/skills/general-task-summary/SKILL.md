---
name: general-task-summary
description: Produce a bounded generic runtime summary when no specialized task strategy is selected. Use when a runtime profile selects general-task-summary or when maintaining this SCAS registry skill module and its handler, tools, policies, validators, tests, or instruction pack.
---

# general-task-summary

## Runtime Contract

Use this skill only when it is selected through a sealed SCAS runtime profile. Do not use this SKILL.md as selection metadata; selection comes from module.json and Control Plane composition records.

## Execution Guidance

- Preserve the profile-selected tools, policies, validators, and scopes declared in module.json.
- Keep outputs aligned with the module validators and runtime skill handler coverage.
- Fail closed when required inputs, tools, handler bindings, or validators are missing.
