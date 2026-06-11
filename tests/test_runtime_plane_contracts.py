from __future__ import annotations

# ruff: noqa: F403,F405,I001

from copy import deepcopy
from tests.contract_schema_support import *  # noqa: F403


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda runtime_plane: runtime_plane["records"]["runtime_runs"][0].pop("id"),
            "'id' is a required property",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["runtime_steps"][0].pop(
                "idempotency_key"
            ),
            "'idempotency_key' is a required property",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["runtime_events"][0].__setitem__(
                "event_type",
                "freeform_event",
            ),
            "'freeform_event' is not one of",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["runtime_events"][0].__setitem__(
                "actor_role",
                "freeform_actor",
            ),
            "'freeform_actor' is not one of",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["runtime_events"][0].__setitem__(
                "planned_action_json",
                {},
            ),
            "Additional properties are not allowed",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["memory_candidates"][0].pop(
                "validator_status"
            ),
            "'validator_status' is a required property",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["memory_candidates"][0].pop(
                "policy_status"
            ),
            "'policy_status' is a required property",
        ),
        (
            lambda runtime_plane: runtime_plane["records"]["memory_candidates"][0].pop(
                "candidate_class"
            ),
            "'candidate_class' is a required property",
        ),
    ],
)
def test_invalid_runtime_plane_records_are_rejected_by_schema(
    runtime_plane_schema: dict[str, Any],
    runtime_plane_example: dict[str, Any],
    mutator: Any,
    message_part: str,
) -> None:
    invalid_runtime_plane = deepcopy(runtime_plane_example)
    mutator(invalid_runtime_plane)

    assert_invalid(runtime_plane_schema, invalid_runtime_plane, message_part)


def test_runtime_plane_rejects_invalid_runtime_reference(
    runtime_plane_schema: dict[str, Any],
    runtime_plane_example: dict[str, Any],
) -> None:
    invalid_runtime_plane = deepcopy(runtime_plane_example)
    invalid_runtime_plane["records"]["memory_candidates"][0]["source_step_id"] = "missing-step"

    assert_valid(runtime_plane_schema, invalid_runtime_plane)
    with pytest.raises(AssertionError):
        assert_runtime_plane_references_are_valid(invalid_runtime_plane)


def test_runtime_plane_rejects_invalid_event_reference(
    runtime_plane_schema: dict[str, Any],
    runtime_plane_example: dict[str, Any],
) -> None:
    invalid_runtime_plane = deepcopy(runtime_plane_example)
    invalid_runtime_plane["records"]["runtime_events"][1]["step_id"] = "missing-step"

    assert_valid(runtime_plane_schema, invalid_runtime_plane)
    with pytest.raises(AssertionError):
        assert_runtime_plane_references_are_valid(invalid_runtime_plane)
