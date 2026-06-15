from __future__ import annotations

import json
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTAKE_DIR = Path(".scas-runtime") / "intake"
DEFAULT_ARTIFACT_ROOT = Path(".scas-runtime")
TENANTS_DIR = REPO_ROOT / "examples" / "tenants"

TASK_TYPE_HINTS = (
    "auto",
    "general-task",
    "research",
    "task-execution",
    "code-review",
)

AUTHORIZATION_POLICY_BY_TASK_TYPE = {
    "auto": "submitter-can-request-general-task",
    "general-task": "submitter-can-request-general-task",
    "research": "submitter-can-request-research",
    "task-execution": "submitter-can-request-task-execution",
    "code-review": "submitter-can-request-code-review",
}

COMPOSITION_FIXTURE_BY_TASK_TYPE = {
    "general-task": Path("examples/control-api/composition-context-response-general-task.json"),
    "research": Path("examples/control-api/composition-context-response-research.json"),
    "task-execution": Path(
        "examples/control-api/composition-context-response-task-execution.json"
    ),
    "code-review": Path("examples/control-api/composition-context-response.json"),
}


@dataclass(frozen=True)
class RuntimeCommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def default_task_id(request: str, submitted_at: datetime) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", request.casefold()).strip("-")
    compact_slug = slug[:40].strip("-") or "task"
    return f"task-ui-{compact_slug}-{submitted_at.strftime('%Y%m%d%H%M%S')}"


def build_task_envelope(
    *,
    request: str,
    task_id: str,
    environment: str,
    task_type_hint: str,
    write_access: bool,
    destructive_actions: bool,
    repository_path: str | None,
    repository_slug: str | None,
    submitted_at: datetime,
    tenant_auth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_request = request.strip()
    if not clean_request:
        raise ValueError("request must not be empty.")
    if environment not in {"dev", "staging", "prod"}:
        raise ValueError(f"Unsupported environment: {environment}.")
    if task_type_hint not in TASK_TYPE_HINTS:
        raise ValueError(f"Unsupported task type hint: {task_type_hint}.")
    if destructive_actions and not write_access:
        raise ValueError("destructive_actions requires write_access.")

    context: dict[str, Any] = {
        "auth": {
            "principal_id": "user-konstantin",
            "principal_type": "user",
            "roles": ["repository-maintainer"],
            "authorization_policies": [
                AUTHORIZATION_POLICY_BY_TASK_TYPE[task_type_hint],
            ],
            "control_plane_principal_kind": "role",
            "control_plane_principal_id": "repository-maintainer",
            "display_name": "Konstantin Milonas",
        },
        "intake": {
            "source": "streamlit-task-intake-ui",
            "environment": environment,
            "task_type_hint": task_type_hint,
            "submitted_at": submitted_at.isoformat(),
        },
    }

    repository: dict[str, Any] = {}
    if repository_path:
        repository["path"] = repository_path
    if repository_slug:
        repository["slug"] = repository_slug
    if repository:
        context["repository"] = repository
    if tenant_auth is not None:
        context["auth"].update(tenant_auth)

    return {
        "id": task_id.strip(),
        "source": "user",
        "request": clean_request,
        "constraints": {
            "write_access": write_access,
            "destructive_actions": destructive_actions,
        },
        "context": context,
    }


def load_tenant_registry(tenants_dir: Path = TENANTS_DIR) -> dict[str, dict[str, Any]]:
    tenants: dict[str, dict[str, Any]] = {}
    for path in sorted(tenants_dir.glob("*.json")):
        tenant = json.loads(path.read_text(encoding="utf-8"))
        if tenant.get("status") in {"setup", "active"}:
            tenants[str(tenant["tenant_id"])] = tenant
    return tenants


def build_tenant_role_auth(
    tenant: dict[str, Any],
    role_id: str,
    *,
    principal_id: str = "repository-maintainer",
) -> dict[str, Any]:
    role = next(
        (item for item in tenant.get("role_bundles", []) if item.get("id") == role_id),
        None,
    )
    if role is None:
        raise ValueError(f"Unknown tenant role: {role_id}.")
    hostnames = tenant.get("hostnames", [])
    if not hostnames:
        raise ValueError(f"Tenant has no configured hostname: {tenant['tenant_id']}.")
    return {
        "principal_id": principal_id,
        "tenant_id": tenant["tenant_id"],
        "area_id": tenant["area_id"],
        "tenant_hostname": hostnames[0]["hostname"],
        "membership_id": f"tm-{tenant['tenant_id']}-{principal_id}",
        "roles": [role["id"]],
        "control_plane_principal_kind": "role",
        "control_plane_principal_id": principal_id,
        "role_data_sources": [
            grant["data_source_id"] for grant in role.get("data_source_grants", [])
        ],
        "role_capabilities": list(role.get("capability_grants", [])),
    }


def write_task_envelope(
    envelope: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    intake_dir: Path = DEFAULT_INTAKE_DIR,
) -> Path:
    root = repo_root.resolve()
    output_dir = (
        (root / intake_dir).resolve()
        if not intake_dir.is_absolute()
        else intake_dir.resolve()
    )
    if not _is_relative_to(output_dir, root):
        raise ValueError("intake_dir must resolve inside the repository root.")

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"task-envelope-{datetime.now().strftime('%Y%m%d%H%M%S%f')}.json"
    output_path = output_dir / filename
    output_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def fixture_for_task_type(task_type_hint: str) -> Path:
    if task_type_hint == "auto":
        return COMPOSITION_FIXTURE_BY_TASK_TYPE["general-task"]
    return COMPOSITION_FIXTURE_BY_TASK_TYPE[task_type_hint]


def build_runtime_command(
    *,
    task_file: Path,
    composition_context_file: Path,
    environment: str,
    artifact_root: Path,
    repository_root: Path,
    run_minimal_loop: bool,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "skill_centric_agent_system.runtime.cli",
        "--task-file",
        str(task_file),
        "--composition-context-file",
        str(composition_context_file),
        "--environment",
        environment,
        "--artifact-root",
        str(artifact_root),
        "--repository-root",
        str(repository_root),
    ]
    if run_minimal_loop:
        command.append("--run-minimal-loop")
    return command


def build_runtime_args(
    *,
    task_file: Path,
    composition_context_file: Path,
    environment: str,
    artifact_root: Path,
    repository_root: Path,
    run_minimal_loop: bool,
) -> list[str]:
    command = build_runtime_command(
        task_file=task_file,
        composition_context_file=composition_context_file,
        environment=environment,
        artifact_root=artifact_root,
        repository_root=repository_root,
        run_minimal_loop=run_minimal_loop,
    )
    return command[3:]


def run_local_runtime(
    *,
    task_file: Path,
    composition_context_file: Path,
    environment: str,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    repository_root: Path = REPO_ROOT,
    run_minimal_loop: bool = True,
) -> RuntimeCommandResult:
    from skill_centric_agent_system.runtime.cli import main as runtime_cli_main

    root = repository_root.resolve()
    safe_task_file = _resolve_repo_file(task_file, root)
    safe_context_file = _resolve_repo_file(composition_context_file, root)
    safe_artifact_root = _resolve_repo_child(artifact_root, root)
    command = build_runtime_command(
        task_file=safe_task_file,
        composition_context_file=safe_context_file,
        environment=environment,
        artifact_root=safe_artifact_root,
        repository_root=root,
        run_minimal_loop=run_minimal_loop,
    )
    argv = build_runtime_args(
        task_file=safe_task_file,
        composition_context_file=safe_context_file,
        environment=environment,
        artifact_root=safe_artifact_root,
        repository_root=root,
        run_minimal_loop=run_minimal_loop,
    )
    stdout = StringIO()
    stderr = StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        returncode = runtime_cli_main(argv)
    return RuntimeCommandResult(
        command=command,
        returncode=returncode,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


def parse_runtime_stdout(stdout: str) -> dict[str, Any] | None:
    stripped = stdout.strip()
    if not stripped:
        return None
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("Runtime stdout must be a JSON object.")
    return parsed


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="SCAS Task Intake",
        page_icon=":material/forum:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _apply_styles(st)
    _init_session(st)

    prompt = st.chat_input("Aufgabe an SCAS")
    if prompt:
        st.session_state["task_request"] = prompt
        st.session_state["messages"].append({"role": "user", "content": prompt})

    st.sidebar.title("SCAS")
    tenants = load_tenant_registry()
    tenant_options = ["global", *sorted(tenants)]
    selected_tenant_id = st.sidebar.selectbox("Tenant", tenant_options, index=0)
    selected_role_id: str | None = None
    if selected_tenant_id != "global":
        role_options = [role["id"] for role in tenants[selected_tenant_id]["role_bundles"]]
        selected_role_id = st.sidebar.selectbox("Tenant-Rolle", role_options, index=0)
    environment = st.sidebar.selectbox("Umgebung", ["dev", "staging"], index=0)
    task_type_hint = st.sidebar.selectbox(
        "Task-Typ",
        TASK_TYPE_HINTS,
        index=0,
    )
    write_access = st.sidebar.toggle("Write Access", value=False)
    destructive_actions = st.sidebar.toggle(
        "Destructive Actions",
        value=False,
        disabled=not write_access,
    )
    run_minimal_loop = st.sidebar.toggle("Minimal Loop", value=True)

    st.title("SCAS Task Intake")
    st.caption("Thin intake for the self-composing single-agent runtime.")

    conversation, envelope_tab, runtime_tab = st.tabs(["Dialog", "Envelope", "Runtime"])

    with conversation:
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        request = st.text_area(
            "Aufgabe",
            value=st.session_state["task_request"],
            height=180,
            placeholder="Beschreibe die Aufgabe, die SCAS analysieren und ausführen soll.",
        )
        repository_path = st.text_input("Repository Path", value=".")
        repository_slug = st.text_input(
            "Repository Slug",
            value="KonstantinData/skill-centric-agent-system",
        )

        if st.button("Envelope erzeugen", type="primary"):
            try:
                submitted_at = datetime.now().astimezone()
                task_id = default_task_id(request, submitted_at)
                tenant_auth = (
                    build_tenant_role_auth(tenants[selected_tenant_id], selected_role_id)
                    if selected_tenant_id != "global" and selected_role_id is not None
                    else None
                )
                envelope = build_task_envelope(
                    request=request,
                    task_id=task_id,
                    environment=environment,
                    task_type_hint=task_type_hint,
                    write_access=write_access,
                    destructive_actions=destructive_actions,
                    repository_path=repository_path,
                    repository_slug=repository_slug,
                    submitted_at=submitted_at,
                    tenant_auth=tenant_auth,
                )
                task_file = write_task_envelope(envelope)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["task_request"] = request
                st.session_state["envelope"] = envelope
                st.session_state["task_file"] = task_file
                st.session_state["messages"].append(
                    {
                        "role": "assistant",
                        "content": f"Envelope erzeugt: `{task_file}`",
                    }
                )
                st.rerun()

    with envelope_tab:
        envelope = st.session_state.get("envelope")
        task_file = st.session_state.get("task_file")
        if envelope:
            st.code(json.dumps(envelope, indent=2, sort_keys=True), language="json")
            st.download_button(
                "JSON herunterladen",
                json.dumps(envelope, indent=2, sort_keys=True) + "\n",
                file_name=f"{envelope['id']}.json",
                mime="application/json",
            )
            if task_file:
                st.info(f"Pfad: {task_file}")
        else:
            st.info("Noch kein Envelope erzeugt.")

    with runtime_tab:
        task_file = st.session_state.get("task_file")
        fixture_path = fixture_for_task_type(task_type_hint)
        st.text_input("Composition Fixture", value=str(fixture_path), disabled=True)
        if task_file:
            command = build_runtime_command(
                task_file=Path(task_file),
                composition_context_file=fixture_path,
                environment=environment,
                artifact_root=DEFAULT_ARTIFACT_ROOT,
                repository_root=REPO_ROOT,
                run_minimal_loop=run_minimal_loop,
            )
            st.code(" ".join(command), language="powershell")
            if st.button("Lokal starten"):
                with st.spinner("Runtime läuft..."):
                    result = run_local_runtime(
                        task_file=Path(task_file),
                        composition_context_file=fixture_path,
                        environment=environment,
                        run_minimal_loop=run_minimal_loop,
                    )
                st.session_state["runtime_result"] = result
                try:
                    parsed = parse_runtime_stdout(result.stdout)
                except ValueError as exc:
                    parsed = None
                    st.error(str(exc))
                if parsed is not None:
                    st.session_state["messages"].append(
                        {
                            "role": "assistant",
                            "content": (
                                f"Run `{parsed['run_id']}` beendet mit Status "
                                f"`{parsed['status']}`."
                            ),
                        }
                    )
                st.rerun()
        else:
            st.info("Erzeuge zuerst ein Envelope.")

        result = st.session_state.get("runtime_result")
        if result:
            st.metric("Exit Code", result.returncode)
            if result.stdout:
                st.code(result.stdout, language="json")
            if result.stderr:
                st.code(result.stderr, language="text")


def _init_session(st: Any) -> None:
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("task_request", "")


def _apply_styles(st: Any) -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #f7f8fb; }
        [data-testid="stSidebar"] { background: #111827; }
        [data-testid="stSidebar"] * { color: #f8fafc !important; }
        h1, h2, h3 { letter-spacing: 0; }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #d8dee8;
            border-radius: 8px;
            padding: 10px 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _resolve_repo_file(path: Path, repo_root: Path) -> Path:
    resolved = _resolve_repo_child(path, repo_root)
    if not resolved.is_file():
        raise ValueError(f"Expected an existing file inside the repository: {path}.")
    return resolved


def _resolve_repo_child(path: Path, repo_root: Path) -> Path:
    root = repo_root.resolve()
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    if not _is_relative_to(resolved, root):
        raise ValueError(f"Path must resolve inside the repository: {path}.")
    return resolved


if __name__ == "__main__":
    main()
