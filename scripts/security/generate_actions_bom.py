"""Generate a small bill of materials for GitHub Actions workflow references."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>[^\s#]+)")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def action_kind(reference: str) -> str:
    if reference.startswith("./") or reference.startswith("../"):
        return "local"
    if reference.startswith("docker://"):
        return "docker"
    return "external"


def split_pin(reference: str) -> tuple[str, str]:
    if "@" not in reference:
        return reference, ""
    name, pin = reference.rsplit("@", 1)
    return name, pin


def collect_actions(workflow_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for workflow in sorted(workflow_dir.glob("*.yml")):
        for line_number, line in enumerate(workflow.read_text(encoding="utf-8").splitlines(), 1):
            match = USES_PATTERN.match(line)
            if not match:
                continue
            reference = match.group("ref").strip().strip('"').strip("'")
            name, pin = split_pin(reference)
            kind = action_kind(reference)
            entries.append(
                {
                    "workflow": workflow.name,
                    "line": line_number,
                    "kind": kind,
                    "name": name,
                    "reference": reference,
                    "pin": pin,
                    "sha_pinned": kind != "external" or bool(SHA_PATTERN.fullmatch(pin)),
                    "docker_digest_pinned": kind != "docker" or "@sha256:" in reference,
                }
            )
    return entries


def build_actions_bom(workflow_dir: Path) -> dict[str, Any]:
    return {
        "contract_version": "0.1.0",
        "artifact_type": "github-actions-bom",
        "actions": collect_actions(workflow_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-dir", type=Path, default=Path(".github/workflows"))
    parser.add_argument("--output", type=Path, default=Path("security-evidence/actions-bom.json"))
    args = parser.parse_args()

    data = build_actions_bom(args.workflow_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
