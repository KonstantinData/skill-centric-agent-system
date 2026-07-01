ALTER TABLE runtime.runtime_runs
    ADD COLUMN IF NOT EXISTS token_budget_total INTEGER CHECK (
        token_budget_total IS NULL OR token_budget_total >= 0
    );

ALTER TABLE runtime.runtime_runs
    ADD COLUMN IF NOT EXISTS tokens_used_total INTEGER NOT NULL DEFAULT 0 CHECK (
        tokens_used_total >= 0
    );

ALTER TABLE runtime.runtime_runs
    ADD COLUMN IF NOT EXISTS stop_reason TEXT CHECK (
        stop_reason IS NULL OR stop_reason IN (
            'completed',
            'max_tokens',
            'max_duration',
            'max_tool_calls',
            'max_data_reads',
            'max_memory_ops',
            'max_recompositions',
            'policy_denied',
            'validator_failed',
            'tool_error',
            'cancelled',
            'needs_recomposition',
            'composer_failure',
            'runtime_error'
        )
    );

ALTER TABLE runtime.runtime_steps
    ADD COLUMN IF NOT EXISTS stop_reason TEXT CHECK (
        stop_reason IS NULL OR stop_reason IN (
            'completed',
            'max_tokens',
            'max_duration',
            'max_tool_calls',
            'max_data_reads',
            'max_memory_ops',
            'max_recompositions',
            'policy_denied',
            'validator_failed',
            'tool_error',
            'cancelled',
            'needs_recomposition',
            'composer_failure',
            'runtime_error'
        )
    );

ALTER TABLE runtime.runtime_steps
    ADD COLUMN IF NOT EXISTS token_budget INTEGER CHECK (
        token_budget IS NULL OR token_budget >= 0
    );

ALTER TABLE runtime.runtime_steps
    ADD COLUMN IF NOT EXISTS tokens_used INTEGER NOT NULL DEFAULT 0 CHECK (
        tokens_used >= 0
    );

ALTER TABLE runtime.runtime_steps
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT CHECK (
        idempotency_key IS NULL OR idempotency_key <> ''
    );

ALTER TABLE runtime.runtime_steps
    ADD COLUMN IF NOT EXISTS attempt INTEGER NOT NULL DEFAULT 1 CHECK (attempt >= 1);

CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_steps_run_idempotency_key
    ON runtime.runtime_steps (run_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS runtime.runtime_events (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    run_id TEXT NOT NULL,
    step_id TEXT,
    event_index INTEGER NOT NULL CHECK (event_index >= 0),
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'task_intake_normalized',
            'task_analyzed',
            'candidates_discovered',
            'candidates_scored',
            'policies_evaluated',
            'graph_validated',
            'profile_emitted',
            'profile_validated',
            'runtime_started',
            'access_attempted',
            'validator_executed',
            'runtime_completed',
            'runtime_failed',
            'runtime_cancelled',
            'tenant_throttled',
            'quota_reserved',
            'quota_exhausted',
            'step_started',
            'step_completed',
            'tool_invocation_started',
            'tool_invocation_completed',
            'budget_exhausted',
            'checkpoint_created',
            'recomposition_requested'
        )
    ),
    actor_role TEXT NOT NULL CHECK (
        actor_role IN (
            'context_manager',
            'planner',
            'executor',
            'validator',
            'policy_engine',
            'quota_manager',
            'runtime',
            'composer'
        )
    ),
    planned_action_uri TEXT CHECK (
        planned_action_uri IS NULL OR planned_action_uri <> ''
    ),
    execution_uri TEXT CHECK (
        execution_uri IS NULL OR execution_uri <> ''
    ),
    result_uri TEXT CHECK (
        result_uri IS NULL OR result_uri <> ''
    ),
    stop_reason TEXT CHECK (
        stop_reason IS NULL OR stop_reason IN (
            'completed',
            'max_tokens',
            'max_duration',
            'max_tool_calls',
            'max_data_reads',
            'max_memory_ops',
            'max_recompositions',
            'policy_denied',
            'validator_failed',
            'tool_error',
            'cancelled',
            'needs_recomposition',
            'composer_failure',
            'runtime_error'
        )
    ),
    idempotency_key TEXT NOT NULL CHECK (idempotency_key <> ''),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (run_id, event_index),
    UNIQUE (run_id, idempotency_key),
    FOREIGN KEY (run_id) REFERENCES runtime.runtime_runs (id) ON DELETE CASCADE,
    FOREIGN KEY (step_id, run_id)
        REFERENCES runtime.runtime_steps (id, run_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runtime_events_run_index
    ON runtime.runtime_events (run_id, event_index);

CREATE INDEX IF NOT EXISTS idx_runtime_events_type_created
    ON runtime.runtime_events (event_type, created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_events_actor_created
    ON runtime.runtime_events (actor_role, created_at);

CREATE INDEX IF NOT EXISTS idx_runtime_events_stop_reason
    ON runtime.runtime_events (stop_reason)
    WHERE stop_reason IS NOT NULL;

CREATE TABLE IF NOT EXISTS runtime.runtime_checkpoints (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    run_id TEXT NOT NULL,
    step_id TEXT,
    checkpoint_index INTEGER NOT NULL CHECK (checkpoint_index >= 0),
    phase TEXT NOT NULL CHECK (
        phase IN (
            'task_intake',
            'analysis',
            'composition',
            'context',
            'planner',
            'executor',
            'validator',
            'finalization'
        )
    ),
    state_uri TEXT NOT NULL CHECK (state_uri <> ''),
    tokens_used_total INTEGER NOT NULL DEFAULT 0 CHECK (tokens_used_total >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE (run_id, checkpoint_index),
    FOREIGN KEY (run_id) REFERENCES runtime.runtime_runs (id) ON DELETE CASCADE,
    FOREIGN KEY (step_id, run_id)
        REFERENCES runtime.runtime_steps (id, run_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runtime_checkpoints_run_index
    ON runtime.runtime_checkpoints (run_id, checkpoint_index);

CREATE INDEX IF NOT EXISTS idx_runtime_checkpoints_phase_created
    ON runtime.runtime_checkpoints (phase, created_at);
