from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = REPO_ROOT / "apps" / "streamlit_task_intake_ui" / "app.py"


spec = importlib.util.spec_from_file_location("streamlit_task_intake_ui_app", APP_PATH)
assert spec is not None
streamlit_task_intake_ui_app = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = streamlit_task_intake_ui_app
spec.loader.exec_module(streamlit_task_intake_ui_app)


def test_default_task_id_is_stable_and_filesystem_safe() -> None:
    submitted_at = datetime(2026, 6, 12, 10, 30, 0, tzinfo=UTC)

    task_id = streamlit_task_intake_ui_app.default_task_id(
        "Review PR #101: docs + runtime!",
        submitted_at,
    )

    assert task_id == "task-ui-review-pr-101-docs-runtime-20260612103000"


def test_build_task_envelope_keeps_ui_as_thin_intake_surface() -> None:
    submitted_at = datetime(2026, 6, 12, 10, 30, 0, tzinfo=UTC)

    envelope = streamlit_task_intake_ui_app.build_task_envelope(
        request="Run the next controlled staging task.",
        task_id="task-ui-controlled-staging",
        environment="staging",
        task_type_hint="task-execution",
        write_access=True,
        destructive_actions=False,
        repository_path=".",
        repository_slug="KonstantinData/skill-centric-agent-system",
        submitted_at=submitted_at,
    )

    assert envelope["id"] == "task-ui-controlled-staging"
    assert envelope["request"] == "Run the next controlled staging task."
    assert envelope["constraints"] == {
        "write_access": True,
        "destructive_actions": False,
    }
    assert envelope["context"]["intake"] == {
        "source": "streamlit-task-intake-ui",
        "environment": "staging",
        "task_type_hint": "task-execution",
        "submitted_at": "2026-06-12T10:30:00+00:00",
    }
    assert envelope["context"]["auth"]["authorization_policies"] == [
        "submitter-can-request-task-execution",
    ]
    assert "skills" not in envelope
    assert "tools" not in envelope
    assert "validators" not in envelope


def test_build_task_envelope_can_scope_task_to_tenant_role() -> None:
    submitted_at = datetime(2026, 6, 12, 10, 30, 0, tzinfo=UTC)
    tenants = streamlit_task_intake_ui_app.load_tenant_registry()
    tenant_auth = streamlit_task_intake_ui_app.build_tenant_role_auth(
        tenants["liquisto"],
        "liquisto-owner",
    )

    envelope = streamlit_task_intake_ui_app.build_task_envelope(
        request="Prepare a Liquisto tenant admin summary.",
        task_id="task-ui-liquisto-admin-summary",
        environment="dev",
        task_type_hint="research",
        write_access=False,
        destructive_actions=False,
        repository_path=".",
        repository_slug="KonstantinData/skill-centric-agent-system",
        submitted_at=submitted_at,
        tenant_auth=tenant_auth,
    )

    assert envelope["context"]["auth"]["tenant_id"] == "liquisto"
    assert envelope["context"]["auth"]["area_id"] == "liquisto"
    assert envelope["context"]["auth"]["tenant_hostname"] == "liquisto.cloud"
    assert envelope["context"]["auth"]["membership_id"] == "tm-liquisto-repository-maintainer"
    assert envelope["context"]["auth"]["roles"] == ["liquisto-owner"]
    assert envelope["context"]["auth"]["role_capabilities"] == ["research", "tenant-admin"]
    assert envelope["context"]["auth"]["role_data_sources"] == ["liquisto-website"]
    assert "skills" not in envelope
    assert "tools" not in envelope


def test_write_task_envelope_stays_inside_repository(tmp_path: Path) -> None:
    envelope = {
        "id": "task-ui-test",
        "request": "Test",
        "constraints": {"write_access": False, "destructive_actions": False},
        "context": {},
    }

    task_file = streamlit_task_intake_ui_app.write_task_envelope(
        envelope,
        repo_root=tmp_path,
        intake_dir=Path(".scas-runtime/intake"),
    )

    assert task_file.parent == tmp_path / ".scas-runtime" / "intake"
    assert task_file.name.startswith("task-envelope-")
    assert task_file.suffix == ".json"
    assert task_file.read_text(encoding="utf-8").endswith("\n")


def test_write_task_envelope_rejects_paths_outside_repo(tmp_path: Path) -> None:
    envelope = {
        "id": "task-ui-test",
        "request": "Test",
        "constraints": {"write_access": False, "destructive_actions": False},
        "context": {},
    }

    try:
        streamlit_task_intake_ui_app.write_task_envelope(
            envelope,
            repo_root=tmp_path,
            intake_dir=tmp_path.parent,
        )
    except ValueError as exc:
        assert "inside the repository root" in str(exc)
    else:
        raise AssertionError("Expected ValueError for output path outside the repository.")


def test_runtime_command_uses_fixture_without_secret_arguments() -> None:
    command = streamlit_task_intake_ui_app.build_runtime_command(
        task_file=Path(".scas-runtime/intake/task-ui-test.json"),
        composition_context_file=Path(
            "examples/control-api/composition-context-response-general-task.json"
        ),
        environment="dev",
        artifact_root=Path(".scas-runtime"),
        repository_root=Path("."),
        run_minimal_loop=True,
    )

    assert "--composition-context-file" in command
    assert "--run-minimal-loop" in command
    assert "--control-plane-token" not in command
    assert "--database-url" not in command


def test_build_runtime_args_omits_python_module_prefix() -> None:
    args = streamlit_task_intake_ui_app.build_runtime_args(
        task_file=Path(".scas-runtime/intake/task-envelope.json"),
        composition_context_file=Path(
            "examples/control-api/composition-context-response-general-task.json"
        ),
        environment="dev",
        artifact_root=Path(".scas-runtime"),
        repository_root=Path("."),
        run_minimal_loop=True,
    )

    assert args[0] == "--task-file"
    assert "-m" not in args
