from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from skill_centric_agent_system.runtime.models import slug_id

SENSITIVE_KEY_PARTS = (
    "authorization",
    "api-key",
    "api_key",
    "apikey",
    "password",
    "private-key",
    "private_key",
    "secret",
    "ssh-key",
    "ssh_key",
    "token",
)
REDACTED = "[REDACTED]"


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                redacted[key_text] = REDACTED
            else:
                redacted[key_text] = redact_sensitive_data(nested)
        return redacted
    if isinstance(value, list | tuple):
        return [redact_sensitive_data(item) for item in value]
    return value


class JsonArtifactStore:
    """Write runtime event/checkpoint payloads as JSON artifacts."""

    def __init__(
        self,
        root: str | Path,
        *,
        uri_prefix: str = "hetzner://runtime",
    ) -> None:
        self.root = Path(root)
        self.uri_prefix = uri_prefix.rstrip("/")

    @property
    def root_uri(self) -> str:
        return self.uri_prefix

    def write_json(
        self,
        relative_path: str | Path | Sequence[str],
        payload: Any,
        *,
        redact: bool = True,
    ) -> str:
        relative = _relative_path(relative_path)
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        artifact_payload = redact_sensitive_data(payload) if redact else payload
        target.write_text(
            json.dumps(artifact_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return self.uri_for(relative)

    def uri_for(self, relative_path: str | Path | Sequence[str]) -> str:
        relative = _relative_path(relative_path).as_posix()
        if not relative:
            return self.root_uri
        return f"{self.root_uri}/{relative}"


def _relative_path(relative_path: str | Path | Sequence[str]) -> Path:
    if isinstance(relative_path, str | Path):
        raw_parts = Path(relative_path).parts
    else:
        raw_parts = tuple(relative_path)

    safe_parts = [slug_id(str(part).removesuffix(".json")) for part in raw_parts if str(part)]
    if not safe_parts:
        return Path()
    *directories, filename = safe_parts
    return Path(*directories) / f"{filename}.json"


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace(" ", "-")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)
