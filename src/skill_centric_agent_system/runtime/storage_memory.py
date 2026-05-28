from __future__ import annotations

from collections.abc import Mapping
from threading import Lock
from typing import Any, cast


class InMemoryRuntimeStore:
    """Runtime store used by tests and local entrypoint dry-runs."""

    def __init__(self) -> None:
        self.runtime_runs: dict[str, dict[str, Any]] = {}
        self.runtime_steps: dict[str, dict[str, Any]] = {}
        self.runtime_events: list[dict[str, Any]] = []
        self.runtime_checkpoints: list[dict[str, Any]] = []
        self.tool_invocations: list[dict[str, Any]] = []
        self.validation_results: list[dict[str, Any]] = []
        self.memory_candidates: list[dict[str, Any]] = []
        self._lock = Lock()
        self._event_indices: dict[str, int] = {}
        self._checkpoint_indices: dict[str, int] = {}

    def insert_runtime_run(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.runtime_runs[stored["id"]] = stored
        return stored

    def update_runtime_run(self, run_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = self.runtime_runs[run_id]
        stored.update(fields)
        return stored

    def get_runtime_run(self, run_id: str) -> Mapping[str, Any] | None:
        return self.runtime_runs.get(run_id)

    def insert_runtime_step(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        idempotency_key = record.get("idempotency_key")
        if idempotency_key is not None:
            existing = self._find_by_run_idempotency(
                self.runtime_steps.values(),
                str(record["run_id"]),
                str(idempotency_key),
            )
            if existing is not None:
                return existing

        stored = dict(record)
        self.runtime_steps[stored["id"]] = stored
        return stored

    def update_runtime_step(self, step_id: str, fields: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = self.runtime_steps[step_id]
        stored.update(fields)
        return stored

    def allocate_runtime_event_index(self, run_id: str) -> int:
        with self._lock:
            next_index = self._event_indices.get(run_id)
            if next_index is None:
                existing_indices = [
                    int(event["event_index"])
                    for event in self.runtime_events
                    if event["run_id"] == run_id
                ]
                next_index = max(existing_indices, default=-1) + 1
            self._event_indices[run_id] = next_index + 1
            return next_index

    def insert_runtime_event(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        with self._lock:
            existing = self._find_by_run_idempotency(
                self.runtime_events,
                str(record["run_id"]),
                str(record["idempotency_key"]),
            )
            if existing is not None:
                return existing

            stored = dict(record)
            self.runtime_events.append(stored)
            return stored

    def allocate_runtime_checkpoint_index(self, run_id: str) -> int:
        with self._lock:
            next_index = self._checkpoint_indices.get(run_id)
            if next_index is None:
                existing_indices = [
                    int(checkpoint["checkpoint_index"])
                    for checkpoint in self.runtime_checkpoints
                    if checkpoint["run_id"] == run_id
                ]
                next_index = max(existing_indices, default=-1) + 1
            self._checkpoint_indices[run_id] = next_index + 1
            return next_index

    def insert_runtime_checkpoint(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        with self._lock:
            existing = self._find_by_run_index(
                self.runtime_checkpoints,
                str(record["run_id"]),
                int(record["checkpoint_index"]),
                "checkpoint_index",
            )
            if existing is not None:
                return existing

            stored = dict(record)
            self.runtime_checkpoints.append(stored)
            return stored

    def insert_tool_invocation(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.tool_invocations.append(stored)
        return stored

    def insert_validation_result(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.validation_results.append(stored)
        return stored

    def insert_memory_candidate(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        stored = dict(record)
        self.memory_candidates.append(stored)
        return stored

    def update_memory_candidate(
        self,
        candidate_id: str,
        fields: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        for candidate in self.memory_candidates:
            if candidate["id"] == candidate_id:
                candidate.update(fields)
                return candidate
        raise KeyError(candidate_id)

    def events_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(event for event in self.runtime_events if event["run_id"] == run_id)

    def checkpoints_for_run(self, run_id: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            checkpoint
            for checkpoint in self.runtime_checkpoints
            if checkpoint["run_id"] == run_id
        )

    def as_runtime_plane_recordset(
        self,
        *,
        contract_version: str = "0.2.0",
        environment: str = "dev",
    ) -> dict[str, Any]:
        return {
            "contract_version": contract_version,
            "environment": environment,
            "records": {
                "runtime_runs": list(self.runtime_runs.values()),
                "runtime_steps": list(self.runtime_steps.values()),
                "runtime_events": list(self.runtime_events),
                "runtime_checkpoints": list(self.runtime_checkpoints),
                "tool_invocations": list(self.tool_invocations),
                "validation_results": list(self.validation_results),
                "memory_candidates": list(self.memory_candidates),
            },
        }

    @staticmethod
    def _find_by_run_idempotency(
        records: Any,
        run_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any] | None:
        for record in records:
            if record["run_id"] == run_id and record.get("idempotency_key") == idempotency_key:
                return cast(Mapping[str, Any], record)
        return None

    @staticmethod
    def _find_by_run_index(
        records: Any,
        run_id: str,
        index: int,
        index_field: str,
    ) -> Mapping[str, Any] | None:
        for record in records:
            if record["run_id"] == run_id and record[index_field] == index:
                return cast(Mapping[str, Any], record)
        return None

