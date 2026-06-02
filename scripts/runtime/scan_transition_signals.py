from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCANNER_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES = REPO_ROOT / "examples" / "evaluations" / "transition-signal-scan-cases.json"

REQUIRED_SCANNER_IDS = {
    "path": SCANNER_VERSION,
    "repository_reference": SCANNER_VERSION,
    "write_intent": SCANNER_VERSION,
    "destructive_intent": SCANNER_VERSION,
    "protected_path": SCANNER_VERSION,
    "pull_request_reference": SCANNER_VERSION,
    "branch_reference": SCANNER_VERSION,
    "commit_reference": SCANNER_VERSION,
}

PROTECTED_PATH_PREFIXES = (
    ".github/",
    "docs/adr/",
    "docs/policies/",
    "migrations/",
    "policies/",
    "schemas/",
    "src/skill_centric_agent_system/composition/",
    "src/skill_centric_agent_system/runtime/",
    "workers/control-api/",
)

PATH_PATTERN = re.compile(
    r"(?<![\w.-])("
    r"(?:[A-Za-z]:\\[^\s`'\"<>|]+)"
    r"|(?:https?://[^\s`'\"<>]+)"
    r"|(?:(?:\.github|docs|examples|migrations|policies|schemas|scripts|src|tests|workers)"
    r"/[A-Za-z0-9._~@%+=:,/\\-]+)"
    r"|(?:[A-Za-z0-9_.-]+/[A-Za-z0-9._~@%+=:,/\\-]+)"
    r")"
)
WRITE_INTENT_PATTERN = re.compile(
    r"\b("
    r"apply(?:\s+the\s+fix)?|"
    r"fix|patch|change|update|modify|edit|add|create|write|implement|"
    r"commit|push|merge|open\s+(?:a\s+)?pr|open\s+(?:a\s+)?pull\s+request"
    r")\b",
    re.IGNORECASE,
)
DESTRUCTIVE_INTENT_PATTERN = re.compile(
    r"\b("
    r"delete|remove|drop|destroy|wipe|purge|overwrite|force[-\s]?push|"
    r"reset\s+--hard|rm\s+-rf"
    r")\b",
    re.IGNORECASE,
)
REPOSITORY_REFERENCE_PATTERN = re.compile(
    r"\b(this\s+repo|this\s+repository|repo|repository|working\s+tree)\b",
    re.IGNORECASE,
)
PULL_REQUEST_REFERENCE_PATTERN = re.compile(
    r"\b(PR\s*#?\d+|pull\s+request\s+#?\d+)\b",
    re.IGNORECASE,
)
BRANCH_REFERENCE_PATTERN = re.compile(
    r"\b(?:branch|head|base)\s+[`'\"]?([A-Za-z0-9._/-]+)[`'\"]?",
    re.IGNORECASE,
)
COMMIT_REFERENCE_PATTERN = re.compile(
    r"\b(?:commit\s+)?([a-f0-9]{7,40})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TransitionSignal:
    signal_kind: str
    value: str
    artifact_id: str
    artifact_hash: str
    span: str
    offset_start: int
    offset_end: int
    source: str
    path_kind: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "signal_kind": self.signal_kind,
            "value": self.value,
            "artifact_id": self.artifact_id,
            "artifact_hash": self.artifact_hash,
            "span": self.span,
            "offset_start": self.offset_start,
            "offset_end": self.offset_end,
            "source": self.source,
        }
        if self.path_kind is not None:
            payload["path_kind"] = self.path_kind
        return payload


def scan_transition_signals(
    *,
    artifact_id: str,
    text: str,
) -> list[TransitionSignal]:
    artifact_hash = _sha256(text)
    signals: list[TransitionSignal] = []

    for match in PATH_PATTERN.finditer(text):
        value = _trim_path_token(match.group(1))
        offset_start = match.start(1)
        offset_end = offset_start + len(value)
        if not value or _looks_like_sentence_fragment(value):
            continue
        path_kind = _path_kind(value)
        signals.append(
            _signal(
                "path_reference",
                value,
                artifact_id,
                artifact_hash,
                text,
                offset_start,
                offset_end,
                "scanner:path",
                path_kind=path_kind,
            )
        )
        if _is_protected_path(value):
            signals.append(
                _signal(
                    "protected_path_reference",
                    value,
                    artifact_id,
                    artifact_hash,
                    text,
                    offset_start,
                    offset_end,
                    "scanner:protected_path",
                    path_kind=path_kind,
                )
            )

    signals.extend(
        _pattern_signals(
            text=text,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            pattern=WRITE_INTENT_PATTERN,
            signal_kind="write_intent",
            source="scanner:write_intent",
        )
    )
    signals.extend(
        _pattern_signals(
            text=text,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            pattern=DESTRUCTIVE_INTENT_PATTERN,
            signal_kind="destructive_intent",
            source="scanner:destructive_intent",
        )
    )
    signals.extend(
        _pattern_signals(
            text=text,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            pattern=REPOSITORY_REFERENCE_PATTERN,
            signal_kind="repository_reference",
            source="scanner:repository_reference",
        )
    )
    signals.extend(
        _pattern_signals(
            text=text,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            pattern=PULL_REQUEST_REFERENCE_PATTERN,
            signal_kind="pull_request_reference",
            source="scanner:repository_reference",
        )
    )
    signals.extend(
        _pattern_signals(
            text=text,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            pattern=BRANCH_REFERENCE_PATTERN,
            signal_kind="branch_reference",
            source="scanner:repository_reference",
        )
    )
    signals.extend(
        _pattern_signals(
            text=text,
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            pattern=COMMIT_REFERENCE_PATTERN,
            signal_kind="commit_reference",
            source="scanner:repository_reference",
        )
    )

    return _dedupe_signals(signals)


def scan_evidence_artifacts(evidence: Mapping[str, Any]) -> list[TransitionSignal]:
    signals: list[TransitionSignal] = []
    for artifact in evidence["raw_artifacts"]:
        signals.extend(
            scan_transition_signals(
                artifact_id=str(artifact["artifact_id"]),
                text=str(artifact["text"]),
            )
        )
    return signals


def scanner_coverage_violations(evidence: Mapping[str, Any]) -> list[str]:
    versions = evidence["source"]["scanner_versions"]
    missing_scanners = sorted(set(REQUIRED_SCANNER_IDS) - set(versions))
    violations = [
        f"source.scanner_versions missing required scanner {scanner_id}"
        for scanner_id in missing_scanners
    ]

    for scanner_id, expected_version in REQUIRED_SCANNER_IDS.items():
        if versions.get(scanner_id) not in (None, expected_version):
            violations.append(
                f"source.scanner_versions.{scanner_id} must be {expected_version}"
            )

    for signal in scan_evidence_artifacts(evidence):
        if not _signal_is_covered(evidence, signal):
            violations.append(
                "scanner signal not covered by extracted evidence: "
                f"{signal.signal_kind} {signal.span!r} "
                f"at {signal.artifact_id}:{signal.offset_start}-{signal.offset_end}"
            )
    return violations


def build_scan_report(cases_path: Path = DEFAULT_CASES) -> dict[str, Any]:
    cases = _load_json(cases_path)
    failures: list[str] = []
    case_reports = []
    for case in cases["cases"]:
        signals = scan_transition_signals(
            artifact_id=str(case["artifact_id"]),
            text=str(case["text"]),
        )
        signal_dicts = [signal.to_dict() for signal in signals]
        for expected in case["expected_signals"]:
            if not _expected_signal_present(expected, signal_dicts):
                failures.append(
                    f"{case['case_id']} missing {expected['signal_kind']} "
                    f"{expected['span']!r}"
                )
        case_reports.append(
            {
                "case_id": case["case_id"],
                "signal_count": len(signals),
                "signals": signal_dicts,
            }
        )
    return {
        "scanner_version": SCANNER_VERSION,
        "status": "passed" if not failures else "failed",
        "case_count": len(cases["cases"]),
        "failures": failures,
        "cases": case_reports,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan SCAS transition-critical signals in raw artifacts.",
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_scan_report(args.cases)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if args.check else 2

    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True), end="\n")
    if report["failures"]:
        print("error: transition signal scan fixtures failed", file=sys.stderr)
        return 1 if args.check else 2
    return 0


def _pattern_signals(
    *,
    text: str,
    artifact_id: str,
    artifact_hash: str,
    pattern: re.Pattern[str],
    signal_kind: str,
    source: str,
) -> list[TransitionSignal]:
    signals: list[TransitionSignal] = []
    for match in pattern.finditer(text):
        group_index = 1 if match.lastindex else 0
        span = match.group(group_index)
        signals.append(
            _signal(
                signal_kind,
                span,
                artifact_id,
                artifact_hash,
                text,
                match.start(group_index),
                match.end(group_index),
                source,
            )
        )
    return signals


def _signal(
    signal_kind: str,
    value: str,
    artifact_id: str,
    artifact_hash: str,
    text: str,
    offset_start: int,
    offset_end: int,
    source: str,
    *,
    path_kind: str | None = None,
) -> TransitionSignal:
    return TransitionSignal(
        signal_kind=signal_kind,
        value=value,
        artifact_id=artifact_id,
        artifact_hash=artifact_hash,
        span=text[offset_start:offset_end],
        offset_start=offset_start,
        offset_end=offset_end,
        source=source,
        path_kind=path_kind,
    )


def _signal_is_covered(evidence: Mapping[str, Any], signal: TransitionSignal) -> bool:
    if signal.signal_kind == "path_reference":
        return any(
            _span_covers(path["evidence"], signal)
            for path in evidence["mentioned_paths"]
        )
    if signal.signal_kind == "protected_path_reference":
        return _critical_field_covers(evidence, "protected_path_reference", signal)
    if signal.signal_kind == "write_intent":
        return _critical_field_covers(evidence, "explicit_write_intent", signal)
    if signal.signal_kind == "destructive_intent":
        return _critical_field_covers(evidence, "explicit_destructive_intent", signal)
    if signal.signal_kind in {
        "repository_reference",
        "pull_request_reference",
        "branch_reference",
        "commit_reference",
    }:
        return _critical_field_covers(evidence, "repository_bound", signal)
    return False


def _critical_field_covers(
    evidence: Mapping[str, Any],
    field_name: str,
    signal: TransitionSignal,
) -> bool:
    field = evidence["critical_fields"][field_name]
    return any(_span_covers(span, signal) for span in field["evidence"])


def _span_covers(span: Mapping[str, Any], signal: TransitionSignal) -> bool:
    return (
        span["artifact_id"] == signal.artifact_id
        and span["artifact_hash"] == signal.artifact_hash
        and int(span["offset_start"]) <= signal.offset_start
        and int(span["offset_end"]) >= signal.offset_end
    )


def _expected_signal_present(
    expected: Mapping[str, Any],
    signals: Iterable[Mapping[str, Any]],
) -> bool:
    return any(
        signal["signal_kind"] == expected["signal_kind"]
        and signal["span"] == expected["span"]
        and signal.get("path_kind") == expected.get("path_kind")
        for signal in signals
    )


def _dedupe_signals(signals: Iterable[TransitionSignal]) -> list[TransitionSignal]:
    deduped: dict[tuple[str, str, int, int], TransitionSignal] = {}
    for signal in signals:
        key = (
            signal.signal_kind,
            signal.artifact_id,
            signal.offset_start,
            signal.offset_end,
        )
        deduped[key] = signal
    return sorted(
        deduped.values(),
        key=lambda signal: (signal.artifact_id, signal.offset_start, signal.signal_kind),
    )


def _path_kind(value: str) -> str:
    if re.match(r"^[A-Za-z]:\\", value):
        return "windows_path"
    if value.startswith(("http://", "https://")):
        return "url_path"
    if value.startswith(("/", "./", "../")):
        return "posix_path"
    return "repo_path"


def _is_protected_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.startswith(PROTECTED_PATH_PREFIXES)


def _trim_path_token(value: str) -> str:
    return value.rstrip(".,;:)]}'\"`")


def _looks_like_sentence_fragment(value: str) -> bool:
    return "://" not in value and "/" not in value and "\\" not in value


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
