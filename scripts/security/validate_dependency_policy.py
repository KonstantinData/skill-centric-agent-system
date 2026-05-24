"""Validate dependency ownership and risk exception policy."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

DEPENDENCY_POLICY_DIR = Path("policies/dependencies")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_python_requirement(requirement: str) -> str:
    return re.split(r"\s*(?:\[|==|>=|<=|~=|!=|>|<)", requirement, maxsplit=1)[0].strip().lower()


def load_python_direct_dependencies(root: Path) -> set[str]:
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = set()
    for requirement in pyproject.get("project", {}).get("dependencies", []):
        dependencies.add(normalize_python_requirement(requirement))
    for requirements in pyproject.get("project", {}).get("optional-dependencies", {}).values():
        for requirement in requirements:
            dependencies.add(normalize_python_requirement(requirement))
    return {dependency for dependency in dependencies if dependency}


def load_npm_direct_dependencies(root: Path) -> set[str]:
    package = load_json(root / "package.json")
    dependencies: set[str] = set()
    for section in ("dependencies", "devDependencies", "optionalDependencies"):
        dependencies.update(package.get(section, {}).keys())
    return {dependency.lower() for dependency in dependencies}


def validate_direct_dependency_registry(root: Path, registry: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    registered = {
        (entry.get("ecosystem"), str(entry.get("package", "")).lower())
        for entry in registry.get("registry", [])
    }
    for dependency in sorted(load_python_direct_dependencies(root)):
        if ("python", dependency) not in registered:
            failures.append(f"python dependency missing owner: {dependency}")
    for dependency in sorted(load_npm_direct_dependencies(root)):
        if ("npm", dependency) not in registered:
            failures.append(f"npm dependency missing owner: {dependency}")
    for entry in registry.get("registry", []):
        for field in ("ecosystem", "package", "owner", "usage"):
            if not entry.get(field):
                failures.append(f"dependency registry entry missing {field}: {entry}")
    return failures


def validate_cve_exceptions(
    exceptions_data: dict[str, Any],
    *,
    today: date | None = None,
) -> list[str]:
    current_date = today or date.today()
    required = {"id", "package", "ecosystem", "owner", "reason", "expires", "accepted_risk"}
    failures: list[str] = []
    for exception in exceptions_data.get("exceptions", []):
        missing = sorted(required - exception.keys())
        if missing:
            failures.append(f"CVE exception missing fields {missing}: {exception.get('id', '?')}")
            continue
        try:
            expires = date.fromisoformat(str(exception["expires"]))
        except ValueError:
            failures.append(f"CVE exception has invalid expires date: {exception.get('id')}")
            continue
        if expires < current_date:
            failures.append(
                f"CVE exception expired on {exception['expires']}: {exception.get('id')}"
            )
    return failures


def validate_license_policy(policy: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if policy.get("unknown_action") != "block":
        failures.append("dependency license policy must block unknown licenses")
    if not policy.get("allowed"):
        failures.append("dependency license policy must define allowed licenses")
    if not policy.get("denied"):
        failures.append("dependency license policy must define denied licenses")
    return failures


def validate_dependency_policy(root: Path | None = None) -> list[str]:
    repo_root = root or Path.cwd()
    policy_dir = repo_root / DEPENDENCY_POLICY_DIR
    registry = load_json(policy_dir / "direct-dependency-owners.json")
    exceptions = load_json(policy_dir / "dependency-risk-exceptions.json")
    license_policy = load_json(policy_dir / "dependency-license-policy.json")

    failures: list[str] = []
    failures.extend(validate_direct_dependency_registry(repo_root, registry))
    failures.extend(validate_cve_exceptions(exceptions))
    failures.extend(validate_license_policy(license_policy))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    failures = validate_dependency_policy(args.root)
    if failures:
        print("Dependency policy validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Dependency policy validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
