---
name: scas-report-package
description: Build the ReportWriter final package from the current SCAS runtime profile. Use when Codex needs bilingual DE/EN target-company briefing drafts, report validation, report section recommendations, visual-focus mapping, open gaps, data request sheet, or outreach playbook packaging.
---

# SCAS Report Package

Use this skill for final operator-facing packaging.

## SCAS Runtime Surfaces

- `registry/modules/**/module.json`
- `schemas/runtime-profile.schema.json`
- `src/skill_centric_agent_system/runtime/`
- `docs/policies/module-contracts.md`
- report blueprint, quality gate, and report rule modules selected by the runtime profile

## Workflow

1. Build report context from run data, synthesis, company profile, market network, contact intelligence, quality review, data request sheet, and outreach playbook.
2. Compose German and English drafts from report blueprints.
3. Use structured LLM composition when configured and allowed.
4. Merge deterministic fallback fields when LLM output is missing required fields.
5. Validate required fields, section count, language markers, risk and next-step limits, and no-free-source phrasing.
6. Return stable `report_package` with validation metadata.

## Boundaries

- Do not conduct additional research.
- Do not dump long source lists or raw evidence registers.
- Preserve `run_id`, `run_status`, confidence, blockers, and meeting actions.

## Select With

Instructions:
- `template/instructions/80-report-writer.md`
- `template/instructions/90-memory-and-tool-boundaries.md`
