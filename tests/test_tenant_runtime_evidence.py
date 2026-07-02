from __future__ import annotations

# ruff: noqa: F403,F405,I001

from copy import deepcopy

from tests.contract_schema_support import *  # noqa: F403
from tests.tenant_authority_support import tenant_authority_paths

TENANT_RUNTIME_EVIDENCE_DIR = REPO_ROOT / "examples" / "runtime-evidence"
REQUIRED_SIGNALS = {
    "queue",
    "worker",
    "quota",
    "dlq",
    "stale_claim_recovery",
}
SENSITIVE_VALUE_MARKERS = (
    "bearer ",
    "private_key",
    "password",
    "api_token",
    "access_token",
    "refresh_token",
    "raw trace",
    "raw tool output",
    "geburtsdatum",
    "diagnose",
    "personalakte",
)


def tenant_examples() -> dict[str, dict[str, Any]]:
    return {
        tenant["tenant_id"]: tenant
        for tenant in (
            load_json(path) for path in tenant_authority_paths()
        )
    }


def active_or_setup_tenants() -> dict[str, dict[str, Any]]:
    return {
        tenant_id: tenant
        for tenant_id, tenant in tenant_examples().items()
        if tenant["status"] in {"active", "setup"}
    }


def tenant_runtime_evidence_examples() -> dict[str, dict[str, Any]]:
    return {
        evidence["tenant_id"]: evidence
        for evidence in (
            load_json(path) for path in sorted(TENANT_RUNTIME_EVIDENCE_DIR.glob("*.json"))
        )
    }


def string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(string_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(string_values(item))
        return values
    return []


def assert_tenant_runtime_evidence_is_registry_local(
    evidence: dict[str, Any],
    tenant: dict[str, Any],
    all_tenant_ids: set[str],
) -> None:
    tenant_id = tenant["tenant_id"]
    assert evidence["tenant_id"] == tenant_id
    assert evidence["area_id"] == tenant["area_id"]
    assert evidence["source_recordset_uri"].startswith(
        f"hetzner://runtime/{evidence['environment']}/evidence/{tenant_id}/"
    )
    assert evidence["certification_level"] == "dev-fixture"
    assert evidence["evidence_scope"] == "fixture"
    assert evidence["environment"] == "dev"
    assert evidence["status"] == "passed"

    artifact_uris = set(evidence["source_artifact_uris"])
    assert artifact_uris
    for artifact_uri in artifact_uris:
        assert f"/evidence/{tenant_id}/" in artifact_uri

    signals = evidence["signals"]
    assert set(signals) == REQUIRED_SIGNALS
    for signal_name, signal in signals.items():
        assert signal["observed"] is True, f"{tenant_id} {signal_name} is not observed"
        assert signal["status"] == "passed", f"{tenant_id} {signal_name} did not pass"
        assert signal["evidence_uri"] in artifact_uris

    queue = signals["queue"]
    assert queue["queue_items_total"] == (
        queue["queued"]
        + queue["claiming"]
        + queue["running"]
        + queue["succeeded"]
        + queue["failed"]
        + queue["cancelled"]
        + queue["retry_scheduled"]
        + queue["dead_lettered"]
    )
    assert queue["queue_items_total"] > 0

    worker = signals["worker"]
    assert worker["claims_total"] == worker["active_claims"] + worker["released_claims"]

    dlq = signals["dlq"]
    assert dlq["dead_letters_total"] == (
        dlq["retryable_dead_letters"] + dlq["non_retryable_dead_letters"]
    )

    stale = signals["stale_claim_recovery"]
    assert stale["stale_claims_detected"] == (
        stale["recovered_claims"] + stale["unrecovered_claims"]
    )
    assert stale["unrecovered_claims"] == 0

    validation = evidence["validation"]
    assert validation == {
        "tenant_registry_match": "passed",
        "runtime_profile_schema": "passed",
        "runtime_api_queue_summary_schema": "passed",
        "hetzner_runtime_plane_schema": "passed",
        "cross_tenant_contamination": "none-detected",
        "sensitive_data_scan": "passed",
    }

    sanitization = evidence["sanitization"]
    assert sanitization["raw_traces_included"] is False
    assert sanitization["raw_tool_outputs_included"] is False
    assert sanitization["secrets_included"] is False
    assert sanitization["personal_data_included"] is False
    assert sanitization["retention_plane"] == "hetzner-runtime-plane"

    serialized_values = "\n".join(string_values(evidence)).lower()
    for other_tenant_id in all_tenant_ids - {tenant_id}:
        assert other_tenant_id not in serialized_values
    for marker in SENSITIVE_VALUE_MARKERS:
        assert marker not in serialized_values


def test_tenant_runtime_evidence_schema_is_valid(
    tenant_runtime_evidence_schema: dict[str, Any],
) -> None:
    assert tenant_runtime_evidence_schema["$id"] == (
        "urn:scas:schema:tenant-runtime-evidence:0.1.0"
    )


def test_all_tenant_runtime_evidence_examples_match_schema(
    tenant_runtime_evidence_schema: dict[str, Any],
) -> None:
    for path in sorted(TENANT_RUNTIME_EVIDENCE_DIR.glob("*.json")):
        assert_valid(tenant_runtime_evidence_schema, load_json(path))


def test_every_active_or_setup_tenant_has_sanitized_runtime_evidence(
    tenant_runtime_evidence_schema: dict[str, Any],
) -> None:
    tenants = active_or_setup_tenants()
    evidence_by_tenant = tenant_runtime_evidence_examples()

    assert set(evidence_by_tenant) == set(tenants)
    for tenant_id, tenant in tenants.items():
        evidence = evidence_by_tenant[tenant_id]
        assert_valid(tenant_runtime_evidence_schema, evidence)
        assert_tenant_runtime_evidence_is_registry_local(
            evidence,
            tenant,
            set(tenants),
        )


def test_tenant_runtime_evidence_rejects_missing_required_signal(
    tenant_runtime_evidence_schema: dict[str, Any],
) -> None:
    evidence = deepcopy(tenant_runtime_evidence_examples()["tenant-under-test"])
    evidence["signals"].pop("dlq")

    assert_invalid(tenant_runtime_evidence_schema, evidence, "'dlq' is a required property")


def test_tenant_runtime_evidence_rejects_prod_fixture_claim(
    tenant_runtime_evidence_schema: dict[str, Any],
) -> None:
    evidence = deepcopy(tenant_runtime_evidence_examples()["tenant-under-test"])
    evidence["environment"] = "prod"

    assert_invalid(tenant_runtime_evidence_schema, evidence, "'target-environment' was expected")


def test_tenant_runtime_evidence_rejects_secret_inclusion(
    tenant_runtime_evidence_schema: dict[str, Any],
) -> None:
    evidence = deepcopy(tenant_runtime_evidence_examples()["tenant-under-test"])
    evidence["sanitization"]["secrets_included"] = True

    assert_invalid(tenant_runtime_evidence_schema, evidence, "False was expected")


def test_tenant_runtime_evidence_detects_cross_tenant_artifact_uri() -> None:
    tenants = active_or_setup_tenants()
    evidence = deepcopy(tenant_runtime_evidence_examples()["tenant-under-test"])
    foreign_tenant_id = next(
        tenant_id for tenant_id in sorted(tenants) if tenant_id != "tenant-under-test"
    )
    evidence["source_artifact_uris"][0] = (
        f"hetzner://runtime/dev/evidence/{foreign_tenant_id}/queue-summary.json"
    )

    with pytest.raises(AssertionError):
        assert_tenant_runtime_evidence_is_registry_local(
            evidence,
            tenants["tenant-under-test"],
            set(tenants),
        )
