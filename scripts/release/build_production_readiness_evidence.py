from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

CONTRACT_VERSION = "0.3.0"
GITHUB_HOST = "github.com"

TARGET_ENVIRONMENTS = {"dev", "staging", "prod"}
CERTIFICATION_MODES = {"evidence-only", "certify"}

EXTERNAL_EVIDENCE_SPECS = {
    "live_runtime_gates": {
        "argument_name": "live_runtime_gates_run_url",
        "expected_workflow": "Live Runtime Gates",
        "missing_message": "certify mode requires live_runtime_gates_run_url",
    },
    "ai_gateway_smoke": {
        "argument_name": "ai_gateway_smoke_run_url",
        "expected_workflow": "CI",
        "missing_message": "certify mode requires ai_gateway_smoke_run_url",
    },
}

REPOSITORY_GATE_RESULTS = (
    ("Repository integrity", "python -m pytest; python -m ruff check ."),
    (
        "Repository security and supply chain",
        "security governance scripts; Actions-BOM; release SBOM",
    ),
    ("Contract and documentation consistency", "tracked JSON parse; committed docs gate"),
    (
        "Executable skill runtime",
        (
            "python -m pytest tests/test_runtime_skill_handlers.py "
            "tests/test_skill_handler_coverage.py "
            "tests/test_skill_handler_version_policy.py; "
            "python scripts/runtime/skill_handler_coverage.py --check"
        ),
    ),
    (
        "Controlled write-capable execution",
        (
            "python -m pytest tests/test_controlled_write_execution.py "
            "tests/test_runtime_tool_gateway_and_loop.py"
        ),
    ),
    (
        "Scheduled runtime retention cleanup",
        (
            ".github/workflows/runtime-retention-cleanup.yml; "
            "python -m pytest tests/test_runtime_redaction_retention.py "
            "tests/test_github_actions_workflows.py"
        ),
    ),
    (
        "Production telemetry and alerting",
        (
            "python scripts/operations/evaluate_telemetry_alerts.py "
            "--policy examples/operations/production-telemetry-policy.json "
            "--snapshot examples/operations/production-telemetry-snapshot.json "
            "--fail-on-critical; "
            "python -m pytest tests/test_production_telemetry_alerting.py"
        ),
    ),
    (
        "Security hardening and threat model closure",
        (
            "python scripts/security/validate_security_closure.py; "
            "python -m pytest tests/test_security_closure.py "
            "tests/test_security_governance.py"
        ),
    ),
    (
        "Analyzer, composer, and human review quality",
        (
            "python -m pytest tests/test_composition_pipeline.py "
            "tests/test_contract_schemas.py -k human_review"
        ),
    ),
    (
        "Expanded production skill handler coverage",
        (
            "python -m pytest tests/test_runtime_skill_handlers.py "
            "tests/test_skill_handler_coverage.py; "
            "python scripts/runtime/skill_handler_coverage.py --check"
        ),
    ),
    ("Control Plane Worker gates", "npm worker type generation, typecheck, tests, check"),
)

STAGING_PROD_OPEN_GAPS = (
    {
        "id": "P5.10",
        "gate": "Production readiness certification run",
        "reason": (
            "The full production readiness certification gate has not yet been run "
            "against the target live environment."
        ),
    },
)


class EvidenceError(ValueError):
    """Raised when release evidence cannot be generated safely."""


@dataclass(frozen=True)
class ActionsRunRef:
    repository: str
    run_id: str
    url: str


def canonical_actions_run_url(repository: str, run_id: str) -> str:
    return f"https://{GITHUB_HOST}/{repository}/actions/runs/{run_id}"


def parse_actions_run_url(url: str, expected_repository: str) -> ActionsRunRef:
    if not url:
        raise EvidenceError("GitHub Actions run URL must not be empty")

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != GITHUB_HOST:
        raise EvidenceError("GitHub Actions run URL must use https://github.com")
    if parsed.query or parsed.fragment:
        raise EvidenceError("GitHub Actions run URL must be canonical without query or fragment")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 5 or parts[2:4] != ["actions", "runs"]:
        raise EvidenceError("GitHub Actions run URL must match /OWNER/REPO/actions/runs/RUN_ID")

    repository = f"{parts[0]}/{parts[1]}"
    if repository.lower() != expected_repository.lower():
        raise EvidenceError(
            f"GitHub Actions run URL repository {repository!r} does not match "
            f"expected repository {expected_repository!r}"
        )

    run_id = parts[4]
    if not run_id.isdecimal():
        raise EvidenceError("GitHub Actions run URL must end with a numeric run ID")

    return ActionsRunRef(
        repository=expected_repository,
        run_id=run_id,
        url=canonical_actions_run_url(expected_repository, run_id),
    )


def validate_common_inputs(
    *,
    target_environment: str,
    certification_mode: str,
    release_scope: str,
) -> None:
    if target_environment not in TARGET_ENVIRONMENTS:
        raise EvidenceError(f"target_environment must be one of {sorted(TARGET_ENVIRONMENTS)}")
    if certification_mode not in CERTIFICATION_MODES:
        raise EvidenceError(f"certification_mode must be one of {sorted(CERTIFICATION_MODES)}")
    if not release_scope.strip():
        raise EvidenceError("release_scope must not be empty")


def validate_certification_inputs(
    *,
    repository: str,
    target_environment: str,
    release_scope: str,
    certification_mode: str,
    live_runtime_gates_run_url: str,
    ai_gateway_smoke_run_url: str,
) -> None:
    validate_common_inputs(
        target_environment=target_environment,
        certification_mode=certification_mode,
        release_scope=release_scope,
    )

    if certification_mode != "certify":
        return

    urls = {
        "live_runtime_gates": live_runtime_gates_run_url,
        "ai_gateway_smoke": ai_gateway_smoke_run_url,
    }
    for evidence_name, url in urls.items():
        spec = EXTERNAL_EVIDENCE_SPECS[evidence_name]
        if not url:
            raise EvidenceError(spec["missing_message"])
        parse_actions_run_url(url, repository)

    if live_runtime_gates_run_url == ai_gateway_smoke_run_url:
        raise EvidenceError("certify mode requires distinct live runtime and AI Gateway runs")


def load_json_file(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvidenceError(f"required run metadata file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"run metadata file is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise EvidenceError(f"run metadata file must contain a JSON object: {path}")
    return data


def validate_run_metadata(
    *,
    evidence_name: str,
    run_url: str,
    metadata: dict[str, object],
    expected_repository: str,
    expected_commit: str,
) -> dict[str, object]:
    spec = EXTERNAL_EVIDENCE_SPECS[evidence_name]
    expected_ref = parse_actions_run_url(run_url, expected_repository)
    expected_workflow = spec["expected_workflow"]

    metadata_run_id = str(metadata.get("databaseId", ""))
    if metadata_run_id != expected_ref.run_id:
        raise EvidenceError(
            f"{evidence_name} metadata run ID {metadata_run_id!r} does not match "
            f"URL run ID {expected_ref.run_id!r}"
        )

    workflow_name = str(metadata.get("workflowName", ""))
    if workflow_name != expected_workflow:
        raise EvidenceError(
            f"{evidence_name} expected workflow {expected_workflow!r}, got {workflow_name!r}"
        )

    status = str(metadata.get("status", ""))
    conclusion = str(metadata.get("conclusion", ""))
    if status != "completed" or conclusion != "success":
        raise EvidenceError(
            f"{evidence_name} run must be completed successfully; "
            f"status={status!r} conclusion={conclusion!r}"
        )

    head_sha = str(metadata.get("headSha", ""))
    if head_sha != expected_commit:
        raise EvidenceError(
            f"{evidence_name} run headSha {head_sha!r} does not match release commit "
            f"{expected_commit!r}"
        )

    metadata_url = str(metadata.get("url", ""))
    if metadata_url and metadata_url != expected_ref.url:
        raise EvidenceError(
            f"{evidence_name} metadata URL {metadata_url!r} does not match {expected_ref.url!r}"
        )

    return {
        "run_id": expected_ref.run_id,
        "run_url": expected_ref.url,
        "workflow": workflow_name,
        "status": status,
        "conclusion": conclusion,
        "head_sha": head_sha,
        "display_title": str(metadata.get("displayTitle", "")),
        "event": str(metadata.get("event", "")),
        "created_at": str(metadata.get("createdAt", "")),
        "updated_at": str(metadata.get("updatedAt", "")),
        "validation_status": "passed",
    }


def open_release_gaps(target_environment: str, release_scope: str) -> list[dict[str, str]]:
    gaps = []
    if target_environment in {"staging", "prod"}:
        gaps.extend(dict(gap) for gap in STAGING_PROD_OPEN_GAPS)

    return gaps


def production_status(
    *,
    target_environment: str,
    certification_mode: str,
    gaps: list[dict[str, str]],
) -> str:
    if gaps:
        return "not-production-ready"
    if certification_mode != "certify":
        return "initial-productive-core" if target_environment == "dev" else "not-production-ready"
    if target_environment == "prod":
        return "production-ready"
    if target_environment == "staging":
        return "staging-ready"
    return "initial-productive-core"


def gate_results(
    *,
    certification_mode: str,
    external_evidence: dict[str, object],
    gaps: list[dict[str, str]],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = [
        {
            "gate": gate,
            "status": "passed",
            "evidence": evidence,
        }
        for gate, evidence in REPOSITORY_GATE_RESULTS
    ]

    if certification_mode == "certify":
        results.extend(
            [
                {
                    "gate": "Live runtime gates",
                    "status": "passed",
                    "evidence": external_evidence["live_runtime_gates"],
                },
                {
                    "gate": "AI Gateway live smoke",
                    "status": "passed",
                    "evidence": external_evidence["ai_gateway_smoke"],
                },
                {
                    "gate": "Live handler binding evidence",
                    "status": "passed",
                    "evidence": external_evidence["live_handler_bindings"],
                },
            ]
        )
    else:
        results.append(
            {
                "gate": "Live runtime gates",
                "status": "not_required",
                "evidence": "evidence-only mode does not certify live runtime gates",
            }
        )
        results.append(
            {
                "gate": "Live handler binding evidence",
                "status": "not_required",
                "evidence": "evidence-only mode does not certify live handler bindings",
            }
        )

    results.extend(
        {
            "gate": gap["gate"],
            "status": "pending",
            "evidence": gap["reason"],
            "backlog_item": gap["id"],
        }
        for gap in gaps
    )
    return results


def external_evidence(
    *,
    repository: str,
    commit: str,
    certification_mode: str,
    live_runtime_gates_run_url: str,
    ai_gateway_smoke_run_url: str,
    live_runtime_gates_metadata: dict[str, object] | None,
    ai_gateway_smoke_metadata: dict[str, object] | None,
    live_handler_binding_evidence: dict[str, object] | None,
) -> dict[str, object]:
    if certification_mode != "certify":
        return {
            "live_runtime_gates": {
                "required": False,
                "run_url": "",
                "validation_status": "not_required",
            },
            "ai_gateway_smoke": {
                "required": False,
                "run_url": "",
                "validation_status": "not_required",
            },
            "live_handler_bindings": {
                "required": False,
                "validation_status": "not_required",
            },
        }

    if live_runtime_gates_metadata is None:
        raise EvidenceError("certify mode requires live runtime run metadata")
    if ai_gateway_smoke_metadata is None:
        raise EvidenceError("certify mode requires AI Gateway smoke run metadata")
    if live_handler_binding_evidence is None:
        raise EvidenceError("certify mode requires live handler binding evidence")

    return {
        "live_runtime_gates": {
            "required": True,
            **validate_run_metadata(
                evidence_name="live_runtime_gates",
                run_url=live_runtime_gates_run_url,
                metadata=live_runtime_gates_metadata,
                expected_repository=repository,
                expected_commit=commit,
            ),
        },
        "ai_gateway_smoke": {
            "required": True,
            **validate_run_metadata(
                evidence_name="ai_gateway_smoke",
                run_url=ai_gateway_smoke_run_url,
                metadata=ai_gateway_smoke_metadata,
                expected_repository=repository,
                expected_commit=commit,
            ),
        },
        "live_handler_bindings": {
            "required": True,
            **validate_live_handler_binding_evidence(live_handler_binding_evidence),
        },
    }


def build_evidence(
    *,
    repository: str,
    commit: str,
    workflow_run_id: str,
    workflow_run_attempt: str,
    target_environment: str,
    release_scope: str,
    certification_mode: str,
    live_runtime_gates_run_url: str = "",
    ai_gateway_smoke_run_url: str = "",
    live_runtime_gates_metadata: dict[str, object] | None = None,
    ai_gateway_smoke_metadata: dict[str, object] | None = None,
    live_handler_binding_evidence: dict[str, object] | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    validate_certification_inputs(
        repository=repository,
        target_environment=target_environment,
        release_scope=release_scope,
        certification_mode=certification_mode,
        live_runtime_gates_run_url=live_runtime_gates_run_url,
        ai_gateway_smoke_run_url=ai_gateway_smoke_run_url,
    )

    gaps = open_release_gaps(target_environment, release_scope)
    external = external_evidence(
        repository=repository,
        commit=commit,
        certification_mode=certification_mode,
        live_runtime_gates_run_url=live_runtime_gates_run_url,
        ai_gateway_smoke_run_url=ai_gateway_smoke_run_url,
        live_runtime_gates_metadata=live_runtime_gates_metadata,
        ai_gateway_smoke_metadata=ai_gateway_smoke_metadata,
        live_handler_binding_evidence=live_handler_binding_evidence,
    )
    status = production_status(
        target_environment=target_environment,
        certification_mode=certification_mode,
        gaps=gaps,
    )
    final_decision = (
        "certified"
        if status in {"staging-ready", "production-ready"}
        else "not-certified"
    )

    return {
        "contract_version": CONTRACT_VERSION,
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "repository": repository,
        "commit": commit,
        "workflow_run": {
            "id": workflow_run_id,
            "attempt": workflow_run_attempt,
            "url": canonical_actions_run_url(repository, workflow_run_id),
        },
        "target_environment": target_environment,
        "release_scope": release_scope,
        "certification_mode": certification_mode,
        "status": status,
        "final_decision": final_decision,
        "gate_results": gate_results(
            certification_mode=certification_mode,
            external_evidence=external,
            gaps=gaps,
        ),
        "external_evidence": external,
        "open_release_gaps": gaps,
        "sensitive_data_handling": "Credential values are not written to this evidence artifact.",
    }


def metadata_from_path(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    return load_json_file(path)


def validate_live_handler_binding_evidence(evidence: dict[str, object]) -> dict[str, object]:
    if evidence.get("status") != "passed":
        raise EvidenceError("live handler binding evidence status must be passed")
    if evidence.get("handler_binding_status") != "passed":
        raise EvidenceError("live handler binding evidence must pass handler_binding_status")

    results = evidence.get("results")
    if not isinstance(results, list) or not results:
        raise EvidenceError("live handler binding evidence must include results")

    case_summaries = []
    for result in results:
        if not isinstance(result, dict):
            raise EvidenceError("live handler binding result must be an object")
        if result.get("status") != "passed":
            raise EvidenceError("live handler binding result status must be passed")
        if result.get("handler_binding_status") != "passed":
            raise EvidenceError("live handler binding result must pass binding status")

        skill_handlers = result.get("skill_handlers")
        if not isinstance(skill_handlers, list) or not skill_handlers:
            raise EvidenceError("live handler binding result must include skill_handlers")
        validated_handlers = [
            _validate_skill_handler_binding(handler) for handler in skill_handlers
        ]
        case_summaries.append(
            {
                "case": str(result.get("case", "")),
                "run_id": str(result.get("run_id", "")),
                "profile_id": str(result.get("profile_id", "")),
                "task_type": str(result.get("task_type", "")),
                "planner_checkpoint_uri": str(result.get("planner_checkpoint_uri", "")),
                "skill_handlers": validated_handlers,
            }
        )

    return {
        "validation_status": "passed",
        "status": "passed",
        "task_suite": str(evidence.get("task_suite", "")),
        "case_count": int(evidence.get("case_count", len(case_summaries))),
        "cases": case_summaries,
    }


def _validate_skill_handler_binding(handler: object) -> dict[str, str]:
    if not isinstance(handler, dict):
        raise EvidenceError("skill handler binding must be an object")

    name = str(handler.get("name", ""))
    version = str(handler.get("version", ""))
    handler_id = str(handler.get("handler_id", ""))
    if not name or not version or not handler_id:
        raise EvidenceError("skill handler binding requires name, version, and handler_id")
    if handler_id != f"{name}@{version}":
        raise EvidenceError(
            f"skill handler binding {handler_id!r} does not match {name}@{version}"
        )
    return {
        "name": name,
        "version": version,
        "handler_id": handler_id,
    }


def env_value(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build production readiness evidence.")
    parser.add_argument("--target-environment", default=env_value("TARGET_ENVIRONMENT", "dev"))
    parser.add_argument(
        "--release-scope",
        default=env_value("RELEASE_SCOPE", "initial-productive-core"),
    )
    parser.add_argument(
        "--certification-mode",
        default=env_value("CERTIFICATION_MODE", "evidence-only"),
    )
    parser.add_argument(
        "--live-runtime-gates-run-url",
        default=env_value("LIVE_RUNTIME_GATES_RUN_URL"),
    )
    parser.add_argument("--ai-gateway-smoke-run-url", default=env_value("AI_GATEWAY_SMOKE_RUN_URL"))
    parser.add_argument("--repository", default=env_value("GITHUB_REPOSITORY"))
    parser.add_argument("--commit", default=env_value("GITHUB_SHA"))
    parser.add_argument("--workflow-run-id", default=env_value("GITHUB_RUN_ID"))
    parser.add_argument("--workflow-run-attempt", default=env_value("GITHUB_RUN_ATTEMPT", "1"))
    parser.add_argument("--output", type=Path, default=Path("production-readiness-evidence.json"))
    parser.add_argument("--live-runtime-gates-metadata", type=Path)
    parser.add_argument("--ai-gateway-smoke-metadata", type=Path)
    parser.add_argument("--live-handler-binding-evidence", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--print-run-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.print_run_id:
            ref = parse_actions_run_url(args.print_run_id, args.repository)
            print(ref.run_id)
            return 0

        validate_certification_inputs(
            repository=args.repository,
            target_environment=args.target_environment,
            release_scope=args.release_scope,
            certification_mode=args.certification_mode,
            live_runtime_gates_run_url=args.live_runtime_gates_run_url,
            ai_gateway_smoke_run_url=args.ai_gateway_smoke_run_url,
        )
        if args.validate_only:
            return 0

        evidence = build_evidence(
            repository=args.repository,
            commit=args.commit,
            workflow_run_id=args.workflow_run_id,
            workflow_run_attempt=args.workflow_run_attempt,
            target_environment=args.target_environment,
            release_scope=args.release_scope,
            certification_mode=args.certification_mode,
            live_runtime_gates_run_url=args.live_runtime_gates_run_url,
            ai_gateway_smoke_run_url=args.ai_gateway_smoke_run_url,
            live_runtime_gates_metadata=metadata_from_path(args.live_runtime_gates_metadata),
            ai_gateway_smoke_metadata=metadata_from_path(args.ai_gateway_smoke_metadata),
            live_handler_binding_evidence=metadata_from_path(
                args.live_handler_binding_evidence
  