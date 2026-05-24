"""Validate the GitHub Actions bill of materials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_actions_bom_file(path: Path) -> list[str]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if data.get("contract_version") != "0.1.0":
        failures.append("actions BOM contract_version must be 0.1.0")
    for entry in data.get("actions", []):
        workflow = entry.get("workflow", "?")
        line = entry.get("line", "?")
        reference = entry.get("reference", "?")
        kind = entry.get("kind")
        if kind == "external" and entry.get("sha_pinned") is not True:
            failures.append(f"{workflow}:{line}: external action not SHA-pinned: {reference}")
        if kind == "docker" and entry.get("docker_digest_pinned") is not True:
            failures.append(f"{workflow}:{line}: docker action not digest-pinned: {reference}")
        if kind not in {"local", "docker", "external"}:
            failures.append(f"{workflow}:{line}: unknown action kind: {kind}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    failures = validate_actions_bom_file(args.path)
    if failures:
        print("Actions BOM validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Actions BOM validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
