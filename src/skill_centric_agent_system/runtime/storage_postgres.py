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

    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        self.connection.execute(
            """
            INSERT INTO runtime.runtime_runs (
                id, task_id, profile_id, profile_version, status, started_at,
                completed_at, artifact_root_uri, token_budget_total,
                tokens_used_total, stop_reason
            )
            VALUES (
                %(id)s, %(task_id)s, %(profile_id)s, %(profile_version)s,
                %(status)s, %(started_at)s, %(completed_at)s,
                %(artifact_root_uri)s, %(token_budget_total)s,
                %(tokens_used_total)s, %(stop_reason)s
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
                   tokens_used_total, stop_reason
            FROM runtime.runtime_runs
            WHERE id = %(run_id)s
            """,
            {"run_id": run_id},
        )
        row = cursor.fetchone()
        return row if row is not None else None

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
                content_uri, sensitivity, retention_policy, validator_status,
                validator_id, validation_reason, policy_status, policy_id,
                policy_reason, created_at
            )
            VALUES (
                %(id)s, %(run_id)s, %(profile_id)s, %(source_step_id)s,
                %(target_memory_scope_id)s, %(content_uri)s, %(sensitivity)s,
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
                "runtime_runs": self._fetch_all(
                    """
                    SELECT id, task_id, profile_id, profile_version, status,
                           started_at, completed_at, artifact_root_uri,
                           token_budget_total, tokens_used_total, stop_reason
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
                           target_memory_scope_id, content_uri, sensitivity,
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

