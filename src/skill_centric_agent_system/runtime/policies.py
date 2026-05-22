from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def profile_redacts_sensitive_data(profile: Mapping[str, Any]) -> bool:
    observability = profile.get("observability", {})
    if not isinstance(observability, Mapping):
        return True
    value = observability.get("redact_sensitive_data", True)
    return bool(value)
