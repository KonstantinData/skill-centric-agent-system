from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BLOCKING_GATES = frozenset(
    {"freeze_prior", "needs_human_review", "needs_more_evidence", "reject"}
)
AUTHORITY_DELTAS = frozenset(
    {
        "tool_addition",
        "scope_expansion",
        "budget_increase",
        "validator_removal",
        "failure_mode_relaxation",
        "policy_exception",
        "data_access_expansion",
        "memory_scope_expansion",
        "knowledge_scope_expansion",
    }
)


class SafetyCompilerError(ValueError):
    """Raised when learned context cannot be compiled safely."""


@dataclass(frozen=True)
class SafetyCompilerDecision:
    decision: str
    automatic_promotion_allowed: bool
    matched_pair_ids: tuple[str, ...]
    authority_delta: tuple[str, ...]
    reviewed_policy_artifacts: tuple[str, ...]
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "automatic_promotion_allowed": self.automatic_promotion_allowed,
            "matched_pair_ids": list(self.matched_pair_ids),
            "authority_delta": list(self.authority_delta),
            "reviewed_policy_artifacts": list(self.reviewed_policy_artifacts),
            "reason": self.reason,
        }


class SafetyCompiler:
    """Compile learned-context influence into deterministic promotion gates."""

    def __init__(self, guard_policy: Mapping[str, Any]) -> None:
        self.guard_policy = dict(guard_policy)
        failures = self._validate_guard_policy(self.guard_policy)
        if failures:
            raise SafetyCompilerError("Invalid semantic drift guard policy: " + "; ".join(failures))

    @classmethod
    def from_policy_file(cls, path: Path) -> SafetyCompiler:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SafetyCompilerError(f"{path} must contain a JSON object.")
        return cls(payload)

    def compile_learned_authority_prior(
        self,
        prior: Mapping[str, Any],
        *,
        reviewed_policy_artifacts: Iterable[str] = (),
    ) -> SafetyCompilerDecision:
        authority_delta = tuple(
            sorted(
                {
                    str(delta)
                    for delta in prior.get("authority_delta", [])
                    if isinstance(delta, str)
                }
            )
        )
        reviewed_artifacts = tuple(
            sorted(
                {
                    artifact.strip()
                    for artifact in reviewed_policy_artifacts
                    if artifact.strip()
                }
            )
        )

        if not authority_delta:
            return SafetyCompilerDecision(
                decision="allow_ranking_only",
                automatic_promotion_allowed=True,
                matched_pair_ids=(),
                authority_delta=(),
                reviewed_policy_artifacts=reviewed_artifacts,
                reason="Learned context changes ranking only and carries no authority delta.",
            )

        matched_pairs = self._matching_pairs(prior, authority_delta)
        if matched_pairs:
            return SafetyCompilerDecision(
                decision=self._strongest_gate(matched_pairs),
                automatic_promotion_allowed=False,
                matched_pair_ids=tuple(pair["pair_id"] for pair in matched_pairs),
                authority_delta=authority_delta,
                reviewed_policy_artifacts=reviewed_artifacts,
                reason="Learned authority delta matches a forbidden contrastive boundary.",
            )

        if not reviewed_artifacts:
            return SafetyCompilerDecision(
                decision="reject",
                automatic_promotion_allowed=False,
                matched_pair_ids=(),
                authority_delta=authority_delta,
                reviewed_policy_artifacts=(),
                reason="Learned authority delta has no reviewed policy artifact.",
            )

        return SafetyCompilerDecision(
            decision="allow_ranking_only",
            automatic_promotion_allowed=True,
            matched_pair_ids=(),
            authority_delta=authority_delta,
            reviewed_policy_artifacts=reviewed_artifacts,
            reason=(
                "Authority delta is bound to reviewed policy artifacts; learned context remains "
                "ranking-only."
            ),
        )

    def _matching_pairs(
        self,
        prior: Mapping[str, Any],
        authority_delta: tuple[str, ...],
    ) -> list[dict[str, str]]:
        source_context = _mapping(prior.get("source_context"))
        target_context = _mapping(prior.get("target_context"))
        authority_delta_set = set(authority_delta)

        matches: list[dict[str, str]] = []
        pairs = self.guard_policy.get("contrastive_pairs", [])
        if not isinstance(pairs, list):
            return matches

        for pair in pairs:
            if not isinstance(pair, Mapping):
                continue
            positive_context = _mapping(pair.get("positive_context"))
            forbidden = _mapping(pair.get("forbidden_generalization"))
            forbidden_deltas = {
                str(delta)
                for delta in forbidden.get("authority_delta", [])
                if isinstance(delta, str)
            }
            forbidden_context = {
                key: value for key, value in forbidden.items() if key != "authority_delta"
            }
            if (
                _context_contains(source_context, positive_context)
                and _context_contains(target_context, forbidden_context)
                and bool(authority_delta_set & forbidden_deltas)
            ):
                matches.append(
                    {
                        "pair_id": str(pair["pair_id"]),
                        "decision": str(pair["expected_gate"]),
                    }
                )
        return matches

    @staticmethod
    def _strongest_gate(matches: Iterable[Mapping[str, str]]) -> str:
        priority = {
            "freeze_prior": 1,
            "needs_more_evidence": 2,
            "needs_human_review": 3,
            "reject": 4,
        }
        return max((match["decision"] for match in matches), key=lambda gate: priority[gate])

    @staticmethod
    def _validate_guard_policy(guard: Mapping[str, Any]) -> list[str]:
        failures: list[str] = []
        if guard.get("guard_id") != "semantic-drift-guard":
            failures.append("guard_id must be semantic-drift-guard")
        if guard.get("authority_invariant") != "learned_context_not_authority":
            failures.append("authority_invariant must be learned_context_not_authority")
        if guard.get("default_on_match") not in BLOCKING_GATES:
            failures.append("default_on_match must be a blocking gate")
        pairs = guard.get("contrastive_pairs")
        if not isinstance(pairs, list) or not pairs:
            failures.append("contrastive_pairs must be a non-empty array")
            return failures
        for pair in pairs:
            if not isinstance(pair, Mapping):
                failures.append("each contrastive pair must be an object")
                continue
            forbidden = pair.get("forbidden_generalization")
            if not isinstance(forbidden, Mapping):
                failures.append(f"{pair.get('pair_id', '<unknown>')}: forbidden boundary missing")
                continue
            deltas = forbidden.get("authority_delta")
            if not isinstance(deltas, list) or not deltas:
                failures.append(f"{pair.get('pair_id', '<unknown>')}: authority_delta missing")
            elif any(delta not in AUTHORITY_DELTAS for delta in deltas):
                failures.append(f"{pair.get('pair_id', '<unknown>')}: unknown authority_delta")
            if pair.get("expected_gate") not in BLOCKING_GATES:
                failures.append(f"{pair.get('pair_id', '<unknown>')}: non-blocking gate")
        return failures


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _context_contains(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(actual.get(key) == value for key, value in expected.items())
