PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    name TEXT NOT NULL CHECK (name <> ''),
    kind TEXT NOT NULL CHECK (
        kind IN (
            'skill',
            'instruction',
            'tool',
            'knowledge_scope',
            'data_scope',
            'memory_scope',
            'policy',
            'validator'
        )
    ),
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'deprecated', 'deleted')),
    current_version_id TEXT NOT NULL CHECK (current_version_id <> ''),
    created_at TEXT NOT NULL CHECK (created_at <> ''),
    updated_at TEXT NOT NULL CHECK (updated_at <> '')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_modules_name
    ON modules (name);

-- current_version_id is validated by contract/application checks. Keeping it out
-- of D1 foreign keys avoids circular insert ordering during registry ingestion.
CREATE INDEX IF NOT EXISTS idx_modules_current_version
    ON modules (current_version_id);

CREATE INDEX IF NOT EXISTS idx_modules_kind_status
    ON modules (kind, status);

CREATE TABLE IF NOT EXISTS module_versions (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    module_id TEXT NOT NULL,
    version TEXT NOT NULL CHECK (version <> ''),
    source_uri TEXT NOT NULL CHECK (source_uri <> ''),
    checksum TEXT NOT NULL CHECK (checksum <> ''),
    selection_base_score REAL NOT NULL CHECK (
        selection_base_score >= 0
        AND selection_base_score <= 1
    ),
    created_at TEXT NOT NULL CHECK (created_at <> ''),
    FOREIGN KEY (module_id) REFERENCES modules (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_module_versions_module_version
    ON module_versions (module_id, version);

CREATE TABLE IF NOT EXISTS module_dependencies (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    module_version_id TEXT NOT NULL,
    dependency_kind TEXT NOT NULL CHECK (
        dependency_kind IN (
            'skill',
            'instruction',
            'tool',
            'knowledge_scope',
            'data_scope',
            'memory_scope',
            'policy',
            'validator'
        )
    ),
    dependency_id TEXT NOT NULL,
    is_required INTEGER NOT NULL CHECK (is_required IN (0, 1)),
    FOREIGN KEY (module_version_id) REFERENCES module_versions (id),
    FOREIGN KEY (dependency_id) REFERENCES modules (id)
);

CREATE INDEX IF NOT EXISTS idx_module_dependencies_module_version
    ON module_dependencies (module_version_id);

CREATE INDEX IF NOT EXISTS idx_module_dependencies_dependency
    ON module_dependencies (dependency_kind, dependency_id);

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    name TEXT NOT NULL CHECK (name <> ''),
    source_type TEXT NOT NULL CHECK (source_type IN ('repo', 'notion', 'r2', 'url', 'manual')),
    uri TEXT NOT NULL CHECK (uri <> ''),
    owner TEXT NOT NULL CHECK (owner <> ''),
    sensitivity TEXT NOT NULL CHECK (
        sensitivity IN ('public', 'internal', 'confidential', 'secret')
    ),
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'deprecated', 'deleted'))
);

CREATE INDEX IF NOT EXISTS idx_knowledge_sources_type_status
    ON knowledge_sources (source_type, status);

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    source_id TEXT NOT NULL,
    version TEXT NOT NULL CHECK (version <> ''),
    content_uri TEXT NOT NULL CHECK (content_uri <> ''),
    manifest_uri TEXT NOT NULL CHECK (manifest_uri <> ''),
    checksum TEXT NOT NULL CHECK (checksum <> ''),
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'deprecated', 'deleted')),
    FOREIGN KEY (source_id) REFERENCES knowledge_sources (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_documents_source_version
    ON knowledge_documents (source_id, version);

CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status
    ON knowledge_documents (status);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content_uri TEXT NOT NULL CHECK (content_uri <> ''),
    vector_id TEXT NOT NULL UNIQUE CHECK (vector_id <> ''),
    scope_id TEXT NOT NULL,
    token_count INTEGER NOT NULL CHECK (token_count >= 1),
    FOREIGN KEY (document_id) REFERENCES knowledge_documents (id),
    FOREIGN KEY (scope_id) REFERENCES modules (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_chunks_document_index
    ON knowledge_chunks (document_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
    ON knowledge_chunks (document_id);

CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_scope
    ON knowledge_chunks (scope_id);

CREATE TABLE IF NOT EXISTS memory_records (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    memory_scope_id TEXT NOT NULL,
    version TEXT NOT NULL CHECK (version <> ''),
    content_uri TEXT NOT NULL CHECK (content_uri <> ''),
    manifest_uri TEXT NOT NULL CHECK (manifest_uri <> ''),
    source_run_id TEXT NOT NULL CHECK (source_run_id <> ''),
    source_profile_id TEXT NOT NULL CHECK (source_profile_id <> ''),
    sensitivity TEXT NOT NULL CHECK (
        sensitivity IN ('public', 'internal', 'confidential', 'secret')
    ),
    retention_policy TEXT NOT NULL CHECK (retention_policy <> ''),
    status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'deprecated', 'deleted')),
    FOREIGN KEY (memory_scope_id) REFERENCES modules (id)
);

CREATE INDEX IF NOT EXISTS idx_memory_records_scope_status
    ON memory_records (memory_scope_id, status);

CREATE INDEX IF NOT EXISTS idx_memory_records_source_run
    ON memory_records (source_run_id);

CREATE TABLE IF NOT EXISTS scope_bindings (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    scope_id TEXT NOT NULL,
    scope_kind TEXT NOT NULL CHECK (
        scope_kind IN ('knowledge_scope', 'data_scope', 'memory_scope')
    ),
    principal_kind TEXT NOT NULL CHECK (principal_kind IN ('role', 'user', 'service')),
    principal_id TEXT NOT NULL CHECK (principal_id <> ''),
    policy_id TEXT NOT NULL,
    effect TEXT NOT NULL CHECK (effect IN ('allow', 'deny')),
    FOREIGN KEY (scope_id) REFERENCES modules (id),
    FOREIGN KEY (policy_id) REFERENCES modules (id)
);

CREATE INDEX IF NOT EXISTS idx_scope_bindings_scope_principal
    ON scope_bindings (scope_kind, scope_id, principal_kind, principal_id);

CREATE INDEX IF NOT EXISTS idx_scope_bindings_policy
    ON scope_bindings (policy_id);

CREATE TABLE IF NOT EXISTS policy_bindings (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    policy_id TEXT NOT NULL,
    target_kind TEXT NOT NULL CHECK (
        target_kind IN (
            'module',
            'knowledge_source',
            'knowledge_document',
            'memory_record',
            'scope'
        )
    ),
    target_id TEXT NOT NULL CHECK (target_id <> ''),
    effect TEXT NOT NULL CHECK (effect IN ('allow', 'deny')),
    priority INTEGER NOT NULL CHECK (priority >= 0),
    FOREIGN KEY (policy_id) REFERENCES modules (id)
);

CREATE INDEX IF NOT EXISTS idx_policy_bindings_policy_target
    ON policy_bindings (policy_id, target_kind, target_id);

CREATE INDEX IF NOT EXISTS idx_policy_bindings_target_priority
    ON policy_bindings (target_kind, target_id, priority);

CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    job_type TEXT NOT NULL CHECK (
        job_type IN ('knowledge_import', 'memory_import', 'embedding_update', 'audit_archive')
    ),
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    source_uri TEXT NOT NULL CHECK (source_uri <> ''),
    target_kind TEXT NOT NULL CHECK (
        target_kind IN ('knowledge_document', 'memory_record', 'audit_archive')
    ),
    target_id TEXT NOT NULL CHECK (target_id <> ''),
    attempts INTEGER NOT NULL CHECK (attempts >= 0),
    created_at TEXT NOT NULL CHECK (created_at <> ''),
    updated_at TEXT NOT NULL CHECK (updated_at <> '')
);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status_type
    ON ingestion_jobs (status, job_type);

CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_target
    ON ingestion_jobs (target_kind, target_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    event_type TEXT NOT NULL CHECK (event_type <> ''),
    actor_id TEXT NOT NULL CHECK (actor_id <> ''),
    target_kind TEXT NOT NULL CHECK (target_kind <> ''),
    target_id TEXT NOT NULL CHECK (target_id <> ''),
    created_at TEXT NOT NULL CHECK (created_at <> ''),
    retention_policy TEXT NOT NULL CHECK (retention_policy <> ''),
    archive_after TEXT NOT NULL CHECK (archive_after <> ''),
    archive_uri TEXT CHECK (archive_uri IS NULL OR archive_uri <> '')
);

CREATE INDEX IF NOT EXISTS idx_audit_events_archive_after
    ON audit_events (archive_after);

CREATE INDEX IF NOT EXISTS idx_audit_events_target
    ON audit_events (target_kind, target_id);

CREATE INDEX IF NOT EXISTS idx_audit_events_created_at
    ON audit_events (created_at);
