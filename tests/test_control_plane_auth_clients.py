from __future__ import annotations

from typing import Any

from skill_centric_agent_system.composition import ControlPlaneClient
from skill_centric_agent_system.runtime.memory_feedback import CloudflareMemoryIngestionClient


class FakeResponse:
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False

    def read(self) -> bytes:
        return b'{"status":"ok"}'


def test_control_plane_client_sends_bearer_token(monkeypatch: Any) -> None:
    captured: dict[str, str | None] = {}

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = str(timeout)
        return FakeResponse()

    monkeypatch.setattr(
        "skill_centric_agent_system.composition.control_plane.urlopen",
        fake_urlopen,
    )

    ControlPlaneClient(
        "https://control.example",
        timeout_seconds=3.0,
        api_token="secret-token",
    ).composition_context({"contract_version": "0.1.0"})

    assert captured == {
        "authorization": "Bearer secret-token",
        "timeout": "3.0",
    }


def test_memory_ingestion_client_sends_bearer_token(monkeypatch: Any) -> None:
    captured: dict[str, str | None] = {}

    def fake_urlopen(request: Any, timeout: float) -> FakeResponse:
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = str(timeout)
        return FakeResponse()

    monkeypatch.setattr(
        "skill_centric_agent_system.runtime.memory_feedback.urlopen",
        fake_urlopen,
    )

    CloudflareMemoryIngestionClient(
        "https://control.example",
        timeout_seconds=4.0,
        api_token="memory-token",
    ).ingest_memory({"contract_version": "0.1.0"})

    assert captured == {
        "authorization": "Bearer memory-token",
        "timeout": "4.0",
    }
