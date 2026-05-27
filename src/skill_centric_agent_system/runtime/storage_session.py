from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from skill_centric_agent_system.runtime.storage_memory import InMemoryRuntimeStore
from skill_centric_agent_system.runtime.storage_postgres import PostgresRuntimeStore
from skill_centric_agent_system.runtime.storage_protocol import RuntimeStore


class RuntimeStorageError(RuntimeError):
    """Raised when runtime storage cannot be opened or used."""


@dataclass
class RuntimeStoreSession:
    """Own the lifecycle of a runtime store and its optional backing connection."""

    store: RuntimeStore
    connection: Any | None = None

    def __enter__(self) -> RuntimeStoreSession:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        if self.connection is None:
            return False

        try:
            if exc_type is None and hasattr(self.connection, "commit"):
                self.connection.commit()
            elif exc_type is not None and hasattr(self.connection, "rollback"):
                self.connection.rollback()
        finally:
            if hasattr(self.connection, "close"):
                self.connection.close()
        return False


def open_runtime_store_session(
    *,
    mode: str,
    database_url: str | None = None,
    connector: Callable[[str], Any] | None = None,
) -> RuntimeStoreSession:
    """Open a runtime storage session for local memory or Hetzner PostgreSQL."""

    if mode == "memory":
        return RuntimeStoreSession(store=InMemoryRuntimeStore())

    if mode != "postgres":
        raise RuntimeStorageError(f"Unsupported runtime storage mode: {mode}.")

    dsn = database_url or os.getenv("SCAS_RUNTIME_DATABASE_URL")
    if not dsn:
        raise RuntimeStorageError(
            "Postgres runtime storage requires --database-url or "
            "SCAS_RUNTIME_DATABASE_URL."
        )

    connection = connector(dsn) if connector is not None else _connect_psycopg(dsn)
    return RuntimeStoreSession(
        store=PostgresRuntimeStore(connection),
        connection=connection,
    )


def _connect_psycopg(database_url: str) -> Any:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - depends on optional extra.
        raise RuntimeStorageError(
            "Postgres runtime storage requires the optional runtime dependency: "
            "pip install 'skill-centric-agent-system[runtime]'."
        ) from exc

    return psycopg.connect(database_url, row_factory=dict_row)


def profile_summary(profile: Mapping[str, Any]) -> dict[str, Any]:
    from skill_centric_agent_system.runtime.models import selected_modules

    return {
        "profile_id": profile["id"],
        "profile_version": profile["profile_version"],
        "selected_modules": selected_modules(profile),
        "limits": profile["limits"],
        "observability": profile["observability"],
    }

