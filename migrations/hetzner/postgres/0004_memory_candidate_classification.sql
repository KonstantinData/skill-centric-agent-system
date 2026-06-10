ALTER TABLE runtime.memory_candidates
    ADD COLUMN IF NOT EXISTS candidate_class TEXT;

ALTER TABLE runtime.memory_candidates
    ADD COLUMN IF NOT EXISTS classification_reason TEXT;

UPDATE runtime.memory_candidates
SET
    candidate_class = COALESCE(candidate_class, 'procedural_lesson'),
    classification_reason = COALESCE(
        classification_reason,
        'Backfilled as procedural_lesson for pre-classification memory candidates.'
    );

ALTER TABLE runtime.memory_candidates
    ALTER COLUMN candidate_class SET NOT NULL;

ALTER TABLE runtime.memory_candidates
    ALTER COLUMN classification_reason SET NOT NULL;

ALTER TABLE runtime.memory_candidates
    ADD CONSTRAINT memory_candidates_candidate_class_check
    CHECK (
        candidate_class IN (
            'procedural_lesson',
            'task_subject_fact',
            'runtime_evidence',
            'knowledge_record_proposal',
            'rejected'
        )
    );

CREATE INDEX IF NOT EXISTS idx_memory_candidates_class_status
    ON runtime.memory_candidates (
        candidate_class,
        validator_status,
        policy_status,
        created_at
    );
