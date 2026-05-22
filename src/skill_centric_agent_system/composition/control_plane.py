from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ControlPlaneClientError(RuntimeError):
    """Raised when the Control Plane endpoint cannot provide composition context."""


@dataclass(frozen=True)
class ControlPlaneClient:
    base_url: str
    timeout_seconds: float = 10.0

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
