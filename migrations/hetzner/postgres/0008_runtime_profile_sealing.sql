ALTER TABLE runtime.runtime_runs
    ADD COLUMN IF NOT EXISTS profile_artifact_uri TEXT;

ALTER TABLE runtime.runtime_runs
    ADD COLUMN IF NOT EXISTS profile_sha256 TEXT CHECK (
        profile_sha256 IS NULL OR profile_sha256 ~ '^[a-f0-9]{64}$'
    );

ALTER TABLE runtime.runtime_runs
    ADD COLUMN IF NOT EXISTS profile_generation INTEGER CHECK (
        profile_generation IS NULL OR profile_generation >= 1
    );

ALTER TABLE runtime.runtime_runs
    ADD COLUMN IF NOT EXISTS parent_profile_id TEXT CHECK (
        parent_profile_id IS NULL OR parent_profile_id ~ '^[a-z][a-z0-9-]*$'
    );

CREATE INDEX IF NOT EXISTS idx_runtime_runs_profile_hash
    ON runtime.runtime_runs (profile_sha256)
    WHERE profile_sha256 IS NOT NULL;
