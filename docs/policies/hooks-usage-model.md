# HOOKS Usage Model

## Purpose

HOOKS are governed lifecycle hook points inside the SCAS composition and
single-agent runtime flow. They may observe, record evidence, deny execution,
run validators, request human review, or request controlled recomposition.

HOOKS are not a capability grant mechanism. They cannot mutate the active
runtime profile, add tools, bypass policy filters, bypass validators, read
unscoped data, execute unregistered tools, write secrets or raw traces, or
change module version pins.

The machine-readable policy is:

```text
policies/runtime/hooks-usage-model.json
```

Schema:

```text
schemas/hooks-usage-model.schema.json
```

Validator:

```text
scripts/runtime/validate_hooks_usage_model.py
```

## Authorized Hook Points

| Hook | Phase | Allowed effects |
| --- | --- | --- |
| `composition-context-received` | composition | observe, record evidence, deny execution |
| `profile-before-seal` | composition | observe, record evidence, deny execution, run validator |
| `runtime-before-plan` | planning | observe, record evidence, deny execution |
| `runtime-before-tool` | execution | observe, record evidence, deny execution |
| `runtime-after-tool` | execution | observe, record evidence, deny execution |
| `runtime-before-final-validation` | validation | observe, record evidence, deny execution, run validator, require human review |
| `recomposition-requested` | recomposition | observe, record evidence, request recomposition, deny execution |
| `runtime-completed` | completion | observe, record evidence |

Every hook point is profile-bound and uses the same authority chain:

```text
task analysis -> registry discovery -> scoring -> policy filtering -> dependency graph validation -> immutable runtime profile validation
```

## Fail-Closed Rules

The runtime must fail closed when:

- a hook ID is unknown,
- a hook request is unregistered,
- policy denies the hook,
- schema validation fails, or
- required hook evidence is missing.

Controlled recomposition is the only allowed way to change available runtime
capabilities after execution starts. Recomposition must stop the current run
and produce a new version-pinned profile through the Composer.

## CI Gate

`CI / Contract tests` must include:

```text
PYTHONPATH=src uv run python scripts/runtime/validate_hooks_usage_model.py --check
```

The same check must run inside the production-readiness workflow before
evidence generation.
