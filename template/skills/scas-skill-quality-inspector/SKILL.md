---
name: scas-skill-quality-inspector
description: Review SCAS skills for trigger precision, boundary clarity, context footprint, consistency, and safety before acceptance.
---

# SCAS Skill Quality Inspector

## Outcome

Find and prioritize skill quality issues before skills are used in runtime composition.

## Inspection Checklist

1. Frontmatter quality: clear `name`, precise `description`.
2. Trigger quality: clear when to use and when not to use.
3. Boundary quality: no over-broad scope or hidden side effects.
4. Context economy: no verbose filler, no duplicated generic guidance.
5. Dependency clarity: referenced instructions/docs actually exist.
6. Safety: no secret handling anti-patterns, no implicit tool escalation.
7. SCAS consistency: language and assumptions match this repository.

## Severity

- High: safety, wrong trigger scope, or architecture conflict.
- Medium: unclear workflow or missing acceptance criteria.
- Low: wording and maintainability polish.

## Output Format

- Findings ordered by severity with file path and concrete fix.
- Final verdict: pass / pass-with-fixes / fail.