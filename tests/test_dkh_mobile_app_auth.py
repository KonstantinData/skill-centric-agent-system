from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CRM_ROOT = REPO_ROOT / "apps" / "dkh-crm"
IOS_ROOT = REPO_ROOT / "apps" / "dkh-ios"
ADMIN_API = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus_admin_api.py"
MOBILE_MIGRATION = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0015_mobile_app_identities.sql"
)
CRM_DEPLOY = REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-crm-deploy.yml"
ADMIN_DEPLOY = REPO_ROOT / ".github" / "workflows" / "es-daskuechenhaus-admin-api-deploy.yml"
RUNBOOK = REPO_ROOT / "docs" / "runbooks" / "es-daskuechenhaus-protected-site.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mobile_auth_uses_apple_identity_tokens_not_cloudflare_access() -> None:
    apple_auth = read(CRM_ROOT / "src" / "lib" / "apple-auth.ts")
    mobile_session = read(CRM_ROOT / "src" / "lib" / "mobile-session.ts")
    route = read(CRM_ROOT / "src" / "app" / "api" / "mobile" / "session" / "route.ts")
    data_route = read(CRM_ROOT / "src" / "app" / "api" / "mobile" / "[resource]" / "route.ts")
    middleware = read(CRM_ROOT / "src" / "middleware.ts")

    assert "https://appleid.apple.com/auth/keys" in apple_auth
    assert "jwtVerify(identityToken" in apple_auth
    assert "DKH_IOS_APP_BUNDLE_ID" in apple_auth
    assert "resolveMobileIdentity" in mobile_session
    assert "/mobile/apple-session" in mobile_session
    assert "DKH_MOBILE_SESSION_SECRET" in mobile_session
    assert "verifyMobileSessionToken" in mobile_session
    assert "identity_token" in route
    assert "createMobileSessionToken" in route
    assert "fetchDkhJson" in data_route
    assert '"overview/state"' in data_route
    assert '"customers/state"' in data_route
    assert "session.email" in data_route
    assert "missing_mobile_session" in data_route
    assert 'request.nextUrl.pathname.startsWith("/api/mobile/")' in middleware
    assert "resolveAccessEmail(request)" in middleware
    assert 'const BROWSER_STRIP_HEADERS = ["authorization", ...ACCESS_CONTEXT_HEADERS];' in middleware

    mobile_middleware_block = middleware.split(
        'if (request.nextUrl.pathname.startsWith("/api/mobile/"))',
        maxsplit=1,
    )[1].split("for (const header of BROWSER_STRIP_HEADERS)", maxsplit=1)[0]
    assert "for (const header of ACCESS_CONTEXT_HEADERS)" in mobile_middleware_block
    assert '"authorization"' not in mobile_middleware_block


def test_mobile_identity_mapping_is_server_side_and_seeded_as_pending_invite() -> None:
    migration = read(MOBILE_MIGRATION)
    admin_api = read(ADMIN_API)

    assert "CREATE TABLE IF NOT EXISTS app.mobile_app_identities" in migration
    assert "apple_subject TEXT" in migration
    assert "expected_apple_email TEXT" in migration
    assert "status IN ('pending', 'requested', 'active', 'revoked')" in migration
    assert "'konstantin@milonas.email'" in migration
    assert "'k.milonas@schober-daskuechenhaus.de'" in migration
    assert "mobile_apple_session" in admin_api
    assert 'parts == ["mobile", "apple-session"]' in admin_api
    assert "identity.status = 'pending'" in admin_api
    assert "identity.status = 'active'" in admin_api
    assert 'urlparse(self.path).path == "/mobile/apple-session"' in admin_api


def test_mobile_api_deploy_keeps_browser_access_separate() -> None:
    deploy = read(CRM_DEPLOY)
    admin_deploy = read(ADMIN_DEPLOY)
    runbook = read(RUNBOOK)
    ios_readme = read(IOS_ROOT / "README.md")

    assert "mobile_api_hostnames" in deploy
    assert "app.es-daskuechenhaus.de" in deploy
    assert "Verify Cloudflare Access remains the public entrypoint" in deploy
    assert "Verify mobile API bypasses Cloudflare Access" in deploy
    assert "DKH_MOBILE_SESSION_SECRET" in deploy
    assert "0015_mobile_app_identities.sql" in admin_deploy
    assert "Cloudflare Access does not protect `app.es-daskuechenhaus.de`" in runbook
    assert "Cloudflare Access remains unchanged for the browser hosts" in ios_readme
