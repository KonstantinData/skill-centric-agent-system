from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter

from jsonschema import Draft202012Validator

from skill_centric_agent_system.runtime import (
    InMemoryRuntimeStore,
    JsonArtifactStore,
    MinimalRuntimeLoop,
    RuntimeEntryPoint,
)
from tests.test_runtime_tool_gateway_and_loop import (
    COMPOSITION_CONTEXT_RESPONSE_PATH,
    REPO_ROOT,
    RUNTIME_PLANE_SCHEMA_PATH,
    TASK_EXAMPLE_PATH,
    load_json,
)


def test_minimal_runtime_loop_stays_within_efficiency_baseline(tmp_path: Path) -> None:
    max_seconds = float(os.environ.get("SCAS_RUNTIME_LOOP_EFFICIENCY_MAX_SECONDS", "3.0"))
    store = InMemoryRuntimeStore()
    artifacts = JsonArtifactStore(tmp_path)
    entrypoint = RuntimeEntryPoint(store=store, artifacts=artifacts)
    start_result = entrypoint.start(
        load_json(TASK_EXAMPLE_PATH),
        composition_context_response=load_json(COMPOSITION_CONTEXT_RESPONSE_PATH),
    )
    loop = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=REPO_ROOT,
    )

    started_at = perf_counter()
    result = loop.run(start_result)
    elapsed_seconds = perf_counter() - started_at

    assert result.status == "succeeded"
    assert elapsed_seconds < max_seconds
    assert len(store.runtime_steps) == 4
    assert len(store.tool_invocations) == 2
    assert len(store.validation_results) == 2
    assert len(store.runtime_checkpoints) <= 5
    assert len(store.runtime_events) <= 30
    recordset = store.as_runtime_plane_recordset()
    assert len(recordset["records"]["runtime_events"]) <= 30
    Draft202012Validator(load_json(RUNTIME_PLANE_SCHEMA_PATH)).validate(recordset)
