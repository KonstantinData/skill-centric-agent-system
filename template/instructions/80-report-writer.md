---
name: scas-report-writer
version: "0.1.0"
kind: instruction
description: Instruction for SCAS final operator-facing report package composition.
triggers:
  - report package
  - bilingual briefing
  - final report
  - pdf export context
inputs:
  - pipeline data
  - domain packages
  - report knowledge
outputs:
  - report package
  - composed report
  - validation results
required_tools:
  - llm_structured
optional_tools: []
knowledge_scopes:
  - report_blueprint_de
  - report_blueprint_en
  - report_quality_gates
  - report_rules
data_scopes:
  - current_run_pipeline_data
policies:
  - no_raw_evidence_dump
  - secret_guard_before_llm
validators:
  - required_report_fields
  - language_validation
  - min_sections
tests:
  - report package preserves run_id and run_status
---

# Report Writer

Run the reporting phase for final packaging, not as a researcher.

## Own

- Compose German and English operator-facing briefing drafts.
- Load report blueprint, report rules, and report quality gates.
- Build a stable `report_package` with report status, title, executive summary, visual focus, recommended sections, open gaps, data request sheet, outreach playbook, composed report, and validation.
- Prefer concise meeting-ready language over raw evidence dumping.

## Validation

Validate:
- required global fields
- minimum section count
- risk and next-step limits
- language markers
- required phrase for "no free public sources" when public contact evidence is exhausted

## Fallback

If LLM composition fails or misses required fields, merge from deterministic fallback drafts and keep validation notes.
