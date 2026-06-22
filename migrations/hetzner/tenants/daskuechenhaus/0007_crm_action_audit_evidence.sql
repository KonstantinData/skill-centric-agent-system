ALTER TABLE app.communication_events
  ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT 'daskuechenhaus',
  ADD COLUMN IF NOT EXISTS skill_pack_id TEXT,
  ADD COLUMN IF NOT EXISTS selected_module_ids TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  ADD COLUMN IF NOT EXISTS validator_results_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS confirmation_status TEXT,
  ADD COLUMN IF NOT EXISTS action_result_json JSONB,
  ADD COLUMN IF NOT EXISTS role_context_json JSONB NOT NULL DEFAULT '{}'::jsonb;

DO $$
BEGIN
  ALTER TABLE app.communication_events
    ADD CONSTRAINT communication_events_tenant_id_not_blank
    CHECK (btrim(tenant_id) <> '');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
  ALTER TABLE app.communication_events
    ADD CONSTRAINT communication_events_confirmation_status
    CHECK (
      confirmation_status IS NULL
      OR confirmation_status IN ('not_required', 'pending', 'accepted', 'rejected')
    );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS communication_events_skill_pack_idx
  ON app.communication_events (skill_pack_id, occurred_at DESC)
  WHERE skill_pack_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS communication_events_tenant_idx
  ON app.communication_events (tenant_id, occurred_at DESC);
