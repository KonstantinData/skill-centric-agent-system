from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

API_BASE = "https://api.cloudflare.com/client/v4"
PRIMARY_HOSTNAME = "es-daskuechenhaus.de"
PRIMARY_APP_NAME = "es-daskuechenhaus.de Einsatzsteuerung"
POLICY_NAME = "Allow DKH operators with MFA"


@dataclass(frozen=True)
class CloudflareConfig:
    account_id: str
    zone_id: str
    token: str


class CloudflareApiError(RuntimeError):
    pass


def parse_emails(raw_value: str) -> list[str]:
    emails = [value.strip().casefold() for value in raw_value.split(",") if value.strip()]
    invalid = [email for email in emails if "@" not in email or email.startswith("@")]
    if invalid:
        raise ValueError(f"Invalid allowed email value(s): {', '.join(invalid)}")
    return sorted(set(emails))


def load_config() -> CloudflareConfig:
    account_id = os.environ.get("DKH_CLOUDFLARE_ACCOUNT_ID") or os.environ.get(
        "CLOUDFLARE_ACCOUNT_ID", ""
    )
    zone_id = os.environ.get("DKH_CLOUDFLARE_ZONE_ID") or os.environ.get(
        "CLOUDFLARE_ZONE_ID", ""
    )
    token = os.environ.get("DKH_CLOUDFLARE_API_TOKEN") or os.environ.get(
        "CLOUDFLARE_API_TOKEN", ""
    )
    missing = [
        name
        for name, value in (
            ("DKH_CLOUDFLARE_ACCOUNT_ID", account_id),
            ("DKH_CLOUDFLARE_ZONE_ID", zone_id),
            ("DKH_CLOUDFLARE_API_TOKEN", token),
        )
        if not value.strip()
    ]
    if missing:
        raise ValueError(f"Missing Cloudflare environment value(s): {', '.join(missing)}")
    return CloudflareConfig(account_id=account_id.strip(), zone_id=zone_id.strip(), token=token)


def cf_request(
    config: CloudflareConfig,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = None
    headers = {
        "authorization": f"Bearer {config.token}",
        "accept": "application/json",
        "content-type": "application/json",
        "user-agent": "scas-dkh-access-bootstrap/1.0",
    }
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
    api_request = request.Request(
        f"{API_BASE}{path}",
        data=payload,
        headers=headers,
        method=method,
    )
    try:
        with request.urlopen(api_request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise CloudflareApiError(f"Cloudflare API {method} {path} failed: {details}") from exc
    result = json.loads(response_body)
    if not result.get("success", False):
        raise CloudflareApiError(f"Cloudflare API {method} {path} returned errors: {result}")
    return result


def ensure_dns_record(config: CloudflareConfig, hostname: str, apply: bool) -> str:
    encoded_name = parse.quote(hostname, safe="")
    path = f"/zones/{config.zone_id}/dns_records?type=AAAA&name={encoded_name}&per_page=100"
    records = cf_request(config, "GET", path).get("result", [])
    payload = {
        "type": "AAAA",
        "name": hostname,
        "content": "100::",
        "ttl": 1,
        "proxied": True,
        "comment": "SCAS-managed placeholder for Worker route protected by Cloudflare Access.",
    }
    if records:
        record_id = records[0]["id"]
        if apply:
            cf_request(config, "PUT", f"/zones/{config.zone_id}/dns_records/{record_id}", payload)
        return "updated" if apply else "would update"
    if apply:
        cf_request(config, "POST", f"/zones/{config.zone_id}/dns_records", payload)
    return "created" if apply else "would create"


def access_app_name(hostname: str) -> str:
    if hostname == PRIMARY_HOSTNAME:
        return PRIMARY_APP_NAME
    return f"{hostname} Einsatzsteuerung"


def find_access_app(config: CloudflareConfig, hostname: str) -> dict[str, Any] | None:
    apps = cf_request(
        config,
        "GET",
        f"/accounts/{config.account_id}/access/apps?per_page=100",
    ).get("result", [])
    expected_name = access_app_name(hostname)
    return next(
        (
            app
            for app in apps
            if app.get("domain") == hostname
            or app.get("name") == expected_name
            or (hostname == PRIMARY_HOSTNAME and app.get("name") == PRIMARY_APP_NAME)
        ),
        None,
    )


def access_app_payload(hostname: str) -> dict[str, Any]:
    return {
        "name": access_app_name(hostname),
        "domain": hostname,
        "type": "self_hosted",
        "session_duration": "8h",
        "app_launcher_visible": False,
        "auto_redirect_to_identity": False,
        "enable_binding_cookie": True,
        "http_only_cookie_attribute": True,
        "same_site_cookie_attribute": "strict",
    }


def ensure_access_app(
    config: CloudflareConfig,
    hostname: str,
    apply: bool,
) -> tuple[str, str | None]:
    existing = find_access_app(config, hostname)
    payload = access_app_payload(hostname)
    if existing:
        app_id = str(existing["id"])
        if apply:
            cf_request(
                config,
                "PUT",
                f"/accounts/{config.account_id}/access/apps/{app_id}",
                payload,
            )
        return ("updated" if apply else "would update", app_id)
    if not apply:
        return "would create", None
    created = cf_request(config, "POST", f"/accounts/{config.account_id}/access/apps", payload)
    return "created", str(created["result"]["id"])


def policy_payload(allowed_emails: list[str]) -> dict[str, Any]:
    return {
        "name": POLICY_NAME,
        "decision": "allow",
        "precedence": 1,
        "include": [{"email": {"email": email}} for email in allowed_emails],
        "mfa_config": {
            "mfa_disabled": False,
            "allowed_authenticators": ["totp", "security_key", "biometrics"],
            "session_duration": "12h",
        },
    }


def ensure_access_policy(
    config: CloudflareConfig,
    app_id: str | None,
    allowed_emails: list[str],
    apply: bool,
) -> str:
    if app_id is None:
        return "would create"
    policies_path = f"/accounts/{config.account_id}/access/apps/{app_id}/policies"
    policies = cf_request(config, "GET", f"{policies_path}?per_page=100").get("result", [])
    payload = policy_payload(allowed_emails)
    existing = next((policy for policy in policies if policy.get("name") == POLICY_NAME), None)
    if existing:
        if apply:
            cf_request(config, "PUT", f"{policies_path}/{existing['id']}", payload)
        return "updated" if apply else "would update"
    if apply:
        cf_request(config, "POST", policies_path, payload)
    return "created" if apply else "would create"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hostname", default="es-daskuechenhaus.de")
    parser.add_argument("--allowed-emails", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    emails = parse_emails(args.allowed_emails)
    if not emails:
        raise ValueError("allowed_emails is required when --apply is used.")

    config = load_config()
    app_status, app_id = ensure_access_app(config, args.hostname, args.apply)
    policy_status = ensure_access_policy(config, app_id, emails, args.apply)
    dns_status = ensure_dns_record(config, args.hostname, args.apply)

    print(
        json.dumps(
            {
                "hostname": args.hostname,
                "access_app": app_status,
                "access_policy": policy_status,
                "dns_record": dns_status,
                "allowed_email_count": len(emails),
                "applied": args.apply,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
