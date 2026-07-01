from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MinimalRuntimeLoop,
    PostgresRuntimeStore,
    RuntimeApiPrincipal,
    RuntimeApiService,
    RuntimeEntryPoint,
    RuntimeLoopError,
    RuntimeQueueConfig,
    RuntimeQueueError,
    RuntimeQueueManager,
    RuntimeQueueWorker,
    runtime_queue_metrics,
)
from skill_centric_agent_system.runtime.cli import (
    _queue_worker_iteration_boundary,
)
from skill_centric_agent_system.runtime.cli import (
    main as runtime_cli_main,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "code-review-task.json"
TENANT_TASK_EXAMPLE_PATH = REPO_ROOT / "examples" / "tasks" / "tenant-research-task.json"
COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response.json"
)
TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-tenant-research.json"
)
RUNTIME_PLANE_SCHEMA_PATH = REPO_ROOT / "schemas" / "hetzner-runtime-plane.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inactive_tenant_context_response() -> dict[str, Any]:
    response = json.loads(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH.read_text(encoding="utf-8"))
    response["tenant_authority"]["status"] = "disabled"
    return response


def mismatched_tenant_context_response() -> dict[str, Any]:
    response = json.loads(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH.read_text(encoding="utf-8"))
    response["tenant_authority"]["tenant_id"] = "other-tenant"
    return response


def mismatched_area_context_response() -> dict[str, Any]:
    response = json.loads(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH.read_text(encoding="utf-8"))
    response["tenant_authority"]["area_id"] = "other-area"
    return response


def tenant_task(task_id: str, *, tenant_id: str = "demo-tenant") -> dict[str, Any]:
    return {
        "id": task_id,
        "objective": "Research the tenant website and summarize current context.",
        "context": {
            "auth": {
                "principal_id": "tenant-user",
                "tenant_id": tenant_id,
                "area_id": tenant_id,
                "tenant_hostname": f"{tenant_id}.example.invalid",
                "membership_id": f"{tenant_id}-membership-user",
                "roles": [f"{tenant_id}-researcher"],
                "control_plane_principal_kind": "user",
                "control_plane_principal_id": "tenant-user",
                "role_data_sources": [f"{tenant_id}-website"],
                "role_capabilities": ["research"],
            }
        },
    }


def tenant_runtime_task() -> dict[str, Any]:
    return tenant_task("task-demo-tenant-research")


def test_runtime_queue_worker_processes_queued_run(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    manager = RuntimeQueueManager(store=store, artifacts=artifacts)
    queue_item = manager.enqueue(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
        idempotency_key="code-review-once",
    )

    result = RuntimeQueueWorker(
        worker_id="worker-a",
        store=store,
        artifacts=artifacts,
        repository_root=str(REPO_ROOT),
    ).process_one()

    assert result is not None
    assert result.queue_id == queue_item["id"]
    assert result.status == "succeeded"
    assert result.run_id == "run-task-demo-tenant-research-attempt-1"
    assert store.runtime_queue_items[queue_item["id"]]["status"] == "succeeded"
    assert store.runtime_runs[result.run_id]["status"] == "succeeded"
    assert result.attempt_id is not None
    assert store.runtime_run_attempts[result.attempt_id]["status"] == "succeeded"
    assert store.runtime_run_claims
    assert store.runtime_quota_reservations
    assert store.runtime_runs[result.run_id]["profile_sha256"]

    recordset = store.as_runtime_plane_recordset()
    Draft202012Validator(load_json(RUNTIME_PLANE_SCHEMA_PATH)).validate(recordset)


def test_runtime_queue_worker_loop_honors_stop_requested(tmp_path: Path, monkeypatch: Any) -> None:
    store = InMemoryRuntimeStore()
    worker = RuntimeQueueWorker(
        worker_id="worker-a",
        store=store,
        artifacts=JsonArtifactStore(tmp_path),
        repository_root=str(REPO_ROOT),
    )
    calls = 0

    def process_one() -> None:
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(worker, "process_one", process_one)

    iteration_errors: list[BaseException | None] = []

    worker.run_forever(
        poll_interval_seconds=0,
        stop_requested=lambda: calls >= 1,
        after_iteration=iteration_errors.append,
    )

    assert calls == 1
    assert iteration_errors == [None]


def test_queue_worker_iteration_boundary_commits_and_rolls_back() -> None:
    class FakeConnection:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        def commit(self) -> None:
            self.commits += 1

        def rollback(self) -> None:
            self.rollbacks += 1

    class FakeStorage:
        def __init__(self) -> None:
            self.connection = FakeConnection()

    storage = FakeStorage()
    boundary = _queue_worker_iteration_boundary(storage)

    boundary(None)
    boundary(RuntimeError("boom"))

    assert storage.connection.commits == 1
    assert storage.connection.rollbacks == 1


def test_runtime_queue_enqueue_is_idempotent(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))

    first = manager.enqueue(tenant_runtime_task(), idempotency_key="same-task")
    second = manager.enqueue(tenant_runtime_task(), idempotency_key="same-task")

    assert first == second
    assert len(store.runtime_queue_items) == 1


def test_runtime_queue_claim_respects_tenant_running_limit(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    first = manager.enqueue(tenant_task("task-demo-tenant-a"), idempotency_key="tenant-a")
    second = manager.enqueue(tenant_task("task-demo-tenant-b"), idempotency_key="tenant-b")

    claimed = manager.claim_next(
        worker_id="worker-a",
        config=RuntimeQueueConfig(tenant_running_limits={"demo-tenant": 1}),
    )
    blocked = manager.claim_next(
        worker_id="worker-b",
        config=RuntimeQueueConfig(tenant_running_limits={"demo-tenant": 1}),
    )

    assert claimed is not None
    assert claimed["id"] == first["id"]
    assert blocked is None
    assert store.runtime_queue_items[first["id"]]["status"] == "claiming"
    assert store.runtime_queue_items[second["id"]]["status"] == "queued"


def test_runtime_queue_claim_creates_attempt_and_claim_atomically(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    queue_item = manager.enqueue(tenant_runtime_task(), idempotency_key="atomic-claim")

    claim_bundle = manager.claim_next_attempt(
        worker_id="worker-a",
        config=RuntimeQueueConfig(),
    )

    assert claim_bundle is not None
    claimed_item = claim_bundle["queue_item"]
    attempt = claim_bundle["attempt"]
    claim = claim_bundle["claim"]
    assert claimed_item["id"] == queue_item["id"]
    assert claimed_item["status"] == "claiming"
    assert claimed_item["attempt_id"] == attempt["id"]
    assert claimed_item["run_id"] == attempt["run_id"]
    assert attempt["id"] in store.runtime_run_attempts
    assert claim["id"] in store.runtime_run_claims
    assert store.runtime_run_claims[claim["id"]]["released_at"] is None


def test_runtime_queue_heartbeat_updates_active_claim(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    clock_values = iter(
        [
            datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
            datetime(2026, 7, 1, 9, 1, tzinfo=UTC),
            datetime(2026, 7, 1, 9, 2, tzinfo=UTC),
        ]
    )
    manager = RuntimeQueueManager(
        store=store,
        artifacts=JsonArtifactStore(tmp_path),
        clock=lambda: next(clock_values),
    )
    queue_item = manager.enqueue(tenant_runtime_task(), idempotency_key="heartbeat-claim")
    claim_bundle = manager.claim_next_attempt(
        worker_id="worker-a",
        config=RuntimeQueueConfig(lease_seconds=300),
    )

    assert claim_bundle is not None
    claim_id = str(claim_bundle["claim"]["id"])
    manager.heartbeat(str(queue_item["id"]), config=RuntimeQueueConfig(lease_seconds=300))

    assert store.runtime_run_claims[claim_id]["heartbeat_at"] == "2026-07-01T09:02:00Z"
    assert store.runtime_run_claims[claim_id]["claimed_until"] == "2026-07-01T09:07:00Z"


def test_runtime_queue_stale_recovery_releases_active_claim(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    queue_item = manager.enqueue(tenant_runtime_task(), idempotency_key="stale-claim")
    claim_bundle = manager.claim_next_attempt(
        worker_id="worker-a",
        config=RuntimeQueueConfig(lease_seconds=1),
    )

    assert claim_bundle is not None
    claim_id = str(claim_bundle["claim"]["id"])
    recovered = store.recover_stale_runtime_queue_items(now="9999-01-01T00:00:00Z")

    assert len(recovered) == 1
    assert recovered[0]["id"] == queue_item["id"]
    assert store.runtime_run_claims[claim_id]["released_at"] == "9999-01-01T00:00:00Z"
    assert store.runtime_run_claims[claim_id]["release_reason"] == "stale_recovered"


def test_runtime_queue_worker_dead_letters_non_composable_task(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    manager = RuntimeQueueManager(store=store, artifacts=artifacts)
    queue_item = manager.enqueue(
        tenant_runtime_task(),
        composition_context_response={
            "contract_version": "0.1.0",
            "registry_version": "0.1.0",
            "composition_status": "denied",
        },
        max_attempts=1,
        idempotency_key="cannot-compose",
    )

    result = RuntimeQueueWorker(
        worker_id="worker-a",
        store=store,
        artifacts=artifacts,
        repository_root=str(REPO_ROOT),
        config=RuntimeQueueConfig(max_attempts=1),
    ).process_one()

    assert result is not None
    assert result.status == "dead_lettered"
    stored = store.runtime_queue_items[queue_item["id"]]
    assert stored["status"] == "dead_lettered"
    assert "CompositionError" in stored["last_error"]
    assert store.runtime_runs == {}


def test_runtime_loop_honors_cooperative_cancellation_checkpoint(
    tmp_path: Path,
) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    start_result = RuntimeEntryPoint(store=store, artifacts=artifacts).start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )

    result = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
        cancellation_checker=lambda _run_id: True,
    ).run(start_result)

    assert result.status == "cancelled"
    assert result.stop_reason == "cancelled"
    assert store.runtime_runs[start_result.run_id]["status"] == "cancelled"
    assert store.runtime_events[-1]["event_type"] == "runtime_cancelled"


def test_runtime_loop_revalidates_profile_seal_before_execution(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    start_result = RuntimeEntryPoint(store=store, artifacts=artifacts).start(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    tampered_profile = artifacts.read_json(start_result.profile_artifact_uri)
    tampered_profile["limits"]["max_tool_calls"] = 999
    artifacts.write_json(
        (
            "profiles",
            str(start_result.profile["id"]),
            start_result.profile_sha256,
        ),
        tampered_profile,
        redact=False,
    )

    with pytest.raises(RuntimeLoopError, match="profile artifact seal"):
        MinimalRuntimeLoop(
            store=store,
            artifacts=artifacts,
            repository_root=REPO_ROOT,
        ).run(start_result)

    assert store.runtime_steps == {}


def test_runtime_queue_cancel_updates_running_run(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    manager = RuntimeQueueManager(store=store, artifacts=artifacts)
    queue_item = manager.enqueue(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
        idempotency_key="cancel-running",
    )
    start_result = RuntimeEntryPoint(store=store, artifacts=artifacts).start(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
        run_id="run-cancel-running",
    )
    manager.mark_running(str(queue_item["id"]), run_id=start_result.run_id)

    cancelled = manager.mark_cancelled(str(queue_item["id"]))

    assert cancelled["status"] == "cancelled"
    assert store.runtime_queue_items[queue_item["id"]]["status"] == "cancelled"
    assert store.runtime_runs[start_result.run_id]["status"] == "cancelled"
    assert store.runtime_runs[start_result.run_id]["stop_reason"] == "cancelled"


def test_runtime_queue_cancel_releases_active_claim(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    queue_item = manager.enqueue(tenant_runtime_task(), idempotency_key="cancel-claim")
    claim_bundle = manager.claim_next_attempt(
        worker_id="worker-a",
        config=RuntimeQueueConfig(),
    )

    assert claim_bundle is not None
    claim_id = str(claim_bundle["claim"]["id"])
    cancelled = manager.mark_cancelled(str(queue_item["id"]))

    assert cancelled["status"] == "cancelled"
    assert cancelled["claimed_by"] is None
    assert cancelled["claimed_until"] is None
    assert store.runtime_run_claims[claim_id]["released_at"] is not None
    assert store.runtime_run_claims[claim_id]["release_reason"] == "cancelled"


def test_runtime_queue_retry_requeues_terminal_item(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    original = manager.enqueue(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
        idempotency_key="retry-source",
    )
    manager.mark_cancelled(str(original["id"]))

    retry = manager.retry(str(original["id"]))

    assert retry["id"] != original["id"]
    assert retry["status"] == "queued"
    assert retry["task_id"] == original["task_id"]
    assert retry["tenant_id"] == original["tenant_id"]
    assert retry["idempotency_key"] == "retry-source:manual-retry:1"


def test_runtime_queue_cli_enqueues_fixture_backed_task(
    tmp_path: Path,
    capsys: Any,
) -> None:
    exit_code = runtime_cli_main(
        [
            "queue",
            "enqueue",
            "--task-file",
            str(_write_task_fixture(tmp_path, tenant_runtime_task())),
            "--composition-context-file",
            str(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
            "--artifact-root",
            str(tmp_path),
            "--idempotency-key",
            "cli-enqueue",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["queue_item"]["status"] == "queued"
    assert output["queue_item"]["idempotency_key"] == "cli-enqueue"


def test_runtime_queue_cli_prints_metrics_snapshot(tmp_path: Path, capsys: Any) -> None:
    exit_code = runtime_cli_main(
        [
            "queue",
            "metrics",
            "--storage-mode",
            "memory",
            "--artifact-root",
            str(tmp_path),
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["queue_depth_by_tenant_status"] == {}
    assert output["claim_latency_seconds"]["count"] == 0


def test_runtime_api_enforces_tenant_scope_for_queue_operations(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    service = RuntimeApiService(
        store=store,
        artifacts=JsonArtifactStore(tmp_path),
        repository_root=str(REPO_ROOT),
    )
    principal = RuntimeApiPrincipal(
        principal_id="tenant-user",
        tenant_id="demo-tenant",
        area_id="demo-tenant",
    )

    response = service.start_run(
        {
            "environment": "dev",
            "task": tenant_runtime_task(),
            "composition_context_response": load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
            "execution": {"run_immediately": False},
        },
        principal=principal,
    )

    assert response["kind"] == "start_run_response"
    assert response["response_mode"] == "queued"
    assert response["queue_item"]["tenant_id"] == "demo-tenant"


def test_runtime_api_returns_result_for_immediate_run(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    service = RuntimeApiService(
        store=store,
        artifacts=JsonArtifactStore(tmp_path),
        repository_root=str(REPO_ROOT),
    )
    principal = RuntimeApiPrincipal(
        principal_id="tenant-user",
        tenant_id="demo-tenant",
        area_id="demo-tenant",
    )
    start_response = service.start_run(
        {
            "environment": "dev",
            "task": tenant_runtime_task(),
            "composition_context_response": load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
            "execution": {"run_immediately": True},
        },
        principal=principal,
    )

    run_id = str(start_response["run"]["id"])
    status = service.get_status(run_id, principal=principal)
    result = service.get_result(run_id, principal=principal)

    assert status["run"]["status"] == "succeeded"
    assert result["kind"] == "run_result_response"
    assert result["result"]["response_uri"]
    assert result["result"]["response"]["run_id"] == run_id
    assert result["result"]["response"]["status"] == "succeeded"


def test_runtime_queue_recovers_stale_claims(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    queue_item = manager.enqueue(tenant_runtime_task(), idempotency_key="stale-claim")
    claimed = manager.claim_next(worker_id="worker-a", config=RuntimeQueueConfig())
    assert claimed is not None
    store.update_runtime_queue_item(
        str(queue_item["id"]),
        {"claimed_until": "2026-07-01T09:00:00Z", "lease_expires_at": "2026-07-01T09:00:00Z"},
    )

    recovered = manager.recover_stale_claims()

    assert len(recovered) == 1
    assert store.runtime_queue_items[queue_item["id"]]["status"] == "retry_scheduled"


def test_runtime_queue_rejects_default_tenant_fallback(tmp_path: Path) -> None:
    manager = RuntimeQueueManager(
        store=InMemoryRuntimeStore(),
        artifacts=JsonArtifactStore(tmp_path),
    )

    with pytest.raises(Exception, match="explicit tenant_id"):
        manager.enqueue(load_json(TASK_EXAMPLE_PATH))


def test_runtime_queue_worker_enforces_tenant_token_quota(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    manager = RuntimeQueueManager(store=store, artifacts=artifacts)
    queue_item = manager.enqueue(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
        max_attempts=1,
        idempotency_key="quota-exhaustion",
    )

    result = RuntimeQueueWorker(
        worker_id="worker-a",
        store=store,
        artifacts=artifacts,
        repository_root=str(REPO_ROOT),
        config=RuntimeQueueConfig(
            max_attempts=1,
            tenant_token_limits_per_minute={"demo-tenant": 1},
        ),
    ).process_one()

    assert result is not None
    assert result.status == "dead_lettered"
    assert store.runtime_queue_items[queue_item["id"]]["status"] == "dead_lettered"
    assert store.runtime_events[-1]["event_type"] == "quota_exhausted"


def test_runtime_queue_counts_finalized_quota_in_same_window(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    manager = RuntimeQueueManager(store=store, artifacts=artifacts)
    first = manager.enqueue(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
        max_attempts=1,
        idempotency_key="quota-first",
    )
    second = manager.enqueue(
        tenant_runtime_task(),
        composition_context_response=load_json(TENANT_COMPOSITION_CONTEXT_RESPONSE_PATH),
        max_attempts=1,
        idempotency_key="quota-second",
    )
    config = RuntimeQueueConfig(
        max_attempts=1,
        tenant_token_limits_per_minute={"demo-tenant": 60_000},
    )

    first_result = RuntimeQueueWorker(
        worker_id="worker-a",
        store=store,
        artifacts=artifacts,
        repository_root=str(REPO_ROOT),
        config=config,
    ).process_one()
    second_result = RuntimeQueueWorker(
        worker_id="worker-b",
        store=store,
        artifacts=artifacts,
        repository_root=str(REPO_ROOT),
        config=config,
    ).process_one()

    assert first_result is not None
    assert first_result.status == "succeeded"
    assert store.runtime_queue_items[first["id"]]["status"] == "succeeded"
    assert second_result is not None
    assert second_result.status == "dead_lettered"
    assert store.runtime_queue_items[second["id"]]["status"] == "dead_lettered"
    assert store.runtime_events[-1]["event_type"] == "quota_exhausted"


def test_runtime_queue_metrics_snapshot_covers_operational_signals(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    manager = RuntimeQueueManager(store=store, artifacts=artifacts)
    manager.enqueue(tenant_task("task-metrics-queued"), idempotency_key="metrics-queued")
    claimed_item = manager.enqueue(
        tenant_task("task-metrics-claimed"),
        idempotency_key="metrics-claimed",
    )
    dead_lettered_item = manager.enqueue(
        tenant_task("task-metrics-dlq"),
        idempotency_key="metrics-dlq",
    )
    manager.claim_next_attempt(worker_id="worker-a", config=RuntimeQueueConfig())
    manager.mark_failed_or_retry(
        dead_lettered_item,
        error=RuntimeQueueError("boom"),
        config=RuntimeQueueConfig(retry_delay_seconds=0),
        run_id=None,
    )
    store.insert_runtime_dead_letter(
        {
            "id": "dlq-metrics",
            "queue_id": str(dead_lettered_item["id"]),
            "run_id": None,
            "attempt_id": None,
            "tenant_id": "demo-tenant",
            "error_type": "RuntimeQueueError",
            "error_message": "boom",
            "created_at": "2026-07-01T09:00:00Z",
        }
    )

    metrics = runtime_queue_metrics(store.as_runtime_plane_recordset())

    assert metrics["queue_depth_by_tenant_status"]["demo-tenant"]["queued"] == 1
    assert metrics["queue_depth_by_tenant_status"]["demo-tenant"]["claiming"] == 1
    assert metrics["dead_letters_by_tenant"]["demo-tenant"] == 1
    assert metrics["active_claims_by_tenant"]["demo-tenant"] == 1
    assert metrics["claim_latency_seconds"]["count"] == 1
    assert claimed_item["tenant_id"] == "demo-tenant"


def test_runtime_queue_load_smoke_claims_fairly_across_tenants(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    for index in range(1000):
        tenant_id = "tenant-a" if index % 2 == 0 else "tenant-b"
        manager.enqueue(
            tenant_task(f"task-load-{index}", tenant_id=tenant_id),
            idempotency_key=f"load-{index}",
        )

    first = manager.claim_next(
        worker_id="worker-a",
        config=RuntimeQueueConfig(tenant_running_limits={"tenant-a": 1, "tenant-b": 1}),
    )
    second = manager.claim_next(
        worker_id="worker-b",
        config=RuntimeQueueConfig(tenant_running_limits={"tenant-a": 1, "tenant-b": 1}),
    )
    third = manager.claim_next(
        worker_id="worker-c",
        config=RuntimeQueueConfig(tenant_running_limits={"tenant-a": 1, "tenant-b": 1}),
    )

    assert first is not None
    assert second is not None
    assert {first["tenant_id"], second["tenant_id"]} == {"tenant-a", "tenant-b"}
    assert third is None
    assert len(store.runtime_queue_items) == 1000


def test_runtime_queue_blocks_disabled_tenant_claims(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))
    manager.enqueue(tenant_task("task-disabled", tenant_id="disabled-tenant"))

    claimed = manager.claim_next(
        worker_id="worker-a",
        config=RuntimeQueueConfig(disabled_tenant_ids=("disabled-tenant",)),
    )

    assert claimed is None


def test_runtime_queue_rejects_server_disabled_tenant_authority(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))

    with pytest.raises(Exception, match="Tenant is not active"):
        manager.enqueue(
            tenant_runtime_task(),
            composition_context_response=inactive_tenant_context_response(),
        )

    assert store.runtime_queue_items == {}


def test_runtime_queue_rejects_mismatched_tenant_authority(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    manager = RuntimeQueueManager(store=store, artifacts=JsonArtifactStore(tmp_path))

    with pytest.raises(Exception, match="does not match the runtime task tenant"):
        manager.enqueue(
            tenant_runtime_task(),
            composition_context_response=mismatched_tenant_context_response(),
        )

    assert store.runtime_queue_items == {}


def test_runtime_start_rejects_mismatched_area_authority(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)

    with pytest.raises(Exception, match="does not match the runtime task area"):
        RuntimeEntryPoint(store=store, artifacts=artifacts).start(
            tenant_runtime_task(),
            composition_context_response=mismatched_area_context_response(),
        )

    assert store.runtime_runs == {}


def test_runtime_start_rejects_server_disabled_tenant_authority(tmp_path: Path) -> None:
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)

    with pytest.raises(Exception, match="Tenant is not active"):
        RuntimeEntryPoint(store=store, artifacts=artifacts).start(
            tenant_runtime_task(),
            composition_context_response=inactive_tenant_context_response(),
        )

    assert store.runtime_runs == {}


def test_postgres_runtime_store_claims_queue_items_with_skip_locked() -> None:
    queued_row = {
        "id": "queue-example",
        "task_id": "task-example",
        "tenant_id": "demo-tenant",
        "area_id": "demo-tenant",
        "environment": "dev",
        "queue_name": "default",
        "status": "queued",
        "priority": 0,
        "scheduled_at": "2026-07-01T09:00:00Z",
        "attempts": 0,
        "max_attempts": 3,
        "claimed_by": None,
        "claimed_at": None,
        "claimed_until": None,
        "lease_expires_at": None,
        "heartbeat_at": None,
        "attempt_id": None,
        "task_payload_uri": "hetzner://runtime/queue/task.json",
        "composition_context_uri": None,
        "run_id": None,
        "last_error": None,
        "idempotency_key": "example",
        "created_at": "2026-07-01T09:00:00Z",
        "updated_at": "2026-07-01T09:00:00Z",
    }
    claimed_row = {
        **queued_row,
        "status": "claiming",
        "attempts": 1,
        "claimed_by": "worker-a",
        "claimed_at": "2026-07-01T09:01:00Z",
        "claimed_until": "2026-07-01T09:06:00Z",
        "lease_expires_at": "2026-07-01T09:06:00Z",
        "heartbeat_at": "2026-07-01T09:01:00Z",
        "attempt_id": "attempt-queue-example-attempt-1",
        "run_id": "run-task-example-attempt-1",
        "updated_at": "2026-07-01T09:01:00Z",
    }

    class FakeCursor:
        def __init__(
            self,
            rows: list[dict[str, Any]] | None = None,
            row: dict[str, Any] | None = None,
        ) -> None:
            self.rows = rows or []
            self.row = row

        def fetchall(self) -> list[dict[str, Any]]:
            return self.rows

        def fetchone(self) -> dict[str, Any] | None:
            return self.row

    class FakeConnection:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, Any] | None]] = []

        def execute(self, sql: str, params: dict[str, Any] | None = None) -> FakeCursor:
            self.calls.append((sql, params))
            if "FOR UPDATE SKIP LOCKED" in sql:
                return FakeCursor(rows=[queued_row])
            if "COUNT(*) AS running_count" in sql:
                return FakeCursor(row={"running_count": 0})
            if "UPDATE runtime.runtime_queue_items" in sql:
                return FakeCursor(row=claimed_row)
            return FakeCursor()

    fake = FakeConnection()
    store = PostgresRuntimeStore(fake)

    claimed = store.claim_next_runtime_queue_item(
        worker_id="worker-a",
        claimed_at="2026-07-01T09:01:00Z",
        lease_expires_at="2026-07-01T09:06:00Z",
        tenant_running_limits={"demo-tenant": 1},
    )

    assert claimed is not None
    assert claimed["status"] == "claiming"
    assert "FOR UPDATE SKIP LOCKED" in fake.calls[0][0]
    assert "LIMIT 20" not in fake.calls[0][0]
    assert any("pg_advisory_xact_lock" in sql for sql, _params in fake.calls)
    assert any("UPDATE runtime.runtime_queue_items" in sql for sql, _params in fake.calls)
    assert any("INSERT INTO runtime.runtime_run_attempts" in sql for sql, _params in fake.calls)
    assert any("INSERT INTO runtime.runtime_run_claims" in sql for sql, _params in fake.calls)


def test_postgres_runtime_store_returns_persisted_queue_rows() -> None:
    persisted = {
        "id": "queue-example",
        "task_id": "task-example",
        "tenant_id": "demo-tenant",
        "area_id": "demo-tenant",
        "environment": "dev",
        "queue_name": "default",
        "status": "queued",
        "priority": 0,
        "scheduled_at": "2026-07-01T09:00:00Z",
        "attempts": 0,
        "max_attempts": 3,
        "claimed_by": None,
        "claimed_at": None,
        "claimed_until": None,
        "lease_expires_at": None,
        "heartbeat_at": None,
        "attempt_id": None,
        "task_payload_uri": "hetzner://runtime/queue/task.json",
        "composition_context_uri": None,
        "run_id": None,
        "last_error": None,
        "idempotency_key": "example",
        "created_at": "2026-07-01T09:00:00Z",
        "updated_at": "2026-07-01T09:00:00Z",
    }

    class FakeCursor:
        def __init__(self, row: dict[str, Any]) -> None:
            self.row = row

        def fetchone(self) -> dict[str, Any]:
            return self.row

    class FakeConnection:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, Any] | None]] = []

        def execute(self, sql: str, params: dict[str, Any] | None = None) -> FakeCursor:
            self.calls.append((sql, params))
            if "UPDATE runtime.runtime_queue_items" in sql:
                return FakeCursor({**persisted, "status": "cancelled"})
            return FakeCursor(persisted)

    fake = FakeConnection()
    store = PostgresRuntimeStore(fake)

    inserted = store.insert_runtime_queue_item(persisted)
    updated = store.update_runtime_queue_item("queue-example", {"status": "cancelled"})

    assert inserted == persisted
    assert updated["status"] == "cancelled"
    assert "ON CONFLICT (idempotency_key)" in fake.calls[0][0]
    assert "RETURNING id, task_id" in fake.calls[0][0]


def _write_task_fixture(tmp_path: Path, task: dict[str, Any]) -> Path:
    path = tmp_path / "task.json"
    path.write_text(json.dumps(task), encoding="utf-8")
    return path
