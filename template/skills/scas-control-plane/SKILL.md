---
name: scas-control-plane
description: Compose and execute the SCAS control-plane workflow from the current runtime profile. Use when Codex needs to normalize target-company intake, build a RuntimeBrief, route domain package assignments, admit domain packages, or route run-based follow-up questions without performing domain research.
---

# SCAS Control Plane

Use this skill for control-plane responsibilities in a SCAS runtime profile.

## SCAS Runtime Surfaces

- `registry/modules/**/module.json`
- `schemas/runtime-profile.schema.json`
- `src/skill_centric_agent_system/composition/`
- `src/skill_centric_agent_system/runtime/`
- `docs/policies/module-contracts.md`

## Workflow

1. Normalize company name and web domain into a canonical domain contract.
2. Build a `RuntimeBrief` with identity, industry, evidence, missing evidence, fetch audit, readiness, and routing gaps.
3. Build assignments from the standard task backlog.
4. Run domain ordering as contract state: Company and Market first, Buyer after Step 1, Contact after Buyer.
5. Apply package admission: accepted payloads become downstream-visible; rejected packages remain diagnostic.
6. Route follow-up questions by keyword scoring to Contact, Buyer, Market, Synthesis, or Company.

## Boundaries

- Do not do domain fact interpretation.
- Do not review task evidence inside domain package loops.
- Do not decide domain package retries.
- Do not expose rejected packages as validated downstream truth.

## Select With

Instructions:
- `template/instructions/00-runtime-profile-contract.md`
- `template/instructions/10-control-plane.md`
- `template/instructions/90-memory-and-tool-boundaries.md`

Validators:
- runtime brief schema validation
- domain package admission gate
- runtime assignment completeness
