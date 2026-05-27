---
name: scas-skill-creator
description: Create or update SCAS skills in `template/skills` with precise triggers, lean context usage, explicit boundaries, and verifiable completion criteria.
---

# SCAS Skill Creator

## Outcome

Produce SCAS-aligned skills that are:
- focused on one responsibility,
- explicit about when to trigger,
- explicit about boundaries,
- small enough to stay maintainable.

## Workflow

1. Confirm target responsibility and expected output artifact.
2. Define trigger and non-trigger conditions.
3. Define bounded workflow steps.
4. Define completion and quality bar.
5. Add dependencies (`Select With`, validators, policy docs) only when required.
6. Keep text concise and avoid generic model behavior explanations.

## Required Structure

Each skill must contain:
- YAML frontmatter with `name` and `description`.
- `Outcome` and `Workflow` sections.
- `Boundaries` section with explicit exclusions.
- `Completion Bar` or equivalent acceptance criteria.

## SCAS Guardrails

- Keep single-agent runtime assumptions.
- Do not grant implicit tools, scopes, or permissions.
- Prefer deterministic checks and schema-bound outputs where possible.