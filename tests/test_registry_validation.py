from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.registry.generate_lockfile import (
    RegistryLockfileError,
    assert_lockfile_current,
    build_lockfile,
)
from scripts.registry.validate_registry import RegistryValidationError, validate_registry

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_ROOT = REPO_ROOT / "registry" / "modules"
SCHEMA_PATH = REPO_ROOT / "schemas" / "module.schema.json"
ENVIRONMENTS_DIR = REPO_ROOT / "registry" / "environments"
LOCKFILE_PATH = REPO_ROOT / "registry" / "versions" / "lockfile.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_registry_phase_3a_schema_validation_passes() -> None:
    assert validate_registry(
        registry_root=REGISTRY_ROOT,
        schema_path=SCHEMA_PATH,
        environments_dir=ENVIRONMENTS_DIR,
        phase="3a",
    ) == []


def test_registry_phase_3b_graph_validation_passes() -> None:
    assert validate_registry(
        registry_root=REGISTRY_ROOT,
        schema_path=SCHEMA_PATH,
        environments_dir=ENVIRONMENTS_DIR,
        phase="3b",
    ) == []


def test_registry_rejects_runtime_role_default_outside_allowed(tmp_path: Path) -> None:
    module_dir = tmp_path / "modules" / "skills" / "git-diff-analysis"
    module_dir.mkdir(parents=True)
    module = load_json(REGISTRY_ROOT / "skills" / "git-diff-analysis" / "module.json")
    module["runtime_roles"]["default"] = "shared"
    (module_dir / "module.json").write_text(json.dumps(module), encoding="utf-8")
    (module_dir / "SKILL.md").write_text(
        "---\nname: git-diff-analysis\ndescription: test\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(RegistryValidationError, match="runtime_roles.default"):
        validate_registry(
            registry_root=tmp_path / "modules",
            schema_path=SCHEMA_PATH,
            environments_dir=ENVIRONMENTS_DIR,
            phase="3a",
        )


def test_registry_rejects_missing_reference(tmp_path: Path) -> None:
    module_dir = tmp_path / "modules" / "skills" / "git-diff-analysis"
    module_dir.mkdir(parents=True)
    module = load_json(REGISTRY_ROOT / "skills" / "git-diff-analysis" / "module.json")
    module["required_tools"] = ["missing-tool"]
    (module_dir / "module.json").write_text(json.dumps(module), encoding="utf-8")
    (module_dir / "SKILL.md").write_text(
        "---\nname: git-diff-analysis\ndescription: test\n---\n",
        encoding="utf-8",
    )

    with pytest.raises(RegistryValidationError, match="missing tool"):
        validate_registry(
            registry_root=tmp_path / "modules",
            schema_path=SCHEMA_PATH,
            environments_dir=ENVIRONMENTS_DIR,
            phase="3b",
        )


def test_registry_lockfile_is_current() -> None:
    assert assert_lockfile_current(output_path=LOCKFILE_PATH, registry_root=REGISTRY_ROOT)[
        "module_count"
    ] >= 1


def test_registry_lockfile_hash_changes_when_module_changes(tmp_path: Path) -> None:
    source = REGISTRY_ROOT / "skills" / "git-diff-analysis"
    target = tmp_path / "modules" / "skills" / "git-diff-analysis"
    target.mkdir(parents=True)
    for path in source.rglob("*"):
        if path.is_file():
            relative = path.relative_to(source)
            (target / relative).parent.mkdir(parents=True, exist_ok=True)
            (target / relative).write_bytes(path.read_bytes())

    before = build_lockfile(
        registry_root=tmp_path / "modules",
        generated_at="2026-06-13T00:00:00+00:00",
    )
    skill = target / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nAdditional test line.\n")
    after = build_lockfile(
        registry_root=tmp_path / "modules",
        generated_at="2026-06-13T00:00:00+00:00",
    )

    assert before["modules"][0]["sha256"] != after["modules"][0]["sha256"]


def test_registry_lockfile_hash_normalizes_text_line_endings(tmp_path: Path) -> None:
    lf_root = tmp_path / "lf" / "modules" / "skills" / "sample"
    crlf_root = tmp_path / "crlf" / "modules" / "skills" / "sample"
    lf_root.mkdir(parents=True)
    crlf_root.mkdir(parents=True)
    module = {
        "name": "sample",
        "version": "0.1.0",
        "kind": "skill",
        "status": "active",
        "schema_version": "0.1.0",
        "environments": ["dev"],
    }
    lf_module = json.dumps(module, indent=2) + "\n"
    crlf_module = lf_module.replace("\n", "\r\n")
    lf_skill = "---\nname: sample\ndescription: test\n---\n"
    crlf_skill = lf_skill.replace("\n", "\r\n")
    (lf_root / "module.json").write_bytes(lf_module.encode("utf-8"))
    (crlf_root / "module.json").write_bytes(crlf_module.encode("utf-8"))
    (lf_root / "SKILL.md").write_bytes(lf_skill.encode("utf-8"))
    (crlf_root / "SKILL.md").write_bytes(crlf_skill.encode("utf-8"))

    lf = build_lockfile(
        registry_root=tmp_path / "lf" / "modules",
        generated_at="2026-06-13T00:00:00+00:00",
    )
    crlf = build_lockfile(
        registry_root=tmp_path / "crlf" / "modules",
        generated_at="2026-06-13T00:00:00+00:00",
    )

    assert lf["modules"][0]["sha256"] == crlf["modules"][0]["sha256"]


def test_registry_lockfile_check_fails_on_stale_file(tmp_path: Path) -> None:
    lockfile = tmp_path / "lockfile.json"
    payload = build_lockfile(
        registry_root=REGISTRY_ROOT,
        generated_at="2026-06-13T00:00:00+00:00",
    )
    payload["modules"][0]["sha256"] = "stale"
    lockfile.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RegistryLockfileError):
        assert_lockfile_current(output_path=lockfile, registry_root=REGISTRY_ROOT)
