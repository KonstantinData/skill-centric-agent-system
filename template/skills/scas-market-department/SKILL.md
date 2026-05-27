---
name: scas-market-department
description: Run the Market Department responsibility set from the current SCAS runtime profile. Use when Codex needs market situation analysis for Liquisto, including demand trend, supply pressure, overcapacity, slowdown, and inventory-relevant market signals.
---

# SCAS Market Department

Use this skill for Market Department work.

## Current Tasks

- `market_situation`: assess market demand, supply pressure, overcapacity, growth or decline, trend direction, key trends, market size, and growth rate.

## Evidence Priorities

Prefer:
- industry reports and market data where available
- trade publications and sector news
- public signals of capacity, slowdown, demand weakness, shortages, or excess stock
- target-company-adjacent market signals that influence inventory pressure

## Completion Bar

The task must identify industry name, assessment, demand outlook, trend direction, and at least two key trends. Supporting fields such as market size and growth rate improve confidence but should not block completion if core evidence is present.

## Select With

Instructions:
- `template/instructions/20-department-lead.md`
- `template/instructions/30-research-worker.md`
- `template/instructions/40-critic-quality-gate.md`
- `template/instructions/50-judge-resolution.md`
- `template/instructions/60-coding-specialist-query-refinement.md`
- `template/instructions/90-memory-and-tool-boundaries.md`

Knowledge scopes:
- `knowledge/sources/market.yaml`
- `knowledge/query_strategies/market.yaml`
- `knowledge/policies/market.yaml`
