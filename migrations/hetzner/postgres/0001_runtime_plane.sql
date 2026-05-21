CREATE SCHEMA IF NOT EXISTS runtime;

CREATE TABLE IF NOT EXISTS runtime.runtime_runs (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    task_id TEXT NOT NULL CHECK (task_id ~ '^[a-z][a-z0-9-]*$'),
    profile_id TEXT NOT NULL CHECK (profile_id ~ '^[a-z][a-z0-9-]*$'),
    profile_version TEXT NOT NULL CHECK (profile_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
    ),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    artifact_root_uri TEXT NOT NULL CHECK (artifact_root_uri <> ''),
    CHECK (completed_at IS NULL OR completed_at >= started_at),
    UNIQUE (id, profile_id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_runs_task
    ON runtime.runtime_runs (task_id);

CREATE INDEX IF NOT EXISTS idx_runtime_runs_profile
    ON runtime.runtime_runs (profile_id, profile_version);

CREATE INDEX IF NOT EXISTS idx_runtime_runs_status_started
    ON runtime.runtime_runs (status, started_at);

CREATE TABLE IF NOT EXISTS runtime.runtime_steps (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    run_id TEXT NOT NULL,
    step_index INTEGER NOT NULL CHECK (step_index >= 0),
    kind TEXT NOT NULL CHECK (kind IN ('context', 'planner', 'executor', 'validator')),
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
    ),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    CHECK (completed_at IS NULL OR completed_at >= started_at),
    UNIQUE (run_id, step_index),
    UNIQUE (id, run_id),
    FOREIGN KEY (run_id) REFERENCES runtime.runtime_runs (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runtime_steps_run_index
    ON runtime.runtime_steps (run_id, step_index);

CREATE INDEX IF NOT EXISTS idx_runtime_steps_status_started
    ON runtime.runtime_steps (status, started_at);

CREATE TABLE IF NOT EXISTS runtime.tool_invocations (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    tool_name TEXT NOT NULL CHECK (tool_name ~ '^[a-z][a-z0-9-]*$'),
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')
    ),
    input_uri TEXT NOT NULL CHECK (input_uri <> ''),
    output_uri TEXT NOT NULL CHECK (output_uri <> ''),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    CHECK (completed_at IS NULL OR completed_at >= started_at),
    FOREIGN KEY (run_id) REFERENCES runtime.runtime_runs (id) ON DELETE CASCADE,
    FOREIGN KEY (step_id, run_id)
        REFERENCES runtime.runtime_steps (id, run_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tool_invocations_run_step
    ON runtime.tool_invocations (run_id, step_id);

CREATE INDEX IF NOT EXISTS idx_tool_invocations_tool_status
    ON runtime.tool_invocations (tool_name, status);

CREATE TABLE IF NOT EXISTS runtime.validation_results (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    validator_id TEXT NOT NULL CHECK (validator_id ~ '^[a-z][a-z0-9-]*$'),
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'warning')),
    findings_uri TEXT NOT NULL CHECK (findings_uri <> ''),
    created_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runtime.runtime_runs (id) ON DELETE CASCADE,
    FOREIGN KEY (step_id, run_id)
        REFERENCES runtime.runtime_steps (id, run_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validation_results_run_step
    ON runtime.validation_results (run_id, step_id);

CREATE INDEX IF NOT EXISTS idx_validation_results_validator_status
    ON runtime.validation_results (validator_id, status);

CREATE TABLE IF NOT EXISTS runtime.memory_candidates (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    run_id TEXT NOT NULL,
    profile_id TEXT NOT NULL CHECK (profile_id ~ '^[a-z][a-z0-9-]*$'),
    source_step_id TEXT NOT NULL,
    target_memory_scope_id TEXT NOT NULL CHECK (
        target_memory_scope_id ~ '^[a-z][a-z0-9-]*$'
    ),
    content_uri TEXT NOT NULL CHECK (content_uri <> ''),
    sensitivity TEXT NOT NULL CHECK (
        sensitivity IN ('public', 'internal', 'confidential', 'secret')
    ),
    retention_policy TEXT NOT NULL CHECK (retention_policy ~ '^[a-z][a-z0-9-]*$'),
    validator_status TEXT NOT NULL CHECK (
        validator_status IN ('pending', 'approved', 'rejected')
    ),
    validator_id TEXT NOT NULL CHECK (validator_id ~ '^[a-z][a-z0-9-]*$'),
    policy_status TEXT NOT NULL CHECK (
        policy_status IN ('pending', 'approved', 'rejected', 'needs_clarification')
    ),
    policy_id TEXT NOT NULL CHECK (policy_id ~ '^[a-z][a-z0-9-]*$'),
    created_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (run_id, profile_id)
        REFERENCES runtime.runtime_runs (id, profile_id)
        ON DELETE CASCADE,
    FOREIGN KEY (source_step_id, run_id)
        REFERENCES runtime.runtime_steps (id, run_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_memory_candidates_run
    ON runtime.memory_candidates (run_id);

CREATE INDEX IF NOT EXISTS idx_memory_candidates_scope_status
    ON runtime.memory_candidates (
        target_memory_scope_id,
        validator_status,
        policy_status
    );

CREATE INDEX IF NOT EXISTS idx_memory_candidates_created_at
    ON runtime.memory_candidates (created_at);
