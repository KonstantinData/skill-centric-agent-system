from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


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


class MinimalResponseContractValidator:
    validator_id = "review-findings-contract"

    def validate(
        self,
        *,
        profile: Mapping[str, Any],
        execution: Mapping[str, Any],
        response: Mapping[str, Any],
    ) -> RuntimeValidationOutcome:
        tool_results = execution.get("tool_results", [])
        has_required_response = all(
            field in response for field in ("run_id", "profile_id", "status", "summary")
        )
        has_tool_result_count = response.get("tool_result_count") == len(tool_results)
        status = "passed" if has_required_response and has_tool_result_count else "failed"
        return RuntimeValidationOutcome(
            validator_id=self.validator_id,
            status=status,
            findings={
                "status": status,
                "required_response_fields_present": has_required_response,
                "tool_result_count_matches_execution": has_tool_result_count,
                "tool_result_count": len(tool_results),
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
            "review-findings-contract": MinimalResponseContractValidator(),
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
