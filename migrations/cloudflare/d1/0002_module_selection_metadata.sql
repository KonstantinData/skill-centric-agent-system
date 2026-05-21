PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS module_selection_metadata (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    module_version_id TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL CHECK (description <> ''),
    capability_class TEXT NOT NULL CHECK (
        capability_class IN (
            'analysis',
            'planning',
            'execution',
            'retrieval',
            'validation',
            'policy',
            'instruction',
            'tool_access',
            'knowledge_access',
            'data_access',
            'memory_access',
            'context'
        )
    ),
    domain_tags_json TEXT NOT NULL CHECK (json_valid(domain_tags_json)),
    task_types_json TEXT NOT NULL CHECK (json_valid(task_types_json)),
    risk_levels_json TEXT NOT NULL CHECK (json_valid(risk_levels_json)),
    task_domains_json TEXT NOT NULL CHECK (json_valid(task_domains_json)),
    required_inputs_json TEXT NOT NULL CHECK (json_valid(required_inputs_json)),
    phrases_json TEXT NOT NULL CHECK (json_valid(phrases_json)),
    negative_phrases_json TEXT NOT NULL CHECK (json_valid(negative_phrases_json)),
    triggers_json TEXT NOT NULL CHECK (json_valid(triggers_json)),
    inputs_json TEXT NOT NULL CHECK (json_valid(inputs_json)),
    outputs_json TEXT NOT NULL CHECK (json_valid(outputs_json)),
    score_modifiers_json TEXT NOT NULL CHECK (json_valid(score_modifiers_json)),
    requires_all_policies INTEGER NOT NULL CHECK (requires_all_policies IN (0, 1)),
    FOREIGN KEY (module_version_id) REFERENCES module_versions (id)
);

CREATE INDEX IF NOT EXISTS idx_module_selection_metadata_capability
    ON module_selection_metadata (capability_class);

