from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SECURITY_SCRIPTS = REPO_ROOT / "scripts" / "security"
sys.path.insert(0, str(SECURITY_SCRIPTS))

import validate_security_closure  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "schemas" / "production-security-closure.schema.json"
POLICY_PATH = REPO_ROOT / "policies" / "security" / "production-security-closure.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_security_closure_schema_and_policy_are_valid() -> None:
    schema = load_json(SCHEMA_PATH)
    policy = load_json(POLICY_PATH)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(policy)
    assert validate_security_closure.validate_security_closure(REPO_ROOT) == []


def test_security_closure_requires_all_token_reviews(tmp_path: Path) -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["token_scope_reviews"] = policy["token_scope_reviews"][:-1]
    policy_path = tmp_path / "security-closure.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    failures = validate_security_closure.validate_security_closure(REPO_ROOT, policy_path)

    assert any("missing token scope reviews" in failure for failure in failures)


def test_security_closure_requires_all_security_gates(tmp_path: Path) -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["required_gates"] = policy["required_gates"][:-1]
    policy_path = tmp_path / "security-closure.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    failures = validate_security_closure.validate_security_closure(REPO_ROOT, policy_path)

    assert any("missing required security gates" in failure for failure in failures)


def test_security_closure_rejects_open_remediation(tmp_path: Path) -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["finding_closure"]["remediation_required"] = ["fix-auth-bypass"]
    policy_path = tmp_path / "security-closure.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    failures = validate_security_closure.validate_security_closure(REPO_ROOT, policy_path)

    assert any("remediation_required" in failure for failure in failures)


def test_security_closure_rejects_secret_like_values(tmp_path: Path) -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["token_scope_reviews"][0]["rotation"] = (
        "-----BEGIN " + "OPENSSH PRIVATE KEY-----"
    )
    policy_path = tmp_path / "security-closure.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    failures = validate_security_closure.validate_security_closure(REPO_ROOT, policy_path)

    assert any("secret-like value" in failure for failure in failures)


def test_security_closure_rejects_unsafe_waiver_policy(tmp_path: Path) -> None:
    policy = deepcopy(load_json(POLICY_PATH))
    policy["waiver_policy"]["allows_unaudited_production_claims"] = True
    policy_path = tmp_path / "security-closure.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    failures = validate_security_closure.validate_security_closure(REPO_ROOT, policy_path)

    assert any("allows_unaudited_production_claims" in failure for failure in failures)
