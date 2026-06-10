from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

DENIABLE_AUTHORITY_KINDS = frozenset(
    {
        "tool",
        "policy",
        "data_scope",
        "knowledge_scope",
        "memory_scope",
        "validator",
        "budget",
        "failure_policy",
    }
)
DENIAL_STATUSES = frozenset({"active", "expired", "superseded"})


class PolicyDenialLedgerError(ValueError):
    """Raised when a denial ledger record or closure entry is unsafe."""


@dataclass(frozen=True)
class PolicyDenialLookup:
    denied: bool
    reason: str
    matched_record_id: str | None = None
    matched_by: str | None = None


class ScopePolicyClosure:
    """Metadata-only reachability table for already-approved scope/policy closure."""

    def __init__(self, entries: Iterable[Mapping[str, Any]] = ()) -> None:
        self.entries = tuple(_validate_closure_entry(entry) for entry in entries)

    def descendants_for(
        self,
        *,
        scope_kind: str,
        ancestor_scope_id: str,
        policy_id: str,
        closure_version: str,
    ) -> frozenset[str]:
        descendants = {
            str(entry["descendant_scope_id"])
            for entry in self.entries
            if entry["scope_kind"] == scope_kind
            and entry["ancestor_scope_id"] == ancestor_scope_id
            and entry["policy_id"] == policy_id
            and entry["closure_version"] == closure_version
        }
        return frozenset(descendants)

    def is_descendant(
        self,
        *,
        scope_kind: str,
        ancestor_scope_id: str,
        requested_scope_id: str,
        policy_id: str,
        closure_version: str,
    ) -> bool:
        if ancestor_scope_id == requested_scope_id:
            return True
        return requested_scope_id in self.descendants_for(
            scope_kind=scope_kind,
            ancestor_scope_id=ancestor_scope_id,
            policy_id=policy_id,
            closure_version=closure_version,
        )


class PolicyDenialLedger:
    """Deduplicate policy denials without granting authority."""

    def __init__(
        self,
        records: Iterable[Mapping[str, Any]] = (),
        *,
        closure: ScopePolicyClosure | None = None,
    ) -> None:
        self.records = tuple(validate_policy_denial_record(record) for record in records)
        self.closure = closure or ScopePolicyClosure()

    def lookup(
        self,
        request: Mapping[str, Any],
    ) -> PolicyDenialLookup:
        request_record = build_policy_denial_record(**dict(request))
        request_fingerprint = str(request_record["denial_fingerprint"])
        for record in self.records:
            if record["status"] != "active":
                continue
            if record["denial_fingerprint"] == request_fingerprint:
                return PolicyDenialLookup(
                    denied=True,
                    reason="exact denial fingerprint already exists",
                    matched_record_id=str(record["id"]),
                    matched_by="fingerprint",
                )
            if _scope_denial_subsumes(
                record=record,
                request=request_record,
                closure=self.closure,
            ):
                return PolicyDenialLookup(
                    denied=True,
                    reason="requested scope is subsumed by an existing denied scope",
                    matched_record_id=str(record["id"]),
                    matched_by="scope_closure",
                )
        return PolicyDenialLookup(denied=False, reason="no matching denial")


def build_policy_denial_record(
    *,
    record_id: str,
    profile_id: str,
    principal_id: str,
    denial_predicate: str,
    requested_authority_kind: str,
    requested_authority_id: str,
    policy_id: str,
    closure_version: str,
    status: str = "active",
    ttl_expires_at: str | None = None,
) -> Mapping[str, Any]:
    record = {
        "contract_version": "0.1.0",
        "id": record_id,
        "profile_id": profile_id,
        "principal_id": principal_id,
        "denial_predicate": denial_predicate,
        "requested_authority": {
            "kind": requested_authority_kind,
            "id": requested_authority_id,
        },
        "policy_id": policy_id,
        "closure_version": closure_version,
        "denial_fingerprint": _denial_fingerprint(
            profile_id=profile_id,
            principal_id=principal_id,
            denial_predicate=denial_predicate,
            requested_authority_kind=requested_authority_kind,
            requested_authority_id=requested_authority_id,
            policy_id=policy_id,
            closure_version=closure_version,
        ),
        "status": status,
        "ttl_expires_at": ttl_expires_at,
        "non_authoritative": True,
        "authority_effect": "deny_only",
    }
    return validate_policy_denial_record(record)


def validate_policy_denial_record(record: Mapping[str, Any]) -> Mapping[str, Any]:
    required = {
        "contract_version",
        "id",
        "profile_id",
        "principal_id",
        "denial_predicate",
        "requested_authority",
        "policy_id",
        "closure_version",
        "denial_fingerprint",
        "status",
        "non_authoritative",
        "authority_effect",
    }
    missing = sorted(field for field in required if field not in record)
    if missing:
        raise PolicyDenialLedgerError("missing fields: " + ", ".join(missing))
    if record["contract_version"] != "0.1.0":
        raise PolicyDenialLedgerError("contract_version must be 0.1.0")
    requested = record["requested_authority"]
    if not isinstance(requested, Mapping):
        raise PolicyDenialLedgerError("requested_authority must be an object")
    if requested.get("kind") not in DENIABLE_AUTHORITY_KINDS:
        raise PolicyDenialLedgerError("requested_authority.kind is invalid")
    if not str(requested.get("id", "")).strip():
        raise PolicyDenialLedgerError("requested_authority.id is required")
    if record["status"] not in DENIAL_STATUSES:
        raise PolicyDenialLedgerError("status is invalid")
    if record["non_authoritative"] is not True:
        raise PolicyDenialLedgerError("denial records must be non_authoritative")
    if record["authority_effect"] != "deny_only":
        raise PolicyDenialLedgerError("denial records must be deny_only")
    for forbidden in (
        "authority_grant",
        "granted_authority",
        "profile_patch",
        "runtime_profile_patch",
        "scope_grant",
        "policy_override",
    ):
        if forbidden in record:
            raise PolicyDenialLedgerError(f"denial records must not contain {forbidden}")
    return dict(record)


def _validate_closure_entry(entry: Mapping[str, Any]) -> Mapping[str, Any]:
    required = {
        "closure_version",
        "scope_kind",
        "ancestor_scope_id",
        "descendant_scope_id",
        "policy_id",
        "non_authoritative",
        "authority_effect",
    }
    missing = sorted(field for field in required if field not in entry)
    if missing:
        raise PolicyDenialLedgerError("closure entry missing fields: " + ", ".join(missing))
    if entry["scope_kind"] not in {"data_scope", "knowledge_scope", "memory_scope"}:
        raise PolicyDenialLedgerError("closure scope_kind is invalid")
    if entry["non_authoritative"] is not True:
        raise PolicyDenialLedgerError("closure entries must be non_authoritative")
    if entry["authority_effect"] != "reachability_only":
        raise PolicyDenialLedgerError("closure entries must be reachability_only")
    return dict(entry)


def _scope_denial_subsumes(
    *,
    record: Mapping[str, Any],
    request: Mapping[str, Any],
    closure: ScopePolicyClosure,
) -> bool:
    denied = record["requested_authority"]
    requested = request["requested_authority"]
    if not isinstance(denied, Mapping) or not isinstance(requested, Mapping):
        return False
    if denied.get("kind") != requested.get("kind"):
        return False
    if denied.get("kind") not in {"data_scope", "knowledge_scope", "memory_scope"}:
        return False
    if record.get("profile_id") != request.get("profile_id"):
        return False
    if record.get("principal_id") != request.get("principal_id"):
        return False
    if record.get("policy_id") != request.get("policy_id"):
        return False
    return closure.is_descendant(
        scope_kind=str(denied["kind"]),
        ancestor_scope_id=str(denied["id"]),
        requested_scope_id=str(requested["id"]),
        policy_id=str(record["policy_id"]),
        closure_version=str(record["closure_version"]),
    )


def _denial_fingerprint(
    *,
    profile_id: str,
    principal_id: str,
    denial_predicate: str,
    requested_authority_kind: str,
    requested_authority_id: str,
    policy_id: str,
    closure_version: str,
) -> str:
    payload = {
        "closure_version": closure_version,
        "denial_predicate": denial_predicate,
        "policy_id": policy_id,
        "principal_id": principal_id,
        "profile_id": profile_id,
        "requested_authority": {
            "id": requested_authority_id,
            "kind": requested_authority_kind,
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
