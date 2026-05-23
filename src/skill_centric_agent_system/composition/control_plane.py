from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ControlPlaneClientError(RuntimeError):
    """Raised when the Control Plane endpoint cannot provide composition context."""


CONTROL_PLANE_USER_AGENT = "skill-centric-agent-system/0.1"


@dataclass(frozen=True)
class ControlPlaneClient:
    base_url: str
    timeout_seconds: float = 10.0
    api_token: str | None = None

    def composition_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        return self._post_json("/composition/context", request_body)

    def retrieval_context(self, request_body: Mapping[str, Any]) -> dict[str, Any]:
        return self._post_json("/retrieval/context", request_body)

    def _post_json(self, path: str, request_body: Mapping[str, Any]) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        request = Request(
            url,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "accept": "application/json",
                "user-agent": CONTROL_PLANE_USER_AGENT,
                **self._authorization_headers(),
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise ControlPlaneClientError(
                f"Control Plane returned HTTP {error.code}: {detail}"
            ) from error
        except URLError as error:
            raise ControlPlaneClientError(f"Control Plane request failed: {error}") from error

        parsed = json.loads(response_body)
        if not isinstance(parsed, dict):
            raise ControlPlaneClientError("Control Plane response must be a JSON object.")
        return parsed

    def _authorization_headers(self) -> dict[str, str]:
        token = self.api_token or os.getenv("SCAS_CONTROL_API_TOKEN")
        if token is None or not token.strip():
            return {}
        return {"authorization": f"Bearer {token.strip()}"}
