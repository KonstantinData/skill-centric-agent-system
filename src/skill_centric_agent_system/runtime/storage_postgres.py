from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class PostgresRuntimeStore:
    """Postgres adapter for the Hetzner runtime tables.

    The adapter accepts a DB-API/psycopg style connection and keeps transaction
    ownership with the caller. Tests can pass a fake connection without importing
    psycopg.
    """

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def insert_runtime_queue_item(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        cursor = self.connection.execute(
            """
            INSERT INTO runtime.runtime_queue_items (
                id, task_id, tenant_id, area_id, environment, queue_name, status,
                priority, scheduled_at, attempts, max_attempts, claimed_by,
                claimed_at, claimed_until, lease_expires_at, heartbeat_at,
                attempt_id, task_payload_uri, composition_context_uri, run_id,
                last_error, idempotency_key, created_at, updated_at
            )
            VALUES (
                %(id)s, %(task_id)s, %(tenant_id)s, %(area_id)s, %(environment)s,
                %(queue_name)s, %(status)s, %(priority)s, %(scheduled_at)s,
                %(attempts)s, %(max_attempts)s, %(claimed_by)s, %(claimed_at)s,
                %(claimed_until)s, %(lease_expires_at)s, %(heartbeat_at)s,
                %(attempt_id)s, %(task_payload_uri)s, %(composition_context_uri)s,
                %(run_id)s, %(last_error)s, %(idempotency_key)s, %(created_at)s,
                %(updated_at)s
            )
            ON CONFLICT (idempotency_key) DO UPDATE
            SET idempotency_key = EXCLUDED.idempotency_key
            RETURNING id, task_id, tenant_id, area_id, environment, queue_name, status,
                      priority, scheduled_at, attempts, max_attempts, claimed_by,
                      claimed_at, claimed_until, lease_expires_at, heartbeat_at,
                      attempt_id, task_payload_uri, composition_context_uri, run_id,
                      last_error, idempotency_key, created_at, updated_at
            """,
            dict(record),
        )
        row = cursor.fetchone()
        return row if row is not None else record

    def get_runtime_queue_item(self, queue_id: str) -> Mapping[str, Any] | None:
        cursor = self.connection.execute(
            """
            SELECT id, task_id, tenant_id, area_id, environment, queue_name, status,
                   priority, scheduled_at, attempts, max_attempts, claimed_by,
                   claimed_at, claimed_until, lease_expires_at, heartbeat_at,
                   attempt_id, task_payload_uri, composition_context_uri, run_id,
                   last_error, idempotency_key, created_at, updated_at
            FROM runtime.runtime_queue_items
            WHERE id = %(queue_id)s
            """,
            {"queue_id": queue_id},
        )
        row = cursor.fetchone()
        return row if row is not None else None

    def update_runtime_queue_item(
        self,
        queue_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": queue_id, **dict(fields)}
        cursor = self.connection.execute(
            f"""
            UPDATE runtime.runtime_queue_items
            SET {assignments}
            WHERE id = %(id)s
            RETURNING id, task_id, tenant_id, area_id, environment, queue_name, status,
                      priority, scheduled_at, attempts, max_attempts, claimed_by,
                      claimed_at, claimed_until, lease_expires_at, heartbeat_at,
                      attempt_id, task_payload_uri, composition_context_uri, run_id,
                      last_error, idempotency_key, created_at, updated_at
            """,
            params,
        )
        row = cursor.fetchone()
        return row if row is not None else params

    def claim_next_runtime_queue_item(
        self,
        *,
        worker_id: str,
        claimed_at: str,
        lease_expires_at: str,
        tenant_running_limits: Mapping[str, int] | None = None,
        global_running_limit: int | None = None,
        allowed_tenant_ids: tuple[str, ...] = (),
        disabled_tenant_ids: tuple[str, ...] = (),
        environment: str | None = None,
        queue_name: str | None = None,
    ) -> Mapping[str, Any] | None:
        if (
            global_running_limit is not None
            and self._global_running_count() >= global_running_limit
        ):
            return None
        cursor = self.connection.execute(
            """
            SELECT id, task_id, tenant_id, area_id, environment, queue_name, status,
                   priority, scheduled_at, attempts, max_attempts, claimed_by,
                   claimed_at, claimed_until, lease_expires_at, heartbeat_at,
                   attempt_id, task_payload_uri, composition_context_uri, run_id,
                   last_error, idempotency_key, created_at, updated_at
            FROM runtime.runtime_queue_items
            WHERE status IN ('queued', 'retry_scheduled')
              AND scheduled_at <= %(claimed_at)s
              AND attempts < max_attempts
              AND (%(environment)s IS NULL OR environment = %(environment)s)
              AND (%(queue_name)s IS NULL OR queue_name = %(queue_name)s)
              AND NOT (tenant_id = ANY(%(disabled_tenant_ids)s))
              AND (
                  cardinality(%(allowed_tenant_ids)s::text[]) = 0
                  OR tenant_id = ANY(%(allowed_tenant_ids)s)
              )
            ORDER BY priority DESC, scheduled_at ASC, created_at ASC, id ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 20
            """,
            {
                "claimed_at": claimed_at,
                "environment": environment,
                "queue_name": queue_name,
                "allowed_tenant_ids": list(allowed_tenant_ids),
                "disabled_tenant_ids": list(disabled_tenant_ids),
            },
        )
        candidates = cursor.fetchall()
        limits = dict(tenant_running_limits or {})
        for candidate in candidates:
            tenant_id = str(candidate["tenant_id"])
            limit = limits.get(tenant_id)
            if limit is not None and self._tenant_running_count(tenant_id) >= limit:
                continue
            params = {
                "id": candidate["id"],
                "worker_id": worker_id,
                "claimed_at": claimed_at,
                "lease_expires_at": lease_expires_at,
                "attempts": int(candidate["attempts"]) + 1,
            }
            self.connection.execute(
                """
                UPDATE runtime.runtime_queue_items
                SET status = 'claiming',
                    attempts = %(attempts)s,
                    claimed_by = %(worker_id)s,
                    claimed_at = %(claimed_at)s,
                    claimed_until = %(lease_expires_at)s,
                    lease_expires_at = %(lease_expires_at)s,
                    heartbeat_at = %(claimed_at)s,
                    updated_at = %(claimed_at)s
                WHERE id = %(id)s
                """,
                params,
            )
            return {
                **dict(candidate),
                "status": "claiming",
                "attempts": params["attempts"],
                "claimed_by": worker_id,
                "claimed_at": claimed_at,
                "claimed_until": lease_expires_at,
                "lease_expires_at": lease_expires_at,
                "heartbeat_at": claimed_at,
                "updated_at": claimed_at,
            }
        return None

    def recover_stale_runtime_queue_items(self, *, now: str) -> tuple[Mapping[str, Any], ...]:
        cursor = self.connection.execute(
            """
            UPDATE runtime.runtime_queue_items
            SET status = 'retry_scheduled',
                claimed_by = NULL,
                claimed_at = NULL,
                claimed_until = NULL,
                lease_expires_at = NULL,
                heartbeat_at = NULL,
                last_error = 'Stale runtime queue claim recovered.',
                updated_at = %(now)s
            WHERE status IN ('claiming', 'running')
              AND claimed_until IS NOT NULL
              AND claimed_until <= %(now)s
            RETURNING id, task_id, tenant_id, area_id, environment, queue_name, status,
                      priority, scheduled_at, attempts, max_attempts, claimed_by,
                      claimed_at, claimed_until, lease_expires_at, heartbeat_at,
                      attempt_id, task_payload_uri, composition_context_uri, run_id,
                      last_error, idempotency_key, created_at, updated_at
            """,
            {"now": now},
        )
        return tuple(cursor.fetchall())

    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_runs (
                id, task_id, profile_id, profile_version, status, started_at,
                completed_at, artifact_root_uri, token_budget_total,
                tokens_used_total, stop_reason, profile_artifact_uri, profile_sha256,
                profile_generation, parent_profile_id
            )
            VALUES (
                %(id)s, %(task_id)s, %(profile_id)s, %(profile_version)s,
                %(status)s, %(started_at)s, %(completed_at)s,
                %(artifact_root_uri)s, %(token_budget_total)s,
                %(tokens_used_total)s, %(stop_reason)s, %(profile_artifact_uri)s,
                %(profile_sha256)s, %(profile_generation)s, %(parent_profile_id)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def update_runtime_run(self, run_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": run_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.runtime_runs SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def get_runtime_run(self, run_id: str) -> Mapping[str, Any] | None:
        cursor = self.connection.execute(
            """
            SELECT id, task_id, profile_id, profile_version, status, started_at,
                   completed_at, artifact_root_uri, token_budget_total,
                   tokens_used_total, stop_reason, profile_artifact_uri,
                   profile_sha256, profile_generation, parent_profile_id
            FROM runtime.runtime_runs
            WHERE id = %(run_id)s
            """,
            {"run_id": run_id},
        )
        row = cursor.fetchone()
        return row if row is not None else None

    def insert_runtime_run_attempt(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_run_attempts (
                id, queue_id, run_id, tenant_id, attempt_number, status, started_at,
                completed_at, stop_reason, profile_id, profile_sha256
            )
            VALUES (
                %(id)s, %(queue_id)s, %(run_id)s, %(tenant_id)s, %(attempt_number)s,
                %(status)s, %(started_at)s, %(completed_at)s, %(stop_reason)s,
                %(profile_id)s, %(profile_sha256)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def update_runtime_run_attempt(
        self,
        attempt_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": attempt_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.runtime_run_attempts SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def insert_runtime_run_claim(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_run_claims (
                id, queue_id, worker_id, tenant_id, claimed_at, claimed_until,
                heartbeat_at, released_at, release_reason
            )
            VALUES (
                %(id)s, %(queue_id)s, %(worker_id)s, %(tenant_id)s, %(claimed_at)s,
                %(claimed_until)s, %(heartbeat_at)s, %(released_at)s, %(release_reason)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def update_runtime_run_claim(
        self,
        claim_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": claim_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.runtime_run_claims SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def insert_runtime_dead_letter(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_dead_letters (
                id, queue_id, run_id, attempt_id, tenant_id, error_type,
                error_message, created_at
            )
            VALUES (
                %(id)s, %(queue_id)s, %(run_id)s, %(attempt_id)s, %(tenant_id)s,
                %(error_type)s, %(error_message)s, %(created_at)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def insert_runtime_quota_reservation(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_quota_reservations (
                id, queue_id, run_id, tenant_id, quota_window, reserved_tokens,
                reserved_tool_calls, status, created_at, finalized_at
            )
            VALUES (
                %(id)s, %(queue_id)s, %(run_id)s, %(tenant_id)s, %(quota_window)s,
                %(reserved_tokens)s, %(reserved_tool_calls)s, %(status)s,
                %(created_at)s, %(finalized_at)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def update_runtime_quota_reservation(
        self,
        reservation_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": reservation_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.runtime_quota_reservations SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def insert_runtime_step(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_steps (
                id, run_id, step_index, kind, status, started_at, completed_at,
                stop_reason, token_budget, tokens_used, idempotency_key, attempt
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_index)s, %(kind)s, %(status)s,
                %(started_at)s, %(completed_at)s, %(stop_reason)s,
                %(token_budget)s, %(tokens_used)s, %(idempotency_key)s,
                %(attempt)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def update_runtime_step(self, step_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": step_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.runtime_steps SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def allocate_runtime_event_index(self, run_id: str) -> int:
        self.connection.execute(
            "SELECT id FROM runtime.runtime_runs WHERE id = %(run_id)s FOR UPDATE",
            {"run_id": run_id},
        )
        cursor = self.connection.execute(
            """
            SELECT COALESCE(MAX(event_index) + 1, 0) AS next_event_index
            FROM runtime.runtime_events
            WHERE run_id = %(run_id)s
            """,
            {"run_id": run_id},
        )
        row = cursor.fetchone()
        if row is None:
            return 0
        return int(row["next_event_index"])

    def insert_runtime_event(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_events (
                id, run_id, step_id, event_index, event_type, actor_role,
                planned_action_uri, execution_uri, result_uri, stop_reason,
                idempotency_key, created_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_id)s, %(event_index)s,
                %(event_type)s, %(actor_role)s, %(planned_action_uri)s,
                %(execution_uri)s, %(result_uri)s, %(stop_reason)s,
                %(idempotency_key)s, %(created_at)s
            )
            ON CONFLICT (run_id, idempotency_key) DO NOTHING
            """,
            dict(record),
        )
        return record

    def allocate_runtime_checkpoint_index(self, run_id: str) -> int:
        self.connection.execute(
            "SELECT id FROM runtime.runtime_runs WHERE id = %(run_id)s FOR UPDATE",
            {"run_id": run_id},
        )
        cursor = self.connection.execute(
            """
            SELECT COALESCE(MAX(checkpoint_index) + 1, 0) AS next_checkpoint_index
            FROM runtime.runtime_checkpoints
            WHERE run_id = %(run_id)s
            """,
            {"run_id": run_id},
        )
        row = cursor.fetchone()
        if row is None:
            return 0
        return int(row["next_checkpoint_index"])

    def insert_runtime_checkpoint(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_checkpoints (
                id, run_id, step_id, checkpoint_index, phase, state_uri,
                tokens_used_total, created_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_id)s, %(checkpoint_index)s,
                %(phase)s, %(state_uri)s, %(tokens_used_total)s, %(created_at)s
            )
            ON CONFLICT (run_id, checkpoint_index) DO NOTHING
            """,
            dict(record),
        )
        return record

    def insert_tool_invocation(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.tool_invocations (
                id, run_id, step_id, tool_name, status, input_uri, output_uri,
                started_at, completed_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_id)s, %(tool_name)s, %(status)s,
                %(input_uri)s, %(output_uri)s, %(started_at)s, %(completed_at)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def insert_validation_result(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.validation_results (
                id, run_id, step_id, validator_id, status, findings_uri, created_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(step_id)s, %(validator_id)s, %(status)s,
                %(findings_uri)s, %(created_at)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            dict(record),
        )
        return record

    def insert_memory_candidate(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.memory_candidates (
                id, run_id, profile_id, source_step_id, target_memory_scope_id,
                candidate_class, classification_reason, content_uri, sensitivity,
                retention_policy, validator_status, validator_id, validation_reason,
                policy_status, policy_id, policy_reason, created_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(profile_id)s, %(source_step_id)s,
                %(target_memory_scope_id)s, %(candidate_class)s,
                %(classification_reason)s, %(content_uri)s, %(sensitivity)s,
                %(retention_policy)s, %(validator_status)s, %(validator_id)s,
                %(validation_reason)s, %(policy_status)s, %(policy_id)s,
                %(policy_reason)s, %(created_at)s
            )
            ON CONFLICT (id) DO NOTHING
            """,
            {
                "validation_reason": None,
                "policy_reason": None,
                **dict(record),
            },
        )
        return record

    def update_memory_candidate(
        self,
        candidate_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        assignments = ", ".join(f"{field} = %({field})s" for field in fields)
        params = {"id": candidate_id, **dict(fields)}
        self.connection.execute(
            f"UPDATE runtime.memory_candidates SET {assignments} WHERE id = %(id)s",
            params,
        )
        return params

    def events_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        cursor = self.connection.execute(
            """
            SELECT id, run_id, step_id, event_index, event_type, actor_role,
                   planned_action_uri, execution_uri, result_uri, stop_reason,
                   idempotency_key, created_at
            FROM runtime.runtime_events
            WHERE run_id = %(run_id)s
            ORDER BY event_index
            """,
            {"run_id": run_id},
        )
        return tuple(cursor.fetchall())

    def checkpoints_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        cursor = self.connection.execute(
            """
            SELECT id, run_id, step_id, checkpoint_index, phase, state_uri,
                   tokens_used_total, created_at
            FROM runtime.runtime_checkpoints
            WHERE run_id = %(run_id)s
            ORDER BY checkpoint_index
            """,
            {"run_id": run_id},
        )
        return tuple(cursor.fetchall())

    def as_runtime_plane_recordset(
        self,
        *,
        contract_version: str = "0.2.0",
        environment: str = "dev",
    ) -> Mapping[str, Any]:
        return {
            "contract_version": contract_version,
            "environment": environment,
            "records": {
                "runtime_queue_items": self._fetch_all(
                    """
                    SELECT id, task_id, tenant_id, area_id, environment, queue_name,
                           status, priority, scheduled_at, attempts, max_attempts,
                           claimed_by, claimed_at, claimed_until, lease_expires_at,
                           heartbeat_at, attempt_id, task_payload_uri,
                           composition_context_uri, run_id, last_error,
                           idempotency_key, created_at, updated_at
                    FROM runtime.runtime_queue_items
                    ORDER BY scheduled_at, priority DESC, id
                    """
                ),
                "runtime_run_attempts": self._fetch_all(
                    """
                    SELECT id, queue_id, run_id, tenant_id, attempt_number, status,
                           started_at, completed_at, stop_reason, profile_id,
                           profile_sha256
                    FROM runtime.runtime_run_attempts
                    ORDER BY started_at, id
                    """
                ),
                "runtime_run_claims": self._fetch_all(
                    """
                    SELECT id, queue_id, worker_id, tenant_id, claimed_at,
                           claimed_until, heartbeat_at, released_at, release_reason
                    FROM runtime.runtime_run_claims
                    ORDER BY claimed_at, id
                    """
                ),
                "runtime_dead_letters": self._fetch_all(
                    """
                    SELECT id, queue_id, run_id, attempt_id, tenant_id, error_type,
                           error_message, created_at
                    FROM runtime.runtime_dead_letters
                    ORDER BY created_at, id
                    """
                ),
                "runtime_quota_reservations": self._fetch_all(
                    """
                    SELECT id, queue_id, run_id, tenant_id, quota_window,
                           reserved_tokens, reserved_tool_calls, status, created_at,
                           finalized_at
                    FROM runtime.runtime_quota_reservations
                    ORDER BY created_at, id
                    """
                ),
                "runtime_runs": self._fetch_all(
                    """
                    SELECT id, task_id, profile_id, profile_version, status,
                           started_at, completed_at, artifact_root_uri,
                           token_budget_total, tokens_used_total, stop_reason,
                           profile_artifact_uri, profile_sha256, profile_generation,
                           parent_profile_id
                    FROM runtime.runtime_runs
                    ORDER BY started_at, id
                    """
                ),
                "runtime_steps": self._fetch_all(
                    """
                    SELECT id, run_id, step_index, kind, status, started_at,
                           completed_at, stop_reason, token_budget, tokens_used,
                           idempotency_key, attempt
                    FROM runtime.runtime_steps
                    ORDER BY run_id, step_index
                    """
                ),
                "runtime_events": self._fetch_all(
                    """
                    SELECT id, run_id, step_id, event_index, event_type, actor_role,
                           planned_action_uri, execution_uri, result_uri, stop_reason,
                           idempotency_key, created_at
                    FROM runtime.runtime_events
                    ORDER BY run_id, event_index
                    """
                ),
                "runtime_checkpoints": self._fetch_all(
                    """
                    SELECT id, run_id, step_id, checkpoint_index, phase, state_uri,
                           tokens_used_total, created_at
                    FROM runtime.runtime_checkpoints
                    ORDER BY run_id, checkpoint_index
                    """
                ),
                "tool_invocations": self._fetch_all(
                    """
                    SELECT id, run_id, step_id, tool_name, status, input_uri,
                           output_uri, started_at, completed_at
                    FROM runtime.tool_invocations
                    ORDER BY run_id, started_at, id
                    """
                ),
                "validation_results": self._fetch_all(
                    """
                    SELECT id, run_id, step_id, validator_id, status, findings_uri,
                           created_at
                    FROM runtime.validation_results
                    ORDER BY run_id, created_at, id
                    """
                ),
                "memory_candidates": self._fetch_all(
                    """
                    SELECT id, run_id, profile_id, source_step_id,
                           target_memory_scope_id, candidate_class,
                           classification_reason, content_uri, sensitivity,
                           retention_policy, validator_status, validator_id,
                           validation_reason, policy_status, policy_id,
                           policy_reason, created_at
                    FROM runtime.memory_candidates
                    ORDER BY run_id, created_at, id
                    """
                ),
            },
        }

    def _fetch_all(self, sql: str) -> list[Mapping[str, Any]]:
        cursor = self.connection.execute(sql)
        return list(cursor.fetchall())

    def _tenant_running_count(self, tenant_id: str) -> int:
        cursor = self.connection.execute(
            """
            SELECT COUNT(*) AS running_count
            FROM runtime.runtime_queue_items
            WHERE tenant_id = %(tenant_id)s
              AND status IN ('claiming', 'running')
            """,
            {"tenant_id": tenant_id},
        )
        row = cursor.fetchone()
        if row is None:
            return 0
        return int(row["running_count"])

    def _global_running_count(self) -> int:
        cursor = self.connection.execute(
            """
            SELECT COUNT(*) AS running_count
            FROM runtime.runtime_queue_items
            WHERE status IN ('claiming', 'running')
            """
        )
        row = cursor.fetchone()
        if row is None:
            return 0
        return int(row["running_count"])

