ALTER TABLE runtime.memory_candidates
    ADD COLUMN IF NOT EXISTS validation_reason TEXT;

ALTER TABLE runtime.memory_candidates
    ADD COLUMN IF NOT EXISTS policy_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_memory_candidates_validation_status
    ON runtime.memory_candidates (validator_status, policy_status, created_at);
