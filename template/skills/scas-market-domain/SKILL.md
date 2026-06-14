---
name: scas-market-domain
description: Run the Market domain package responsibility set from the current SCAS runtime profile. Use when Codex needs market situation analysis for the target case, including demand trend, supply pressure, overcapacity, slowdown, and inventory-relevant market signals.
---

# SCAS Market Domain

Use this skill for Market domain package work.

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
- `template/instructions/20-domain-package-planning.md`
- `template/instructions/30-research-worker.md`
- `template/instructions/40-quality-gate.md`
- `template/instructions/50-resolution.md`
- `template/instructions/60-query-refinement.md`
- `template/instructions/90-memory-and-tool-boundaries.md`

Knowledge scopes:
- market source knowledge scope selected by the runtime profile
- market query-strategy knowledge scope selected by the runtime profile
- market domain policy selected by the runtime profile
