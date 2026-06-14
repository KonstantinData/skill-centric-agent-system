---
name: scas-company-domain
description: Run the Company domain package responsibility set from the current SCAS runtime profile. Use when Codex needs company fundamentals, economic and commercial situation, financial deep dive, product and asset scope, or transaction and event intelligence for a target-company pre-meeting briefing.
---

# SCAS Company Domain

Use this skill for Company domain package work.

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

Each task must produce structured section payload updates, evidence packets, sources, open questions, and an accepted or degraded decision. Gaps are acceptable only when core facts are either satisfied or explicitly degraded by the resolution phase.

## Select With

Instructions:
- `template/instructions/20-domain-package-planning.md`
- `template/instructions/30-research-worker.md`
- `template/instructions/40-quality-gate.md`
- `template/instructions/50-resolution.md`
- `template/instructions/60-query-refinement.md`
- `template/instructions/90-memory-and-tool-boundaries.md`

Knowledge scopes:
- company source knowledge scope selected by the runtime profile
- company query-strategy knowledge scope selected by the runtime profile
- company domain policy selected by the runtime profile
