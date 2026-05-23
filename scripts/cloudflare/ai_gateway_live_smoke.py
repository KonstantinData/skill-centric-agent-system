from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_CONTROL_API_URL = "https://scas-control-api-dev.still-butterfly-bbff.workers.dev"
DEFAULT_REQUEST_FILE = "examples/control-api/ai-gateway-chat-request.json"
USER_AGENT = "skill-centric-agent-system/0.1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a live smoke test against the Control API AI Gateway route.",
    )
    parser.add_argument(
        "--control-api-url",
        default=os.getenv("SCAS_CONTROL_API_URL", DEFAULT_CONTROL_API_URL),
        help="Cloudflare Control API base URL.",
    )
    parser.add_argument(
        "--control-api-token",
        default=os.getenv("SCAS_CONTROL_API_TOKEN"),
        help="Bearer token for the AI Gateway route. Defaults to SCAS_CONTROL_API_TOKEN.",
    )
    parser.add_argument(
        "--request-file",
        default=DEFAULT_REQUEST_FILE,
        help="Minimal OpenAI chat completions request JSON file.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="HTTP timeout for the live smoke request.",
    )
    args = parser.parse_args(argv)

    if not args.control_api_token:
        raise SystemExit("SCAS_CONTROL_API_TOKEN or --control-api-token is required.")

    request_body = _load_json(Path(args.request_file))
    response_body = _post_json(
        base_url=args.control_api_url,
        token=args.control_api_token,
        body=request_body,
        timeout_seconds=args.timeout_seconds,
    )

    choices = response_body.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        raise SystemExit("AI Gateway smoke response did not contain chat choices.")

    print(
        json.dumps(
            {
                "status": "passed",
                "model": response_body.get("model"),
                "choice_count": len(choices),
                "usage": _safe_usage(response_body.get("usage")),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _post_json(
    *,
    base_url: str,
    token: str,
    body: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/ai-gateway/openai/chat/completions"
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "accept": "application/json",
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "user-agent": USER_AGENT,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"AI Gateway smoke failed with HTTP {error.code}: {_compact_error(detail)}"
        ) from error
    except URLError as error:
        raise SystemExit(f"AI Gateway smoke request failed: {error}") from error

    parsed = json.loads(response_text)
    if not isinstance(parsed, dict):
        raise SystemExit("AI Gateway smoke response must be a JSON object.")
    return parsed


def _load_json(path: Path) -> dict[str, Any]:
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return parsed


def _safe_usage(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    safe: dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        candidate = value.get(key)
        if isinstance(candidate, int):
            safe[key] = candidate
    return safe or None


def _compact_error(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value[:500]
    if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
        error = parsed["error"]
        code = error.get("code")
        message = error.get("message")
        return f"{code}: {message}"
    return value[:500]


if __name__ == "__main__":
    raise SystemExit(main())
