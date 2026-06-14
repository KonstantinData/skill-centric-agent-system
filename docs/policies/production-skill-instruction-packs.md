# Production Skill Instruction Packs

## Purpose

Production-required skill handlers need executable, version-pinned instruction
packs that bind:

- module metadata (`registry/modules/**/module.json`),
- handler registration (`src/skill_centric_agent_system/runtime/skill_handlers.py`),
- static test evidence, and
- live-run evidence requirements for certification.

The machine-readable artifact is:

```text
examples/runtime/production-skill-instruction-packs.json
```

Generated and validated by:

```text
scripts/runtime/production_skill_instruction_packs.py
```

Schema:

```text
schemas/production-skill-instruction-packs.schema.json
```

## Rule Set

1. Include every `kind = skill` module with `runtime_role in {runtime, shared}`.
2. Fail closed if a production-required skill is missing an executable handler
   for the exact `name@version` pair.
3. Persist deterministic execution instructions for each skill pack:
   - profile composition preconditions,
   - required task signals/inputs,
   - runtime handler-binding evidence checkpoint requirement,
   - validator + evidence persistence requirement.
4. Track test evidence for module and runtime layers.
5. Track live-run evidence requirements for certification-mode validation.

## CI Gate

`CI / Contract tests` must include:

```text
PYTHONPATH=src uv run python scripts/runtime/production_skill_instruction_packs.py --check
```

The same check must run inside production-readiness workflow before evidence
generation.
