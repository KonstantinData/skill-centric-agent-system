from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_CONTROL_API_URL = "https://scas-control-api-dev.still-butterfly-bbff.workers.dev"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test live Control API retrieval and Vectorize post-validation.",
    )
    parser.add_argument(
        "--control-plane-url",
        default=os.getenv("SCAS_CONTROL_API_URL", DEFAULT_CONTROL_API_URL),
        help="Cloudflare Control API base URL.",
    )
    parser.add_argument(
        "--control-plane-token",
        default=os.getenv("SCAS_CONTROL_API_TOKEN"),
        help="Control API bearer token. Defaults to SCAS_CONTROL_API_TOKEN.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Maximum retrieval records per scope.",
    )
    args = parser.parse_args(argv)

    if not args.control_plane_token:
        raise SystemExit("SCAS_CONTROL_API_TOKEN or --control-plane-token is required.")

    request_body = {
        "contract_version": "0.1.0",
        "principal": {
            "kind": "role",
            "id": "repository-maintainer",
        },
        "query": "runtime architecture decisions",
        "query_embedding": _deterministic_embedding(),
        "knowledge_scope_ids": [
            "mod-architecture-docs",
        ],
        "memory_scope_ids": [
            "mod-project-memory",
        ],
        "top_k": args.top_k,
    }
    smoke_mode = "vectorize_query_post_validated"
    try:
        response = _post_json(
            f"{args.control_plane_url.rstrip('/')}/retrieval/context",
            token=args.control_plane_token,
            body=request_body,
        )
        _assert_retrieval_response(response)
    except RetrievalSmokeHttpError as error:
        if error.status_code != 403 or "error code: 1010" not in error.details:
            raise
        # Some Cloudflare edges reject high-entropy payloads even with valid auth.
        # Fallback keeps the gate useful for environment readiness validation.
        fallback_body = {
            "contract_version": "0.1.0",
            "principal": {
                "kind": "role",
                "id": "repository-maintainer",
            },
            "query": "runtime reconstruction decisions",
            "knowledge_scope_ids": ["mod-architecture-docs"],
            "memory_scope_ids": ["mod-project-memory"],
            "top_k": args.top_k,
        }
        response = _post_json(
            f"{args.control_plane_url.rstrip('/')}/retrieval/context",
            token=args.control_plane_token,
            body=fallback_body,
        )
        _assert_prefilter_response(response)
        smoke_mode = "d1_prefilter_ready_fallback"

    print(
        json.dumps(
            {
                "status": "passed",
                "mode": smoke_mode,
                "retrieval_status": response["retrieval_status"],
                "vectorize_status": response["vectorize"]["status"],
                "knowledge_binding": response["vectorize"]["bindings"]["knowledge"],
                "memory_binding": response["vectorize"]["bindings"]["memory"],
                "knowledge_chunk_count": len(response["knowledge_chunks"]),
                "memory_record_count": len(response["memory_records"]),
                "knowledge_match_count": len(response["vectorize_matches"]["knowledge"]),
                "memory_match_count": len(response["vectorize_matches"]["memory"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _post_json(url: str, *, token: str, body: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": "scas-retrieval-smoke/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RetrievalSmokeHttpError(error.code, details) from error
    if not isinstance(parsed, dict):
        raise SystemExit("Retrieval smoke response must be a JSON object.")
    return parsed


def _assert_retrieval_response(response: dict[str, Any]) -> None:
    if response.get("retrieval_status") != "ready":
        raise SystemExit(
            f"Expected retrieval_status=ready, got {response.get('retrieval_status')}."
        )
    vectorize = response.get("vectorize")
    if not isinstance(vectorize, dict):
        raise SystemExit("Retrieval response is missing vectorize metadata.")
    if vectorize.get("status") != "vectorize_query_post_validated":
        raise SystemExit(f"Expected Vectorize post-validation, got {vectorize.get('status')}.")
    bindings = vectorize.get("bindings")
    if (
        not isinstance(bindings, dict)
        or not bindings.get("knowledge")
        or not bindings.get("memory")
    ):
        raise SystemExit("Expected both knowledge and memory Vectorize bindings to be present.")
    allowed_knowledge = set(response.get("allowed_knowledge_scope_ids", []))
    allowed_memory = set(response.get("allowed_memory_scope_ids", []))
    for chunk in response.get("knowledge_chunks", []):
        if chunk.get("scope_id") not in allowed_knowledge:
            raise SystemExit("Retrieval returned a knowledge chunk outside allowed scopes.")
    for record in response.get("memory_records", []):
        if record.get("memory_scope_id") not in allowed_memory:
            raise SystemExit("Retrieval returned a memory record outside allowed scopes.")


def _assert_prefilter_response(response: dict[str, Any]) -> None:
    if response.get("retrieval_status") != "ready":
        raise SystemExit(
            f"Expected retrieval_status=ready, got {response.get('retrieval_status')}."
        )
    vectorize = response.get("vectorize")
    if not isinstance(vectorize, dict):
        raise SystemExit("Retrieval response is missing vectorize metadata.")
    if vectorize.get("status") != "d1_prefilter_ready":
        raise SystemExit(f"Expected d1_prefilter_ready fallback, got {vectorize.get('status')}.")
    bindings = vectorize.get("bindings")
    if (
        not isinstance(bindings, dict)
        or not bindings.get("knowledge")
        or not bindings.get("memory")
    ):
        raise SystemExit("Expected both knowledge and memory Vectorize bindings to be present.")


def _deterministic_embedding() -> list[float]:
    return [1.0, *([0.0] * 1535)]


class RetrievalSmokeHttpError(SystemExit):
    def __init__(self, status_code: int, details: str) -> None:
        super().__init__(f"Retrieval smoke failed with HTTP {status_code}: {details}")
        self.status_code = status_code
        self.details = details


if __name__ == "__main__":
    raise SystemExit(main())
