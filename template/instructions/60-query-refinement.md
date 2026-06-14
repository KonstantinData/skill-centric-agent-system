---
name: scas-query-refinement
version: "0.1.0"
kind: instruction
description: Instruction for bounded SCAS query and method refinement.
triggers:
  - query refinement
  - blocked research method
  - method issue
  - search strategy recovery
inputs:
  - task key
  - section
  - RuntimeBrief
  - critic issues
  - method brief
outputs:
  - refined query strategy
  - revision focus
required_tools:
  - query_refinement
optional_tools: []
knowledge_scopes:
  - domain_query_strategies
data_scopes:
  - current_task_review
policies:
  - no_direct_research_execution
validators:
  - query_strategy_token_present
tests:
  - method refinement returns strategy tokens instead of unbounded tool grants
---

# Query Refinement

Run bounded query refinement. Your job is to unblock stuck research by improving search method, not by taking over the task.

## Own

- Read quality-gate issues and rejected points.
- Select a better query strategy variant for the same task.
- Suggest focused query refinements for the research phase.
- Preserve accepted findings and target only the missing or weak points.

## Method Tactics

- If direct company search failed, try registries, filings, trade publications, investor materials, or source-type-specific searches.
- If results are noisy, add exact phrases, domain constraints, filetype hints, location, legal form, or product terms.
- If company identity is ambiguous, add normalized domain, headquarters, industry, or legal suffix terms.

## Output Rule

Return a bounded strategy token such as `strategy:<task_key>:method_refinement`, the rejected-point focus, and a short explanation. Do not grant yourself search, page fetch, or code execution.
