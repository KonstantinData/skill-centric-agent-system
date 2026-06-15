from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

RUNTIME_OUTPUT_CONTRACT_VERSION = "0.1.0"
TASK_OUTPUT_VALIDATORS = {
    "review-findings-contract": "code-review",
    "research-output-contract": "research",
    "task-execution-output-contract": "task-execution",
    "general-output-contract": "general-task",
}


class RuntimeValidationError(RuntimeError):
    """Raised when profile-selected validation fails."""

    stop_reason = "validator_failed"


@dataclass(frozen=True)
class RuntimeValidationOutcome:
    validator_id: str
    status: str
    findings: Mapping[str, Any]


class RuntimeValidator(Protocol):
    validator_id: str

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome: ...


class RuntimeProfileSchemaValidator:
    validator_id = "runtime-profile-schema"

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome:
        missing = [
            field
            for field in (
                "id",
                "profile_version",
                "instructions",
                "tools",
                "module_versions",
                "limits",
                "validators",
            )
            if field not in profile
        ]
        status = "failed" if missing else "passed"
        return RuntimeValidationOutcome(
            validator_id=self.validator_id,
            status=status,
            findings={
                "status": status,
                "missing_profile_fields": missing,
            },
        )


class TenantProfileValidator:
    validator_id = "tenant-profile-validator"

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome:
        tenant_context = profile.get("tenant_context")
        tenant_authority = profile.get("tenant_authority")
        errors: list[str] = []

        if not isinstance(tenant_context, Mapping):
            errors.append("tenant_context_missing")
        elif tenant_context.get("tenant_id") == "global":
            if tenant_authority is not None:
                errors.append("global_tenant_authority_present")
        elif not isinstance(tenant_authority, Mapping):
            errors.append("tenant_authority_missing")
        else:
            if tenant_authority.get("tenant_id") != tenant_context.get("tenant_id"):
                errors.append("tenant_id_mismatch")
            if tenant_authority.get("area_id") != tenant_context.get("area_id"):
                errors.append("area_id_mismatch")
            hostname = tenant_authority.get("hostname")
            if not isinstance(hostname, Mapping):
                errors.append("hostname_authority_missing")
            else:
                if hostname.get("tenant_id") != tenant_context.get("tenant_id"):
                    errors.append("hostname_tenant_id_mismatch")
                if hostname.get("hostname") != tenant_context.get("hostname"):
                    errors.append("hostname_mismatch")
            if tenant_authority.get("direct_user_grants_allowed") is not False:
                errors.append("direct_user_grants_enabled")

            membership = tenant_authority.get("membership")
            if not isinstance(membership, Mapping):
                errors.append("membership_missing")
            else:
                auth_context = profile.get("auth_context", {})
                principal = (
                    auth_context.get("principal", {})
                    if isinstance(auth_context, Mapping)
                    else {}
                )
                principal_id = principal.get("id") if isinstance(principal, Mapping) else None
                if membership.get("id") != tenant_context.get("membership_id"):
                    errors.append("membership_id_mismatch")
                if membership.get("principal_id") != principal_id:
                    errors.append("membership_principal_mismatch")

        return _validator_outcome(self.validator_id, errors)


class NoCrossTenantScopeValidator:
    validator_id = "no-cross-tenant-scope-validator"

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome:
        return _validate_scopes_against_tenant_authority(
            self.validator_id,
            profile,
            scope_fields=("knowledge_scopes", "data_scopes", "memory_scopes"),
        )


class NoCrossAreaScopeValidator:
    validator_id = "no-cross-area-scope-validator"

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome:
        tenant_context = profile.get("tenant_context")
        tenant_authority = profile.get("tenant_authority")
        errors: list[str] = []
        if isinstance(tenant_context, Mapping) and tenant_context.get("tenant_id") != "global":
            if not isinstance(tenant_authority, Mapping):
                errors.append("tenant_authority_missing")
            elif tenant_context.get("area_id") != tenant_authority.get("area_id"):
                errors.append("area_id_mismatch")
        return _validator_outcome(self.validator_id, errors)


class KnowledgeScopeValidator:
    validator_id = "knowledge-scope-validator"

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome:
        return _validate_scopes_against_tenant_authority(
            self.validator_id,
            profile,
            scope_fields=("knowledge_scopes",),
        )


class RuntimeOutputContractValidator:
    def __init__(self, validator_id: str, task_type: str) -> None:
        self.validator_id = validator_id
        self.task_type = task_type

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome:
        tool_results = execution.get("tool_results", [])
        runtime_output = response.get("runtime_output")
        has_required_response = _has_required_response(response)
        has_tool_result_count = response.get("tool_result_count") == len(tool_results)
        output_errors = _runtime_output_errors(runtime_output, self.task_type)
        status = (
            "passed"
            if has_required_response and has_tool_result_count and not output_errors
            else "failed"
        )
        return RuntimeValidationOutcome(
            validator_id=self.validator_id,
            status=status,
            findings={
                "status": status,
                "required_response_fields_present": has_required_response,
                "tool_result_count_matches_execution": has_tool_result_count,
                "tool_result_count": len(tool_results),
                "runtime_output_errors": output_errors,
            },
        )


class RuntimeValidatorFramework:
    """Run the validators selected by the active Runtime Agent Profile."""

    def __init__(
        self,
        validators: Mapping[str, RuntimeValidator] | None = None,
    ) -> None:
        builtin_validators: dict[str, RuntimeValidator] = {
            "runtime-profile-schema": RuntimeProfileSchemaValidator(),
            "tenant-profile-validator": TenantProfileValidator(),
            "no-cross-tenant-scope-validator": NoCrossTenantScopeValidator(),
            "no-cross-area-scope-validator": NoCrossAreaScopeValidator(),
            "knowledge-scope-validator": KnowledgeScopeValidator(),
            **{
                validator_id: RuntimeOutputContractValidator(validator_id, task_type)
                for validator_id, task_type in TASK_OUTPUT_VALIDATORS.items()
            },
        }
        self.validators = {**builtin_validators, **dict(validators or {})}

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> tuple[RuntimeValidationOutcome, ...]:
        outcomes: list[RuntimeValidationOutcome] = []
        for validator_id in profile.get("validators", []):
            validator = self.validators.get(str(validator_id))
            if validator is None:
                outcomes.append(
                    RuntimeValidationOutcome(
                        validator_id=str(validator_id),
                        status="failed",
                        findings={
                            "status": "failed",
                            "reason": "validator_not_registered",
                        },
                    )
                )
                continue
            outcomes.append(
                validator.validate(
                    profile=profile,
                    execution=execution,
                    response=response,
                )
            )
        return tuple(outcomes)


def assert_validation_passed(outcomes: tuple[RuntimeValidationOutcome, ...]) -> None:
    failed = [outcome.validator_id for outcome in outcomes if outcome.status == "failed"]
    if failed:
        validators = ", ".join(failed)
        raise RuntimeValidationError(f"Runtime validation failed: {validators}.")


def _has_required_response(response: Mapping[str, Any]) -> bool:
    return all(
        field in response
        for field in (
            "run_id",
            "task_id",
            "profile_id",
            "task_type",
            "status",
            "summary",
            "runtime_output",
        )
    )


def _runtime_output_errors(value: Any, expected_task_type: str) -> list[str]:
    if not isinstance(value, Mapping):
        return ["runtime_output_missing"]

    errors: list[str] = []
    if value.get("contract_version") != RUNTIME_OUTPUT_CONTRACT_VERSION:
        errors.append("invalid_contract_version")
    if value.get("task_type") != expected_task_type:
        errors.append("task_type_mismatch")
    if value.get("status") not in {"completed", "blocked", "failed"}:
        errors.append("invalid_status")
    if not isinstance(value.get("summary"), str) or not str(value.get("summary")).strip():
        errors.append("summary_missing")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list):
        errors.append("artifacts_not_array")
    details = value.get("details")
    if not isinstance(details, Mapping):
        errors.append("details_missing")
        return errors

    if expected_task_type == "code-review":
        errors.extend(_require_array(details, "findings"))
        errors.extend(_require_array(details, "reviewed_artifacts"))
    elif expected_task_type == "research":
        errors.extend(_require_non_empty_array(details, "key_points"))
        errors.extend(_require_array(details, "sources"))
        errors.extend(_require_array(details, "open_questions"))
    elif expected_task_type == "task-execution":
        errors.extend(_require_non_empty_array(details, "planned_changes"))
        errors.extend(_require_array(details, "executed_actions"))
        errors.extend(_require_array(details, "blocked_actions"))
    elif expected_task_type == "general-task":
        errors.extend(_require_non_empty_array(details, "notes"))
    else:
        errors.append("unsupported_task_type")

    return errors


def _validate_scopes_against_tenant_authority(
    validator_id: str,
    profile: Mapping[str, Any],
    *,
    scope_fields: tuple[str, ...],
) -> RuntimeValidationOutcome:
    tenant_context = profile.get("tenant_context")
    if not isinstance(tenant_context, Mapping) or tenant_context.get("tenant_id") == "global":
        return _validator_outcome(validator_id, [])

    authority = profile.get("tenant_authority")
    if not isinstance(authority, Mapping):
        return _validator_outcome(validator_id, ["tenant_authority_missing"])

    authority_field_by_profile_field = {
        "knowledge_scopes": "allowed_knowledge_scopes",
        "data_scopes": "allowed_data_scopes",
        "memory_scopes": "allowed_memory_scopes",
    }
    errors: list[str] = []
    for field in scope_fields:
        authority_field = authority_field_by_profile_field[field]
        selected = _string_set(profile.get(field, []))
        allowed = _string_set(authority.get(authority_field, []))
        denied = sorted(selected - allowed)
        if denied:
            errors.append(f"{field}_not_allowed:{','.join(denied)}")
    return _validator_outcome(validator_id, errors)


def _validator_outcome(validator_id: str, errors: list[str]) -> RuntimeValidationOutcome:
    status = "failed" if errors else "passed"
    return RuntimeValidationOutcome(
        validator_id=validator_id,
        status=status,
        findings={
            "status": status,
            "errors": errors,
        },
    )


def _string_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if str(value).strip()}


def _require_array(value: Mapping[str, Any], field: str) -> list[str]:
    if not isinstance(value.get(field), list):
        return [f"{field}_not_array"]
    return []


def _require_non_empty_array(value: Mapping[str, Any], field: str) -> list[str]:
    errors = _require_array(value, field)
    if errors:
        return errors
    if not value[field]:
        return [f"{field}_empty"]
    return []
