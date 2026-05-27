---
name: scas-company-department
description: Run the Company Department responsibility set from the current SCAS runtime profile. Use when Codex needs company fundamentals, economic and commercial situation, financial deep dive, product and asset scope, or transaction and event intelligence for a Liquisto pre-meeting briefing.
---

# SCAS Company Department

Use this skill for Company Department work.

## Current Tasks

- `company_fundamentals`: verify identity, website, industry, description, products and services.
- `economic_commercial_situation`: assess pressure, recent events, financial pressure, inventory signals, revenue trend.
- `financial_deep_dive`: extract financial assessment, key financials, inventory positions, balance-sheet signals.
- `product_asset_scope`: classify visible goods, components, materials, spare parts, and inventory positions.
- `transaction_event_intelligence`: identify M&A, carve-outs, restructurings, program terminations, and regulatory disclosures.

## Evidence Priorities

Prefer:
- owned website for identity and product scope
- annual reports, filings, investor documents, and registries for financial evidence
- press releases and trade press for strategic events
- public product pages for made vs distributed vs held-in-stock classification

## Completion Bar

Each task must produce structured section payload updates, evidence packets, sources, open questions, and an accepted or degraded decision. Gaps are acceptable only when core facts are either satisfied or explicitly degraded by the Judge.

## Select With

Instructions:
- `template/instructions/20-department-lead.md`
- `template/instructions/30-research-worker.md`
- `template/instructions/40-critic-quality-gate.md`
- `template/instructions/50-judge-resolution.md`
- `template/instructions/60-coding-specialist-query-refinement.md`
- `template/instructions/90-memory-and-tool-boundaries.md`

Knowledge scopes:
- `knowledge/sources/company.yaml`
- `knowledge/query_strategies/company.yaml`
- `knowledge/policies/company.yaml`
