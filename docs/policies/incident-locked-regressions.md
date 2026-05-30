# Incident-Locked Regressions

## Purpose

Incident-locked regressions are never-again fixtures tied to confirmed drift or
safety incidents.
Each incident case must be bound to:

- an invariant ID, and
- a change-type expectation from the formal safety change-type matrix.

## Execution

- Fixture corpus:
  `examples/evaluations/incident-locked-regression-cases.json`
- Runner:
  `scripts/runtime/run_incident_locked_regressions.py`
- CI gate evidence:
  `ci-evidence/incident-locked-regressions.json`

The runner fails closed when:

- a case references an unknown change type,
- a case invariant is not mandatory for the specified change type, or
- replay results do not match expected violation outcomes.
