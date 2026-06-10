from __future__ import annotations

import pytest

from skill_centric_agent_system.runtime.policy_denials import (
    PolicyDenialLedger,
    PolicyDenialLedgerError,
    ScopePolicyClosure,
    build_policy_denial_record,
    validate_policy_denial_record,
)


def denial_request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "record_id": "pdl-profile-code-review-repository-readonly",
        "profile_id": "profile-code-review",
        "principal_id": "repository-maintainer",
        "denial_predicate": "data_scope_not_in_runtime_profile",
        "requested_authority_kind": "data_scope",
        "requested_authority_id": "repository-readonly",
        "policy_id": "no-destructive-commands",
        "closure_version": "scope-policy-closure-0-1-0",
    }
    request.update(overrides)
    return request


def test_policy_denial_ledger_deduplicates_exact_denial_fingerprint() -> None:
    record = build_policy_denial_record(**denial_request())
    ledger = PolicyDenialLedger([record])

    result = ledger.lookup(denial_request(record_id="new-record-id"))

    assert result.denied
    assert result.matched_record_id == "pdl-profile-code-review-repository-readonly"
    assert result.matched_by == "fingerprint"


def test_policy_denial_ledger_subsumes_denied_child_scope_through_closure() -> None:
    closure = ScopePolicyClosure(
        [
            {
                "closure_version": "scope-policy-closure-0-1-0",
                "scope_kind": "data_scope",
                "ancestor_scope_id": "repository-root",
                "descendant_scope_id": "repository-readonly",
                "policy_id": "no-destructive-commands",
                "non_authoritative": True,
                "authority_effect": "reachability_only",
            }
        ]
    )
    record = build_policy_denial_record(
        **denial_request(
            record_id="pdl-profile-code-review-repository-root",
            requested_authority_id="repository-root",
        )
    )
    ledger = PolicyDenialLedger([record], closure=closure)

    result = ledger.lookup(denial_request())

    assert result.denied
    assert result.matched_record_id == "pdl-profile-code-review-repository-root"
    assert result.matched_by == "scope_closure"


def test_policy_denial_ledger_does_not_cross_policy_or_profile_boundaries() -> None:
    closure = ScopePolicyClosure(
        [
            {
                "closure_version": "scope-policy-closure-0-1-0",
                "scope_kind": "data_scope",
                "ancestor_scope_id": "repository-root",
                "descendant_scope_id": "repository-readonly",
                "policy_id": "no-destructive-commands",
                "non_authoritative": True,
                "authority_effect": "reachability_only",
            }
        ]
    )
    record = build_policy_denial_record(
        **denial_request(
            record_id="pdl-profile-code-review-repository-root",
            requested_authority_id="repository-root",
        )
    )
    ledger = PolicyDenialLedger([record], closure=closure)

    result = ledger.lookup(denial_request(policy_id="different-policy"))

    assert not result.denied
    assert result.reason == "no matching denial"


def test_policy_denial_records_cannot_grant_authority() -> None:
    record = dict(build_policy_denial_record(**denial_request()))
    record["authority_grant"] = {"tools": ["git-write"]}

    with pytest.raises(PolicyDenialLedgerError, match="authority_grant"):
        validate_policy_denial_record(record)

    record = dict(build_policy_denial_record(**denial_request()))
    record["authority_effect"] = "scope_grant"

    with pytest.raises(PolicyDenialLedgerError, match="deny_only"):
        validate_policy_denial_record(record)
