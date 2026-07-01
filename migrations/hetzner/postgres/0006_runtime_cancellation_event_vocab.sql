ALTER TABLE runtime.runtime_events
    DROP CONSTRAINT IF EXISTS runtime_events_event_type_check;

ALTER TABLE runtime.runtime_events
    ADD CONSTRAINT runtime_events_event_type_check CHECK (
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
    );

ALTER TABLE runtime.runtime_events
    DROP CONSTRAINT IF EXISTS runtime_events_actor_role_check;

ALTER TABLE runtime.runtime_events
    ADD CONSTRAINT runtime_events_actor_role_check CHECK (
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
    );
