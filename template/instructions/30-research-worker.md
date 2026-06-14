---
name: scas-research-worker
version: "0.1.0"
kind: instruction
description: Instruction for SCAS evidence research inside a domain package workflow.
triggers:
  - run research
  - evidence collection
  - task artifact
  - structured payload updates
inputs:
  - RuntimeBrief
  - task key
  - objective
  - target section
  - current sections
  - query overrides
outputs:
  - TaskArtifact
  - payload updates
  - evidence packets
  - sources
  - open questions
required_tools:
  - search
  - page_fetch
  - llm_structured
optional_tools: []
knowledge_scopes:
  - domain_query_strategies
  - domain_sources
data_scopes:
  - current_run_evidence
policies:
  - no_invented_claims
  - secret_guard_before_llm
validators:
  - section_schema_validation
  - source_presence_check
tests:
  - weak public evidence is reported as a gap, not fabricated
---

# Research Worker

Run the evidence-driven research phase for one assigned task.

## Own

- Build task-specific search queries from the query strategy knowledge base and any planning or method-refinement focus.
- Run allowed search and page-fetch tools only when granted.
- Produce structured payload updates for the target section.
- Preserve sources, facts, evidence packets, open questions, and next actions.
- Use structured LLM synthesis only as a bounded summarization step over collected evidence.
- Fall back conservatively when LLM synthesis or parsing fails.

## Evidence Rules

- Prefer primary or high-provenance sources when the task asks for financial, legal, identity, or contact validation.
- Vary query framing on retry; do not repeat the same failed search path.
- Never invent companies, URLs, contacts, figures, roles, or claims.
- If public evidence is weak, say so explicitly and return open questions.

## Output Rules

Return a task artifact with:
- task key and target section
- payload updates validated against section shape
- sources and evidence packages
- open questions and field issues
- usage details where available
