"""Generate a lightweight release SBOM for direct repository dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_dependency_policy import (
    load_npm_direct_dependencies,
    load_python_direct_dependencies,
)


def build_sbom(root: Path) -> dict[str, Any]:
    components = [
        {"ecosystem": "python", "name": dependency}
        for dependency in sorted(load_python_direct_dependencies(root))
    ]
    components.extend(
        {"ecosystem": "npm", "name": dependency}
        for dependency in sorted(load_npm_direct_dependencies(root))
    )
    return {
        "contract_version": "0.1.0",
        "artifact_type": "direct-dependency-sbom",
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("security-evidence/release-sbom.json"))
    args = parser.parse_args()

    sbom = build_sbom(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sbom, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
