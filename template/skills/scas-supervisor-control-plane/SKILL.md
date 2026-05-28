---
name: scas-supervisor-control-plane
description: Compose and execute the Supervisor control-plane workflow from the current SCAS runtime profile. Use when Codex needs to normalize target-company intake, build a SupervisorBrief, route department assignments, admit department packages, or route run-based follow-up questions without performing domain research.
---

# SCAS Supervisor Control Plane

Use this skill for Supervisor responsibilities in a SCAS profile.

## Source Runtime

- `src/agents/supervisor.py`
- `src/orchestration/supervisor_loop.py`
- `src/orchestration/task_router.py`
- `src/orchestration/runtime_agents.py`
- `src/orchestration/tool_policy.py`

## Workflow

1. Normalize company name and web domain into a canonical domain contract.
2. Build a `SupervisorBrief` with identity, industry, evidence, missing evidence, fetch audit, readiness, and routing gaps.
3. Build assignments from the standard task backlog.
4. Run department ordering as contract state: Company and Market first, Buyer after Step 1, Contact after Buyer.
5. Apply package admission: accepted payloads become downstream-visible; rejected packages remain diagnostic.
6. Route follow-up questions by keyword scoring to Contact, Buyer, Market, Synthesis, or Company.

## Boundaries

- Do not do domain fact interpretation.
- Do not review task evidence inside department loops.
- Do not decide department retries.
- Do not expose rejected packages as validated downstream truth.

## Select With

Instructions:
- `template/instructions/00-runtime-profile-contract.md`
- `template/instructions/10-supervisor-control-plane.md`
- `template/instructions/90-memory-and-tool-boundaries.md`

Validators:
- supervisor brief schema validation
- department package admission gate
- runtime assignment completeness
