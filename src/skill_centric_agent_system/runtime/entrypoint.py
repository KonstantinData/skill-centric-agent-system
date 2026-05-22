from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from skill_centric_agent_system.composition import (
    AnalyzedTask,
    ControlPlaneClient,
    RuntimeProfileComposer,
    TaskAnalyzer,
)
from skill_centric_agent_system.runtime.artifacts import JsonArtifactStore
from skill_centric_agent_system.runtime.storage import (
    FlightRecorder,
    RuntimeStore,
    profile_summary,
)


class RuntimeEntryPointError(RuntimeError):
    """Raised when a runtime run cannot be started."""


@dataclass(frozen=True)
class RuntimeStartResult:
    run_id: str
    analyzed_task: AnalyzedTask
    composition_context_request: dict[str, Any]
    composition_context_response: Mapping[str, Any]
    profile: dict[str, Any]


class RuntimeEntryPoint:
    """Start a runtime run from task intake through profile composition."""

    def __init__(
        self,
        *,
        store: RuntimeStore,
        artifacts: JsonArtifactStore,
        analyzer: TaskAnalyzer | None = None,
        composer: RuntimeProfileComposer | None = None,
        control_plane_client: ControlPlaneClient | None = None,
        environment: Literal["dev", "staging", "prod"] = "dev",
    ) -> None:
        self.store = store
        self.artifacts = artifacts
        self.analyzer = analyzer or TaskAnalyzer()
        self.composer = composer or RuntimeProfileComposer()
        self.control_plane_client = control_plane_client
        self.environment = environment
        self.flight_recorder = FlightRecorder(store, artifacts)

    def start(
        self,
        task: Mapping[str, Any],
        *,
        composition_context_response: Mapping[str, Any] | None = None,
        run_id: str | None = None,
    ) -> RuntimeStartResult:
        analyzed_task = self.analyzer.analyze(task)
        context_request = analyzed_task.to_composition_context_request(
            environment=self.environment
        )
        context_response = composition_context_response or self._fetch_composition_context(
            context_request
        )
        profile = self.composer.compose(analyzed_task, context_response)
        run = self.flight_recorder.start_run(
            task_id=analyzed_task.task_id,
            profile=profile,
            run_id=run_id,
        )
        run_identifier = str(run["id"])

        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="task_analyzed",
            actor_role="composer",
            planned_action={"task_id": analyzed_task.task_id},
            result={
                "task_type": analyzed_task.task_type,
                "risk_level": analyzed_task.risk_level,
                "domains": list(analyzed_task.domains),
                "required_inputs": list(analyzed_task.required_inputs),
                "available_inputs": list(analyzed_task.available_inputs),
                "missing_information": list(analyzed_task.missing_information),
            },
        )
        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="candidates_discovered",
            actor_role="composer",
            planned_action=context_request,
            result=context_response,
        )
        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="profile_emitted",
            actor_role="composer",
            result={"profile": profile},
        )
        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="profile_validated",
            actor_role="composer",
            result={
                "profile_id": profile["id"],
                "validators": profile["validators"],
                "module_versions": profile["module_versions"],
            },
        )
        self.flight_recorder.checkpoint(
            run_id=run_identifier,
            phase="composition",
            state=profile_summary(profile),
        )
        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="runtime_started",
            actor_role="composer",
            result={
                "run_id": run_identifier,
                "profile_id": profile["id"],
                "profile_version": profile["profile_version"],
            },
        )

        return RuntimeStartResult(
            run_id=run_identifier,
            analyzed_task=analyzed_task,
            composition_context_request=context_request,
            composition_context_response=context_response,
            profile=profile,
        )

    def _fetch_composition_context(self, context_request: Mapping[str, Any]) -> dict[str, Any]:
        if self.control_plane_client is None:
            raise RuntimeEntryPointError(
                "RuntimeEntryPoint requires either a ControlPlaneClient or an explicit "
                "composition_context_response."
            )
        return self.control_plane_client.composition_context(context_request)
