from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class MemoryFeedbackError(RuntimeError):
    """Raised when a memory candidate cannot be submitted safely."""


@dataclass(frozen=True)
class CloudflareMemoryIngestionClient:
    base_url: str
    timeout_seconds: float = 10.0
    api_token: str | None = None

    def ingest_memory(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + "/memory/ingest"
        request = Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "accept": "application/json",
                **self._authorization_headers(),
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise MemoryFeedbackError(
                f"Cloudflare memory ingestion returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise MemoryFeedbackError(f"Cloudflare memory ingestion failed: {error}") from error

        parsed = json.loads(response_body)
        if not isinstance(parsed, dict):
            raise MemoryFeedbackError("Cloudflare memory ingestion response must be an object.")
        return parsed

    def _authorization_headers(self) -> dict[str, str]:
        token = self.api_token or os.getenv("SCAS_CONTROL_API_TOKEN")
        if token is None or not token.strip():
            return {}
        return {"authorization": f"Bearer {token.strip()}"}


class MemoryFeedbackPipeline:
    """Submit approved Hetzner memory candidates to Cloudflare durable memory."""

    def __init__(
        self,
        client: CloudflareMemoryIngestionClient,
        *,
        contract_version: str = "0.1.0",
    ) -> None:
        self.client = client
        self.contract_version = contract_version

    def submit_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        consolidated_content: Mapping[str, Any],
        version: str = "0.1.0",
    ) -> dict[str, Any]:
        _validate_candidate(candidate)
        request_body = {
            "contract_version": self.contract_version,
            "memory": {
                "id": str(candidate["id"]),
                "memory_scope_id": str(candidate["target_memory_scope_id"]),
                "version": version,
                "content": {
                    **dict(consolidated_content),
                    "source_artifact_uri": str(candidate["content_uri"]),
                },
                "source_run_id": str(candidate["run_id"]),
                "source_profile_id": str(candidate["profile_id"]),
                "sensitivity": str(candidate["sensitivity"]),
                "retention_policy": str(candidate["retention_policy"]),
            },
        }
        return self.client.ingest_memory(request_body)


def _validate_candidate(candidate: Mapping[str, Any]) -> None:
    required_fields = {
        "id",
        "run_id",
        "profile_id",
        "target_memory_scope_id",
        "content_uri",
        "sensitivity",
        "retention_policy",
        "validator_status",
        "policy_status",
    }
    missing = sorted(field for field in required_fields if field not in candidate)
    if missing:
        raise MemoryFeedbackError("Memory candidate is missing fields: " + ", ".join(missing))
    if candidate["validator_status"] != "approved":
        raise MemoryFeedbackError("Memory candidate validator_status must be approved.")
    if candidate["policy_status"] != "approved":
        raise MemoryFeedbackError("Memory candidate policy_status must be approved.")
