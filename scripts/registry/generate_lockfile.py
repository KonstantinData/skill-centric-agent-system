from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_ROOT = REPO_ROOT / "registry" / "modules"
DEFAULT_OUTPUT = REPO_ROOT / "registry" / "versions" / "lockfile.json"
LOCKFILE_VERSION = "0.1.0"


class RegistryLockfileError(ValueError):
    """Raised when the registry lockfile is stale or cannot be generated."""


def build_lockfile(
    *,
    registry_root: Path = DEFAULT_REGISTRY_ROOT,
    environment: str = "dev",
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat()
    modules: list[dict[str, Any]] = []
    for module_path in sorted(registry_root.rglob("module.json")):
        module = _load_json(module_path)
        if environment not in module.get("environments", []):
            continue
        module_dir = module_path.parent
        modules.append(
            {
                "kind": module["kind"],
                "name": module["name"],
                "path": _repo_path(module_dir),
                "schema_version": module["schema_version"],
                "sha256": _hash_module_dir(module_dir),
                "status": module["status"],
                "version": module["version"],
            }
        )
    modules.sort(key=lambda item: (item["kind"], item["name"], item["version"]))
    return {
        "lockfile_version": LOCKFILE_VERSION,
        "generated_at": generated_at,
        "environment": environment,
        "registry_root": _repo_path(registry_root),
        "module_count": len(modules),
        "modules": modules,
    }


def write_lockfile(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    registry_root: Path = DEFAULT_REGISTRY_ROOT,
    environment: str = "dev",
) -> dict[str, Any]:
    payload = build_lockfile(registry_root=registry_root, environment=environment)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_json_dump(payload), encoding="utf-8")
    return payload


def assert_lockfile_current(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    registry_root: Path = DEFAULT_REGISTRY_ROOT,
    environment: str = "dev",
) -> dict[str, Any]:
    committed = _load_json(output_path)
    expected = build_lockfile(
        registry_root=registry_root,
        environment=environment,
        generated_at=str(committed.get("generated_at", "")),
    )
    if committed != expected:
        raise RegistryLockfileError(
            "registry lockfile is stale; run "
            "`python scripts/registry/generate_lockfile.py` and commit the result"
        )
    return expected


def _hash_module_dir(module_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in module_dir.rglob("*") if item.is_file()):
        relative = path.relative_to(module_dir).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise RegistryLockfileError(f"{_repo_path(path)} must contain a JSON object")
    return parsed


def _json_dump(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate or check the SCAS registry lockfile.")
    parser.add_argument("--registry-root", type=Path, default=DEFAULT_REGISTRY_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--environment", choices=("dev", "staging", "prod"), default="dev")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.check:
            payload = assert_lockfile_current(
                output_path=args.output,
                registry_root=args.registry_root,
                environment=args.environment,
            )
        else:
            payload = write_lockfile(
                output_path=args.output,
                registry_root=args.registry_root,
                environment=args.environment,
            )
        if args.print_json:
            print(_json_dump(payload), end="")
    except (OSError, json.JSONDecodeError, RegistryLockfileError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
