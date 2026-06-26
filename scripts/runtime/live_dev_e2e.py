from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any
from uuid import uuid4

from skill_centric_agent_system.composition import (
    CompositionError,
    ControlPlaneClient,
    TaskAnalyzer,
)
from skill_centric_agent_system.runtime import (
    JsonArtifactStore,
    MinimalRuntimeLoop,
    RuntimeEntryPoint,
    RuntimeLoopError,
    open_runtime_store_session,
)

DEFAULT_CONTROL_API_URL = "https://scas-control-api-dev.still-butterfly-bbff.workers.dev"
TARGET_ENVIRONMENTS = ("dev", "staging", "prod")
GENERIC_TASK_SUITE = (
    ("code-review", "examples/tasks/code-review-task.json"),
    ("research", "examples/tasks/research-task.json"),
    ("task-execution", "examples/tasks/task-execution-task.json"),
    ("general-task", "examples/tasks/general-task.json"),
)
TENANT_TASK_FILE = "examples/tasks/tenant-research-task.json"
REDACTED_PRINCIPAL_ID = "<redacted>"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the live dev E2E gate across Cloudflare and Hetzner.",
    )
    parser.add_argument(
        "--task-file",
        default="examples/tasks/code-review-task.json",
        help="Task intake JSON file.",
    )
    parser.add_argument(
        "--task-suite",
        choices=("single", "generic", "tenant"),
        default="single",
        help=(
            "Run only --task-file, run the generic suite covering code-review, "
            "research, task-execution, and general-task, or run the tenant suite "
            "with positive and fail-closed tenant cases."
        ),
    )
    parser.add_argument(
        "--control-plane-url",
        default=os.getenv("SCAS_CONTROL_API_URL", DEFAULT_CONTROL_API_URL),
        help="Cloudflare Control API base URL.",
    )
    parser.add_argument(
        "--control-plane-token",
        default=os.getenv("SCAS_CONTROL_API_TOKEN"),
        help="Control API bearer token. Defaults to SCAS_CONTROL_API_TOKEN.",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("SCAS_RUNTIME_DATABASE_URL"),
        help="Hetzner PostgreSQL URL. Defaults to SCAS_RUNTIME_DATABASE_URL.",
    )
    parser.add_argument(
        "--artifact-root",
        default=os.getenv("SCAS_RUNTIME_ARTIFACT_ROOT", "/opt/scas/runtime"),
        help="Hetzner runtime artifact root.",
    )
    parser.add_argument(
        "--repository-root",
        default=os.getenv("SCAS_REPOSITORY_ROOT", "."),
        help="Repository root used by profile-scoped tools.",
    )
    parser.add_argument(
        "--environment",
        choices=TARGET_ENVIRONMENTS,
        default=os.getenv("TARGET_ENVIRONMENT", "dev"),
        help="Runtime environment label for run metadata and policy routing.",
    )
    args = parser.parse_args(argv)

    if not args.database_url:
        raise SystemExit("SCAS_RUNTIME_DATABASE_URL or --database-url is required.")
    if not args.control_plane_token:
        raise SystemExit("SCAS_CONTROL_API_TOKEN or --control-plane-token is required.")

    control_plane_client = ControlPlaneClient(
        args.control_plane_url,
        api_token=args.control_plane_token,
    )
    artifacts = JsonArtifactStore(args.artifact_root)
    run_suffix = os.getenv("GITHUB_RUN_ID") or uuid4().hex[:12]
    configured_artifact_root_uri = (
        "hetzner://runtime/" + Path(args.artifact_root).as_posix().lstrip("/")
    )

    with open_runtime_store_session(
        mode="postgres",
        database_url=args.database_url,
    ) as storage:
        if args.task_suite == "tenant":
            results = _run_tenant_suite(
                store=storage.store,
                artifacts=artifacts,
                control_plane_client=control_plane_client,
                environment=args.environment,
                repository_root=args.repository_root,
                artifact_root=Path(args.artifact_root),
                artifact_root_uri=configured_artifact_root_uri,
                run_suffix=run_suffix,
            )
        else:
            task_cases = (
                tuple((label, Path(path)) for label, path in GENERIC_TASK_SUITE)
                if args.task_suite == "generic"
                else (("single", Path(args.task_file)),)
            )
            results = [
                _run_positive_case(
                    label=label,
                    task=_load_json(task_path),
                    store=storage.store,
                    artifacts=artifacts,
                    control_plane_client=control_plane_client,
                    environment=args.environment,
                    repository_root=args.repository_root,
                    artifact_root=Path(args.artifact_root),
                    artifact_root_uri=configured_artifact_root_uri,
                    run_id=f"run-live-{run_suffix}-{label}",
                )
                for label, task_path in task_cases
            ]

    status = "passed" if all(result["status"] == "passed" for result in results) else "failed"
    handler_binding_status = (
        "passed"
        if all(result["handler_binding_status"] == "passed" for result in results)
        else "failed"
    )
    print(
        json.dumps(
            {
                "environment": args.environment,
                "status": status,
                "handler_binding_status": handler_binding_status,
                "task_suite": args.task_suite,
                "case_count": len(results),
                "results": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if status == "passed" and handler_binding_status == "passed" else 1


def _run_tenant_suite(
    *,
    store: Any,
    artifacts: JsonArtifactStore,
    control_plane_client: ControlPlaneClient,
    environment: str,
    repository_root: str,
    artifact_root: Path,
    artifact_root_uri: str,
    run_suffix: str,
) -> list[dict[str, Any]]:
    base_task = _load_json(Path(TENANT_TASK_FILE))
    positive = _run_positive_case(
        label="tenant-positive",
        task=base_task,
        store=store,
        artifacts=artifacts,
        control_plane_client=control_plane_client,
        environment=environment,
        repository_root=repository_root,
        artifact_root=artifact_root,
        artifact_root_uri=artifact_root_uri,
        run_id=f"run-live-{run_suffix}-tenant-positive",
    )
    negative_cases = [
        _run_denied_start_case(
            label="tenant-unknown-tenant",
            task=_tenant_task_variant(
                base_task,
                tenant_id="unknown-tenant",
                role_id="unknown-tenant-owner",
                membership_id="tm-unknown-tenant-repository-maintainer",
                hostname="unknown-tenant.example.invalid",
                role_data_sources=("unknown-tenant-website",),
            ),
            store=store,
            artifacts=artifacts,
            control_plane_client=control_plane_client,
            environment=environment,
            run_id=f"run-live-{run_suffix}-tenant-unknown-tenant",
        ),
        _run_denied_start_case(
            label="tenant-inactive-tenant",
            task=_tenant_task_variant(
                base_task,
                tenant_id="inactive-demo-tenant",
                role_id="inactive-demo-tenant-owner",
                membership_id="tm-inactive-demo-tenant-repository-maintainer",
                hostname="inactive-demo-tenant.example.invalid",
                role_data_sources=("inactive-demo-tenant-website",),
            ),
            store=store,
            artifacts=artifacts,
            control_plane_client=control_plane_client,
            environment=environment,
            run_id=f"run-live-{run_suffix}-tenant-inactive-tenant",
        ),
        _run_denied_start_case(
            label="tenant-missing-membership",
            task=_tenant_task_variant(
                base_task,
                membership_id="tm-demo-tenant-missing-member",
            ),
            store=store,
            artifacts=artifacts,
            control_plane_client=control_plane_client,
            environment=environment,
            run_id=f"run-live-{run_suffix}-tenant-missing-membership",
        ),
        _run_denied_start_case(
            label="tenant-foreign-data-source",
            task=_tenant_task_variant(
                base_task,
                role_data_sources=("foreign-tenant-website",),
            ),
            store=store,
            artifacts=artifacts,
            control_plane_client=control_plane_client,
            environment=environment,
            run_id=f"run-live-{run_suffix}-tenant-foreign-data-source",
        ),
        _run_tampered_profile_case(
            task=base_task,
            store=store,
            artifacts=artifacts,
            control_plane_client=control_plane_client,
            environment=environment,
            repository_root=repository_root,
            run_id=f"run-live-{run_suffix}-tenant-tampered-authority",
        ),
    ]
    return [positive, *negative_cases]


def _run_positive_case(
    *,
    label: str,
    task: Mapping[str, Any],
    store: Any,
    artifacts: JsonArtifactStore,
    control_plane_client: ControlPlaneClient,
    environment: str,
    repository_root: str,
    artifact_root: Path,
    artifact_root_uri: str,
    run_id: str,
) -> dict[str, Any]:
    runtime = RuntimeEntryPoint(
        store=store,
        artifacts=artifacts,
        control_plane_client=control_plane_client,
        environment=environment,  # type: ignore[arg-type]
    )
    analyzed = runtime.analyzer.analyze(task)
    context_request = analyzed.to_composition_context_request(
        environment=environment,  # type: ignore[arg-type]
    )
    context_response = control_plane_client.composition_context(context_request)
    try:
        start_result = runtime.start(
            task,
            composition_context_response=context_response,
            run_id=run_id,
        )
    except CompositionError as error:
        return {
            "case": label,
            "environment": environment,
            "status": "failed",
            "handler_binding_status": "failed",
            "expected_failure_stage": "none",
            "composition_request": _composition_request_summary(context_request),
            "composition_response": _composition_response_summary(context_response),
            "composition_status": context_response.get("composition_status"),
            "error_type": type(error).__name__,
            "error": str(error),
            "runtime_started": False,
        }
    loop_result = MinimalRuntimeLoop(
        store=store,
        artifacts=artifacts,
        repository_root=repository_root,
        control_plane_client=control_plane_client,
    ).run(start_result)
    run_record = store.get_runtime_run(start_result.run_id)
    events = store.events_for_run(start_result.run_id)
    checkpoints = store.checkpoints_for_run(start_result.run_id)
    handler_evidence = handler_binding_evidence_from_checkpoints(
        checkpoints,
        artifact_root=artifact_root,
    )
    case_status = (
        "passed"
        if loop_result.status == "succeeded"
        and handler_evidence["handler_binding_status"] == "passed"
        else "failed"
    )
    return {
        "case": label,
        "environment": environment,
        "status": case_status,
        "run_id": start_result.run_id,
        "task_type": start_result.profile["task_type"],
        "profile_id": start_result.profile["id"],
        "profile_version": start_result.profile["profile_version"],
        "handler_binding_status": handler_evidence["handler_binding_status"],
        "planner_checkpoint_uri": handler_evidence["planner_checkpoint_uri"],
        "skill_handlers": handler_evidence["skill_handlers"],
        "run_status": run_record["status"] if run_record else None,
        "stop_reason": run_record["stop_reason"] if run_record else None,
        "composition_status": start_result.composition_context_response.get(
            "composition_status"
        ),
        "composition_request": _composition_request_summary(
            start_result.composition_context_request
        ),
        "composition_response": _composition_response_summary(
            start_result.composition_context_response
        ),
        "event_count": len(events),
        "checkpoint_count": len(checkpoints),
        "artifact_root_uri": artifact_root_uri,
        "runtime_record_artifact_root_uri": (
            run_record["artifact_root_uri"] if run_record else None
        ),
        "runtime_output_task_type": loop_result.response["runtime_output"]["task_type"],
    }


def _run_denied_start_case(
    *,
    label: str,
    task: Mapping[str, Any],
    store: Any,
    artifacts: JsonArtifactStore,
    control_plane_client: ControlPlaneClient,
    environment: str,
    run_id: str,
) -> dict[str, Any]:
    analyzer = TaskAnalyzer()
    analyzed = analyzer.analyze(task)
    context_request = analyzed.to_composition_context_request(
        environment=environment,  # type: ignore[arg-type]
    )
    context_response = control_plane_client.composition_context(context_request)
    runtime = RuntimeEntryPoint(
        store=store,
        artifacts=artifacts,
        analyzer=analyzer,
        control_plane_client=control_plane_client,
        environment=environment,  # type: ignore[arg-type]
    )
    try:
        runtime.start(
            task,
            composition_context_response=context_response,
            run_id=run_id,
        )
    except CompositionError as error:
        return {
            "case": label,
            "environment": environment,
            "status": "passed",
            "expected_failure_stage": "composition",
            "composition_status": context_response.get("composition_status"),
            "composition_request": _composition_request_summary(context_request),
            "composition_response": _composition_response_summary(context_response),
            "handler_binding_status": "passed",
            "error_type": type(error).__name__,
            "error": str(error),
            "runtime_started": False,
        }

    return {
        "case": label,
        "environment": environment,
        "status": "failed",
        "expected_failure_stage": "composition",
        "composition_status": context_response.get("composition_status"),
        "composition_request": _composition_request_summary(context_request),
        "composition_response": _composition_response_summary(context_response),
        "handler_binding_status": "failed",
        "error": "Tenant negative case unexpectedly started a runtime run.",
        "runtime_started": True,
    }


def _run_tampered_profile_case(
    *,
    task: Mapping[str, Any],
    store: Any,
    artifacts: JsonArtifactStore,
    control_plane_client: ControlPlaneClient,
    environment: str,
    repository_root: str,
    run_id: str,
) -> dict[str, Any]:
    runtime = RuntimeEntryPoint(
        store=store,
        artifacts=artifacts,
        control_plane_client=control_plane_client,
        environment=environment,  # type: ignore[arg-type]
    )
    analyzed = runtime.analyzer.analyze(task)
    context_request = analyzed.to_composition_context_request(
        environment=environment,  # type: ignore[arg-type]
    )
    context_response = control_plane_client.composition_context(context_request)
    try:
        start_result = runtime.start(
            task,
            composition_context_response=context_response,
            run_id=run_id,
        )
    except CompositionError as error:
        return {
            "case": "tenant-tampered-authority",
            "environment": environment,
            "status": "failed",
            "expected_failure_stage": "runtime_profile_enforcement",
            "composition_status": context_response.get("composition_status"),
            "composition_request": _composition_request_summary(context_request),
            "composition_response": _composition_response_summary(context_response),
            "handler_binding_status": "failed",
            "error_type": type(error).__name__,
            "error": str(error),
            "runtime_started": False,
        }
    if isinstance(start_result.profile.get("tenant_authority"), dict):
        start_result.profile["tenant_authority"]["tenant_id"] = "foreign-tenant"

    try:
        MinimalRuntimeLoop(
            store=store,
            artifacts=artifacts,
            repository_root=repository_root,
            control_plane_client=control_plane_client,
        ).run(start_result)
    except RuntimeLoopError as error:
        return {
            "case": "tenant-tampered-authority",
            "environment": environment,
            "status": "passed" if error.stop_reason == "policy_denied" else "failed",
            "expected_failure_stage": "runtime_profile_enforcement",
            "composition_status": start_result.composition_context_response.get(
                "composition_status"
            ),
            "composition_request": _composition_request_summary(
                start_result.composition_context_request
            ),
            "composition_response": _composition_response_summary(
                start_result.composition_context_response
            ),
            "handler_binding_status": "passed",
            "run_id": start_result.run_id,
            "stop_reason": error.stop_reason,
            "error_type": type(error).__name__,
            "error": str(error),
        }

    return {
        "case": "tenant-tampered-authority",
        "environment": environment,
        "status": "failed",
        "expected_failure_stage": "runtime_profile_enforcement",
        "composition_status": start_result.composition_context_response.get(
            "composition_status"
        ),
        "composition_request": _composition_request_summary(
            start_result.composition_context_request
        ),
        "composition_response": _composition_response_summary(
            start_result.composition_context_response
        ),
        "handler_binding_status": "failed",
        "run_id": start_result.run_id,
        "error": "Tampered tenant authority unexpectedly reached runtime execution.",
    }


def _composition_request_summary(
    context_request: Mapping[str, Any],
) -> dict[str, Any]:
    principal = context_request.get("principal", {})
    tenant_context = context_request.get("tenant_context")
    task = context_request.get("task", {})
    signals = task.get("signals", {}) if isinstance(task, Mapping) else {}
    return {
        "principal_kind": (
            principal.get("kind") if isinstance(principal, Mapping) else None
        ),
        "principal_id": _redact_principal_id(
            principal.get("id") if isinstance(principal, Mapping) else None
        ),
        "task_type": task.get("type") if isinstance(task, Mapping) else None,
        "tenant_context_present": isinstance(tenant_context, Mapping),
        "tenant_id": (
            tenant_context.get("tenant_id")
            if isinstance(tenant_context, Mapping)
            else None
        ),
        "area_id": (
            tenant_context.get("area_id") if isinstance(tenant_context, Mapping) else None
        ),
        "membership_id": (
            tenant_context.get("membership_id")
            if isinstance(tenant_context, Mapping)
            else None
        ),
        "capability_hints": (
            signals.get("capability_hints") if isinstance(signals, Mapping) else []
        ),
    }


def _composition_response_summary(
    context_response: Mapping[str, Any],
) -> dict[str, Any]:
    tenant_authority = context_response.get("tenant_authority")
    graph_validation = context_response.get("graph_validation", {})
    return {
        "composition_status": context_response.get("composition_status"),
        "tenant_authority_present": isinstance(tenant_authority, Mapping),
        "tenant_authority_tenant_id": (
            tenant_authority.get("tenant_id")
            if isinstance(tenant_authority, Mapping)
            else None
        ),
        "candidate_module_count": _reference_count(context_response, "candidate_modules"),
        "allowed_knowledge_scope_count": _reference_count(
            context_response,
            "allowed_knowledge_scopes",
        ),
        "allowed_data_scope_count": _reference_count(
            context_response,
            "allowed_data_scopes",
        ),
        "allowed_memory_scope_count": _reference_count(
            context_response,
            "allowed_memory_scopes",
        ),
        "validation_requirement_count": _reference_count(
            context_response,
            "validation_requirements",
        ),
        "policy_decision_count": _reference_count(context_response, "policy_decisions"),
        "graph_is_valid": (
            graph_validation.get("is_valid")
            if isinstance(graph_validation, Mapping)
            else None
        ),
        "graph_errors": (
            graph_validation.get("errors", [])
            if isinstance(graph_validation, Mapping)
            else []
        ),
    }


def _redact_principal_id(principal_id: Any) -> Any:
    secret_principal_id = os.getenv("SCAS_LIVE_E2E_REDACT_PRINCIPAL_ID", "")
    if secret_principal_id and principal_id == secret_principal_id:
        return REDACTED_PRINCIPAL_ID
    return principal_id


def _reference_count(context_response: Mapping[str, Any], key: str) -> int:
    value = context_response.get(key, [])
    return len(value) if isinstance(value, list) else 0


def _tenant_task_variant(
    task: Mapping[str, Any],
    *,
    tenant_id: str | None = None,
    role_id: str | None = None,
    membership_id: str | None = None,
    hostname: str | None = None,
    role_data_sources: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    variant = deepcopy(dict(task))
    context = variant.setdefault("context", {})
    if not isinstance(context, dict):
        raise ValueError("tenant task context must be a JSON object.")
    auth = context.setdefault("auth", {})
    if not isinstance(auth, dict):
        raise ValueError("tenant task auth context must be a JSON object.")

    if tenant_id is not None:
        auth["tenant_id"] = tenant_id
        auth["area_id"] = tenant_id
    if role_id is not None:
        auth["roles"] = [role_id]
    if membership_id is not None:
        auth["membership_id"] = membership_id
    if hostname is not None:
        auth["tenant_hostname"] = hostname
    if role_data_sources is not None:
        auth["role_data_sources"] = list(role_data_sources)
    return variant


def handler_binding_evidence_from_checkpoints(
    checkpoints: tuple[Mapping[str, Any], ...],
    *,
    artifact_root: Path,
) -> dict[str, Any]:
    planner_checkpoint = next(
        (checkpoint for checkpoint in checkpoints if checkpoint.get("phase") == "planner"),
        None,
    )
    if planner_checkpoint is None:
        return {
            "handler_binding_status": "failed",
            "planner_checkpoint_uri": "",
            "skill_handlers": [],
        }

    state_uri = str(planner_checkpoint.get("state_uri", ""))
    planner_payload = _load_runtime_artifact(artifact_root, state_uri)
    skill_handlers = planner_payload.get("skill_handlers", [])
    if not isinstance(skill_handlers, list):
        skill_handlers = []

    sanitized_handlers = [
        {
            "handler_id": str(handler.get("handler_id", "")),
            "name": str(handler.get("name", "")),
            "version": str(handler.get("version", "")),
        }
        for handler in skill_handlers
        if isinstance(handler, Mapping)
    ]
    return {
        "handler_binding_status": (
            "passed" if _handler_bindings_are_valid(sanitized_handlers) else "failed"
        ),
        "planner_checkpoint_uri": state_uri,
        "skill_handlers": sanitized_handlers,
    }


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return parsed


def _load_runtime_artifact(artifact_root: Path, uri: str) -> dict[str, Any]:
    relative = uri.removeprefix("hetzner://runtime/").strip("/")
    return _load_json(artifact_root / Path(relative))


def _handler_bindings_are_valid(skill_handlers: list[dict[str, str]]) -> bool:
    if not skill_handlers:
        return False
    return all(
        handler["handler_id"] == f"{handler['name']}@{handler['version']}"
        and handler["name"]
        and handler["version"]
        for handler in skill_handlers
    )


if __name__ == "__main__":
    raise SystemExit(main())
