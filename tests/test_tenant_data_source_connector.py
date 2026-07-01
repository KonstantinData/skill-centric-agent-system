from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from skill_centric_agent_system.composition.profile_composer import RuntimeProfileComposer
from skill_centric_agent_system.composition.task_analyzer import TaskAnalyzer
from skill_centric_agent_system.runtime.data_sources import (
    TenantDataSourceConnector,
    TenantDataSourceError,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TENANT_CONTEXT_RESPONSE_PATH = (
    REPO_ROOT / "examples" / "control-api" / "composition-context-response-tenant-research.json"
)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def tenant_research_profile() -> dict[str, object]:
    task = {
        "id": "task-tenant-under-test-research",
        "objective": "Research the tenant website and summarize current context.",
        "context": {
            "auth": {
                "principal_id": "tenant-user",
                "tenant_id": "tenant-under-test",
                "area_id": "tenant-under-test",
                "tenant_hostname": "tenant-under-test.example.invalid",
                "membership_id": "tenant-under-test-membership-user",
                "roles": ["tenant-under-test-researcher"],
                "control_plane_principal_id": "tenant-under-test-researcher",
                "role_data_sources": ["tenant-under-test-website"],
                "role_capabilities": ["research"],
            }
        },
    }
    analyzed = TaskAnalyzer().analyze(task)
    return RuntimeProfileComposer().compose(analyzed, load_json(TENANT_CONTEXT_RESPONSE_PATH))


def test_tenant_data_source_connector_returns_role_granted_source() -> None:
    connector = TenantDataSourceConnector(tenant_research_profile())

    handle = connector.connect("tenant-under-test-website")

    assert handle.data_source_id == "tenant-under-test-website"
    assert handle.tenant_id == "tenant-under-test"
    assert handle.access_mode == "read"
    assert handle.status == "active"


@pytest.mark.parametrize(
    ("mutator", "message_part"),
    [
        (
            lambda profile: None,
            "not granted by the active tenant role",
        ),
        (
            lambda profile: profile["tenant_authority"]["data_sources"][0].__setitem__(
                "tenant_id",
                "other-tenant",
            ),
            "crosses tenant boundary",
        ),
    ],
)
def test_tenant_data_source_connector_rejects_unavailable_sources(
    mutator: object,
    message_part: str,
) -> None:
    profile = tenant_research_profile()
    if callable(mutator):
        mutator(profile)
    connector = TenantDataSourceConnector(profile)
    source_id = "other-tenant-website" if message_part.startswith("not granted") else (
        "tenant-under-test-website"
    )

    with pytest.raises(TenantDataSourceError, match=message_part):
        connector.connect(source_id)


def test_tenant_data_source_connector_rejects_ungranted_access_mode() -> None:
    connector = TenantDataSourceConnector(tenant_research_profile())

    with pytest.raises(TenantDataSourceError, match="access mode is not granted"):
        connector.connect("tenant-under-test-website", access_mode="write")


def test_tenant_data_source_connector_rejects_global_profile() -> None:
    profile = deepcopy(tenant_research_profile())
    profile["tenant_context"]["tenant_id"] = "global"
    profile["tenant_authority"] = None

    connector = TenantDataSourceConnector(profile)

    with pytest.raises(TenantDataSourceError, match="tenant-scoped profile"):
        connector.connect("tenant-under-test-website")
