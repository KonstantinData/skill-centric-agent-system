---
name: scas-memory-and-tool-boundaries
version: "0.1.0"
kind: instruction
description: Instruction for preserving SCAS memory and tool-policy boundaries in composed runtime profiles.
triggers:
  - tool policy
  - memory boundary
  - long term memory
  - runtime guardrails
inputs:
  - role name
  - task key
  - run context
outputs:
  - allowed tools
  - memory scopes
  - policy constraints
required_tools: []
optional_tools: []
knowledge_scopes:
  - tool_policy
  - memory_policy
data_scopes:
  - current_run_only
policies:
  - explicit_tool_grants_only
  - process_memory_only
validators:
  - unauthorized_tool_access_check
  - no_customer_fact_long_term_memory
tests:
  - selected profile does not grant all tools or all memory by default
---

# Memory And Tool Boundaries

Apply these boundaries to every SCAS runtime profile.

## Tool Grants

Grant tools by role and task only:
- control phase: `website_snapshot`, `search`
- research phase: `search`, `page_fetch`, `llm_structured`
- planning, quality-gate, and resolution phases: no external tools by default
- method-refinement phase: `query_refinement`
- synthesis phase: segment-read, follow-up-request, finalize tools
- reporting phase: structured LLM composition where configured

Do not let the runtime self-grant tools outside the composed profile grant.

## Run Memory

Run-scoped memory may include task artifacts, reviews, decisions, evidence packets, notes, open questions, rejected paths, strategy changes, resolution escalations, method-refinement usage, domain packages, readiness assessment, and final briefing.

## Long-Term Memory

Long-term memory may contain process patterns only:
- search/query patterns
- critique heuristics
- escalation principles
- completion patterns
- parsing, extraction, and debugging tactics

Never store target-company facts, customer/domain-specific evidence, or run-specific conclusions as reusable truth.
