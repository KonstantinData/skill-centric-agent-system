---
name: scas-runtime-profile-contract
version: "0.1.0"
kind: instruction
description: Base instruction for composing SCAS runtime profiles from governed registry modules.
triggers:
  - SCAS briefing runtime
  - runtime profile composition
  - skill-centric runtime mapping
inputs:
  - user objective
  - company name
  - web domain
  - registry module metadata
outputs:
  - selected instructions
  - selected skills
  - allowed tools
  - validators
required_tools: []
optional_tools: []
knowledge_scopes:
  - scas_runtime_architecture
data_scopes:
  - task_local_runtime_context
policies:
  - explicit_tool_grants_only
  - no_cross_run_customer_memory
validators:
  - runtime_profile_completeness
  - output_contract_compliance
tests:
  - selected modules map to the requested SCAS runtime responsibilities
---

# Runtime Profile Contract

Use this base instruction when composing a single-agent SCAS runtime profile from governed registry modules. Preserve the domain workflow intent while keeping execution inside one governed runtime agent.

## Runtime Source

Primary SCAS source surfaces:
- `registry/modules/**/module.json`
- `schemas/runtime-profile.schema.json`
- `schemas/module.schema.json`
- `src/skill_centric_agent_system/composition/`
- `src/skill_centric_agent_system/runtime/`
- `docs/reference/architecture.md`
- `docs/policies/module-contracts.md`

## Profile Shape

Select only the modules needed for the task:
- instructions for the active runtime role and phase
- skills for the active domain or capability
- tools granted by the selected profile role and task
- knowledge scopes for the relevant domain only
- validators matching the output contract

Do not load all domain, report, memory, and policy knowledge by default.

## Runtime Profile Modes

Represent the workflow as task-local runtime modes inside one runtime agent:
- `control`: intake normalization, task routing, domain package admission, follow-up routing
- `company-domain`: company facts, economics, finance, product and asset scope, strategic events
- `market-domain`: market situation and inventory-relevant demand or supply pressure
- `buyer-domain`: peers, downstream buyers, monetization paths, redeployment paths
- `contact-domain`: target-company contacts, buyer-firm contacts, contact qualification
- `synthesis`: cross-domain opportunity assessment and negotiation relevance
- `reporting`: bilingual operator-facing report package

Inside each domain package workflow, preserve responsibilities as phases:
- planning phase builds the investigation plan and final package
- research phase gathers evidence
- quality-gate phase validates evidence quality
- resolution phase handles borderline or exhausted tasks
- method-refinement phase improves blocked search methods

## Hard Boundaries

- Preserve SCAS package-contract vocabulary: `TaskArtifact`, `TaskReviewArtifact`, `TaskDecisionArtifact`, `DomainPackage`, `EvidencePacket`, `GapCandidate`, `AnswerMatrixUpdate`.
- Treat narrative summaries as secondary; structured artifacts and answer-matrix coverage drive closure.
- Keep the control phase out of domain-internal retries and resolution decisions.
- Use explicit tool grants; the runtime may not self-grant search, page fetch, LLM, memory, or write access.
- Store reusable long-term memory only as process patterns, never target-company facts or run-specific conclusions.
