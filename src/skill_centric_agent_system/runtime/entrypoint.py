from __future__ import annotations

import hashlib
import json
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
from skill_centric_agent_system.runtime.models import (
    RECOMPOSITION_REASONS,
    RecompositionRequest,
    require_choice,
    slug_id,
)
from skill_centric_agent_system.runtime.policies import profile_redacts_sensitive_data
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
    profile_artifact_uri: str
    profile_sha256: str


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
        generation_mode: Literal["initial", "recomposition"] = "initial",
        profile_generation: int = 1,
        parent_profile_id: str | None = None,
        recomposition_reason: str | None = None,
    ) -> RuntimeStartResult:
        self._assert_profile_generation_request(
            generation_mode=generation_mode,
            profile_generation=profile_generation,
            parent_profile_id=parent_profile_id,
            recomposition_reason=recomposition_reason,
        )
        analyzed_task = self.analyzer.analyze(task)
        context_request = analyzed_task.to_composition_context_request(
            environment=self.environment,
            generation_mode=generation_mode,
            parent_profile_id=parent_profile_id,
        )
        context_response = composition_context_response or self._fetch_composition_context(
            context_request
        )
        profile = self.composer.compose(
            analyzed_task,
            context_response,
            profile_generation=profile_generation,
            parent_profile_id=parent_profile_id,
            recomposition_reason=recomposition_reason,
        )
        profile_artifact_uri, profile_sha256 = self._seal_profile(profile)
        redact_sensitive_data = profile_redacts_sensitive_data(profile)
        run = self.flight_recorder.start_run(
            task_id=analyzed_task.task_id,
            profile=profile,
            run_id=run_id or _default_run_id(analyzed_task.task_id, profile_generation),
            profile_artifact_uri=profile_artifact_uri,
            profile_sha256=profile_sha256,
            profile_generation=int(profile["profile_generation"]),
            parent_profile_id=profile.get("parent_profile_id"),
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
            redact_sensitive_data=redact_sensitive_data,
        )
        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="candidates_discovered",
            actor_role="composer",
            planned_action=context_request,
            result=context_response,
            redact_sensitive_data=redact_sensitive_data,
        )
        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="profile_emitted",
            actor_role="composer",
            result={"profile": profile},
            redact_sensitive_data=redact_sensitive_data,
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
            redact_sensitive_data=redact_sensitive_data,
        )
        self.flight_recorder.checkpoint(
            run_id=run_identifier,
            phase="composition",
            state=profile_summary(profile),
            redact_sensitive_data=redact_sensitive_data,
        )
        self.flight_recorder.record_event(
            run_id=run_identifier,
            event_type="runtime_started",
            actor_role="composer",
            result={
                "run_id": run_identifier,
                "profile_id": profile["id"],
                "profile_version": profile["profile_version"],
                "profile_artifact_uri": profile_artifact_uri,
                "profile_sha256": profile_sha256,
            },
            redact_sensitive_data=redact_sensitive_data,
        )

        return RuntimeStartResult(
            run_id=run_identifier,
            analyzed_task=analyzed_task,
            composition_context_request=context_request,
            composition_context_response=context_response,
            profile=profile,
            profile_artifact_uri=profile_artifact_uri,
            profile_sha256=profile_sha256,
        )

    def _seal_profile(self, profile: Mapping[str, Any]) -> tuple[str, str]:
        canonical = json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")
        profile_sha256 = hashlib.sha256(canonical).hexdigest()
        uri = self.artifacts.write_json(
            ("profiles", str(profile["id"]), profile_sha256),
            dict(profile),
            redact=False,
        )
        return uri, profile_sha256

    def continue_recomposition(
        self,
        task: Mapping[str, Any],
        *,
        recomposition_request: RecompositionRequest | Mapping[str, Any],
        composition_context_response: Mapping[str, Any] | None = None,
        run_id: str | None = None,
    ) -> RuntimeStartResult:
        request = (
            recomposition_request
            if isinstance(recomposition_request, RecompositionRequest)
            else RecompositionRequest.from_mapping(recomposition_request)
        )
        return self.start(
            task,
            composition_context_response=composition_context_response,
            run_id=run_id
            or slug_id(
                f"{request.source_run_id}-generation-{request.requested_profile_generation}",
                prefix="run",
            ),
            generation_mode="recomposition",
            profile_generation=request.requested_profile_generation,
            parent_profile_id=request.parent_profile_id,
            recomposition_reason=request.recomposition_reason,
        )

    def _fetch_composition_context(self, context_request: Mapping[str, Any]) -> dict[str, Any]:
        if self.control_plane_client is None:
            raise RuntimeEntryPointError(
                "RuntimeEntryPoint requires either a ControlPlaneClient or an explicit "
                "composition_context_response."
            )
        return self.control_plane_client.composition_context(context_request)

    def _assert_profile_generation_request(
        self,
        *,
        generation_mode: Literal["initial", "recomposition"],
        profile_generation: int,
        parent_profile_id: str | None,
        recomposition_reason: str | None,
    ) -> None:
        if profile_generation < 1:
            raise RuntimeEntryPointError("profile_generation must be greater than zero.")
        if generation_mode == "initial":
            if profile_generation != 1 or parent_profile_id is not None or recomposition_reason:
                raise RuntimeEntryPointError(
                    "Initial composition cannot include recomposition traceability."
                )
            return
        if parent_profile_id is None or recomposition_reason is None:
            raise RuntimeEntryPointError(
                "Recomposition requires parent_profile_id and recomposition_reason."
            )
        require_choice(recomposition_reason, RECOMPOSITION_REASONS, "recomposition_reason")
        if profile_generation <= 1:
            raise RuntimeEntryPointError(
                "Recomposition requires profile_generation greater than 1."
            )


def _default_run_id(task_id: str, profile_generation: int) -> str | None:
    if profile_generation <= 1:
        return None
    return slug_id(f"{task_id}-generation-{profile_generation}", prefix="run")
