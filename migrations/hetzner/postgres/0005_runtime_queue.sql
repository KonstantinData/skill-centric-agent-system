CREATE TABLE IF NOT EXISTS runtime.runtime_queue_items (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    task_id TEXT NOT NULL CHECK (task_id ~ '^[a-z][a-z0-9-]*$'),
    tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z][a-z0-9-]*$'),
    area_id TEXT NOT NULL CHECK (area_id ~ '^[a-z][a-z0-9-]*$'),
    environment TEXT NOT NULL DEFAULT 'dev' CHECK (environment IN ('dev', 'staging', 'prod')),
    queue_name TEXT NOT NULL DEFAULT 'default' CHECK (queue_name ~ '^[a-z][a-z0-9-]*$'),
    status TEXT NOT NULL CHECK (
        status IN (
            'queued',
            'claiming',
            'running',
            'succeeded',
            'failed',
            'cancelled',
            'retry_scheduled',
            'dead_lettered'
        )
    ),
    priority INTEGER NOT NULL DEFAULT 0,
    scheduled_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts INTEGER NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
    claimed_by TEXT CHECK (claimed_by IS NULL OR claimed_by <> ''),
    claimed_at TIMESTAMPTZ,
    claimed_until TIMESTAMPTZ,
    lease_expires_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    attempt_id TEXT CHECK (attempt_id IS NULL OR attempt_id ~ '^[a-z][a-z0-9-]*$'),
    task_payload_uri TEXT NOT NULL CHECK (task_payload_uri <> ''),
    composition_context_uri TEXT CHECK (
        composition_context_uri IS NULL OR composition_context_uri <> ''
    ),
    run_id TEXT CHECK (run_id IS NULL OR run_id ~ '^[a-z][a-z0-9-]*$'),
    last_error TEXT,
    idempotency_key TEXT NOT NULL CHECK (idempotency_key <> ''),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CHECK (claimed_at IS NULL OR claimed_until IS NOT NULL),
    CHECK (updated_at >= created_at),
    UNIQUE (idempotency_key),
    FOREIGN KEY (run_id) REFERENCES runtime.runtime_runs (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_queue_claimable
    ON runtime.runtime_queue_items (
        environment,
        queue_name,
        status,
        scheduled_at,
        priority DESC,
        created_at,
        id
    )
    WHERE status IN ('queued', 'retry_scheduled');

CREATE INDEX IF NOT EXISTS idx_runtime_queue_tenant_status
    ON runtime.runtime_queue_items (tenant_id, status, scheduled_at);

CREATE INDEX IF NOT EXISTS idx_runtime_queue_claimed_until
    ON runtime.runtime_queue_items (claimed_until)
    WHERE status IN ('claiming', 'running');

CREATE INDEX IF NOT EXISTS idx_runtime_queue_run
    ON runtime.runtime_queue_items (run_id)
    WHERE run_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS runtime.runtime_run_attempts (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    queue_id TEXT NOT NULL REFERENCES runtime.runtime_queue_items (id) ON DELETE CASCADE,
    run_id TEXT CHECK (run_id IS NULL OR run_id ~ '^[a-z][a-z0-9-]*$'),
    tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z][a-z0-9-]*$'),
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    status TEXT NOT NULL CHECK (
        status IN (
            'queued',
            'claiming',
            'running',
            'succeeded',
            'failed',
            'cancelled',
            'retry_scheduled',
            'dead_lettered'
        )
    ),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    stop_reason TEXT,
    profile_id TEXT CHECK (profile_id IS NULL OR profile_id ~ '^[a-z][a-z0-9-]*$'),
    profile_sha256 TEXT CHECK (profile_sha256 IS NULL OR profile_sha256 ~ '^[a-f0-9]{64}$'),
    UNIQUE (queue_id, attempt_number)
);

CREATE INDEX IF NOT EXISTS idx_runtime_run_attempts_queue
    ON runtime.runtime_run_attempts (queue_id, attempt_number);

CREATE TABLE IF NOT EXISTS runtime.runtime_run_claims (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    queue_id TEXT NOT NULL REFERENCES runtime.runtime_queue_items (id) ON DELETE CASCADE,
    worker_id TEXT NOT NULL CHECK (worker_id <> ''),
    tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z][a-z0-9-]*$'),
    claimed_at TIMESTAMPTZ NOT NULL,
    claimed_until TIMESTAMPTZ NOT NULL,
    heartbeat_at TIMESTAMPTZ NOT NULL,
    released_at TIMESTAMPTZ,
    release_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_runtime_run_claims_active
    ON runtime.runtime_run_claims (tenant_id, claimed_until)
    WHERE released_at IS NULL;

CREATE TABLE IF NOT EXISTS runtime.runtime_dead_letters (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    queue_id TEXT NOT NULL REFERENCES runtime.runtime_queue_items (id) ON DELETE CASCADE,
    run_id TEXT,
    attempt_id TEXT,
    tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z][a-z0-9-]*$'),
    error_type TEXT NOT NULL CHECK (error_type <> ''),
    error_message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_dead_letters_tenant_created
    ON runtime.runtime_dead_letters (tenant_id, created_at);

CREATE TABLE IF NOT EXISTS runtime.runtime_quota_reservations (
    id TEXT PRIMARY KEY CHECK (id ~ '^[a-z][a-z0-9-]*$'),
    queue_id TEXT NOT NULL REFERENCES runtime.runtime_queue_items (id) ON DELETE CASCADE,
    run_id TEXT,
    tenant_id TEXT NOT NULL CHECK (tenant_id ~ '^[a-z][a-z0-9-]*$'),
    quota_window TEXT NOT NULL CHECK (quota_window <> ''),
    reserved_tokens INTEGER NOT NULL DEFAULT 0 CHECK (reserved_tokens >= 0),
    reserved_tool_calls INTEGER NOT NULL DEFAULT 0 CHECK (reserved_tool_calls >= 0),
    status TEXT NOT NULL CHECK (status IN ('reserved', 'finalized', 'refunded')),
    created_at TIMESTAMPTZ NOT NULL,
    finalized_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_runtime_quota_reservations_tenant_window
    ON runtime.runtime_quota_reservations (tenant_id, quota_window, status);
