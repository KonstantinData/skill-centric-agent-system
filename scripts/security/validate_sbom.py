"""Validate the lightweight release SBOM."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate_sbom_file(path: Path) -> list[str]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if data.get("contract_version") != "0.1.0":
        failures.append("SBOM contract_version must be 0.1.0")
    if data.get("artifact_type") != "direct-dependency-sbom":
        failures.append("SBOM artifact_type must be direct-dependency-sbom")
    components = data.get("components")
    if not isinstance(components, list) or not components:
        failures.append("SBOM must contain at least one component")
        return failures
    seen: set[tuple[str, str]] = set()
    for component in components:
        if not isinstance(component, dict):
            failures.append(f"SBOM component must be object: {component}")
            continue
        ecosystem = component.get("ecosystem")
        name = component.get("name")
        if ecosystem not in {"python", "npm"}:
            failures.append(f"SBOM component has invalid ecosystem: {component}")
        if not isinstance(name, str) or not name:
            failures.append(f"SBOM component missing name: {component}")
        key = (str(ecosystem), str(name).lower())
        if key in seen:
            failures.append(f"SBOM component duplicated: {ecosystem}/{name}")
        seen.add(key)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    failures = validate_sbom_file(args.path)
    if failures:
        print("SBOM validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("SBOM validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
