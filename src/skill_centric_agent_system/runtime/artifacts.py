from __future__ import annotations

import json
import re
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
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"\b("
    r"api[-_ ]?key|apikey|password|private[-_ ]?key|secret|"
    r"ssh[-_ ]?key|token"
    r")\b(\s*[:=]\s*)([^\s'\",;]+)",
    re.IGNORECASE,
)
AUTHORIZATION_BEARER_PATTERN = re.compile(
    r"\bAuthorization(\s*:\s*)Bearer\s+[A-Za-z0-9._~+/=-]+",
    re.IGNORECASE,
)
BEARER_TOKEN_PATTERN = re.compile(
    r"\bBearer\s+[A-Za-z0-9._~+/=-]+",
    re.IGNORECASE,
)
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)


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
    if isinstance(value, str):
        return _redact_sensitive_string(value)
    return value


class JsonArtifactStore:
    """Write runtime event/checkpoint payloads as JSON artifacts."""

    def __init__(
        self,
        root: str | Path,
        *,
        uri_prefix: str = "hetzner://runtime",
        chunk_string_threshold_bytes: int = 64_000,
        chunk_size_bytes: int = 32_000,
    ) -> None:
        self.root = Path(root)
        self.uri_prefix = uri_prefix.rstrip("/")
        self.chunk_string_threshold_bytes = chunk_string_threshold_bytes
        self.chunk_size_bytes = chunk_size_bytes

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
        artifact_payload = self._chunk_large_strings(
            artifact_payload,
            relative.with_suffix(""),
        )
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

    def _chunk_large_strings(self, payload: Any, base_path: Path) -> Any:
        return self._chunk_large_strings_at(payload, base_path, ())

    def _chunk_large_strings_at(
        self,
        value: Any,
        base_path: Path,
        field_path: tuple[str, ...],
    ) -> Any:
        if isinstance(value, str):
            encoded = value.encode("utf-8")
            if len(encoded) <= self.chunk_string_threshold_bytes:
                return value
            return self._write_chunked_text(base_path, field_path, encoded)
        if isinstance(value, Mapping):
            return {
                key: self._chunk_large_strings_at(
                    nested,
                    base_path,
                    (*field_path, str(key)),
                )
                for key, nested in value.items()
            }
        if isinstance(value, list):
            return [
                self._chunk_large_strings_at(nested, base_path, (*field_path, str(index)))
                for index, nested in enumerate(value)
            ]
        return value

    def _write_chunked_text(
        self,
        base_path: Path,
        field_path: tuple[str, ...],
        encoded: bytes,
    ) -> dict[str, Any]:
        chunks: list[dict[str, Any]] = []
        chunk_dir = base_path / "chunks" / _field_path(field_path)
        for index, start in enumerate(range(0, len(encoded), self.chunk_size_bytes)):
            chunk = encoded[start : start + self.chunk_size_bytes]
            relative = chunk_dir / f"{index:04d}.txt"
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(chunk)
            chunks.append(
                {
                    "index": index,
                    "uri": self.uri_for_raw(relative),
                    "byte_start": start,
                    "byte_length": len(chunk),
                }
            )

        manifest_relative = chunk_dir / "manifest.json"
        manifest = {
            "artifact_kind": "chunked_text",
            "encoding": "utf-8",
            "byte_length": len(encoded),
            "chunk_size_bytes": self.chunk_size_bytes,
            "chunk_count": len(chunks),
            "chunks": chunks,
        }
        manifest_target = self.root / manifest_relative
        manifest_target.parent.mkdir(parents=True, exist_ok=True)
        manifest_target.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "artifact_ref": "chunked_text",
            "manifest_uri": self.uri_for_raw(manifest_relative),
            "encoding": "utf-8",
            "byte_length": len(encoded),
            "chunk_count": len(chunks),
        }

    def uri_for_raw(self, relative_path: str | Path) -> str:
        relative = Path(relative_path).as_posix()
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


def _field_path(parts: tuple[str, ...]) -> Path:
    safe_parts = [slug_id(part) for part in parts if part]
    if not safe_parts:
        return Path("root")
    return Path(*safe_parts)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace(" ", "-")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _redact_sensitive_string(value: str) -> str:
    redacted = PRIVATE_KEY_PATTERN.sub(REDACTED, value)
    redacted = AUTHORIZATION_BEARER_PATTERN.sub(
        lambda match: f"Authorization{match.group(1)}Bearer {REDACTED}",
        redacted,
    )
    redacted = BEARER_TOKEN_PATTERN.sub(f"Bearer {REDACTED}", redacted)
    return SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}",
        redacted,
    )
