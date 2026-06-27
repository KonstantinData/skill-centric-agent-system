from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_ROOT = REPO_ROOT / "packages" / "tenant-workbench-domain"
CLIENT_ROOT = REPO_ROOT / "packages" / "tenant-workbench-client"
UI_ROOT = REPO_ROOT / "packages" / "tenant-workbench-ui"
KHH_WEB_ROOT = REPO_ROOT / "apps" / "khh-workbench"
KHH_NATIVE_PROOF_ROOT = REPO_ROOT / "apps" / "khh-mobile-proof"


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def read_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_platform_neutral_adr_defines_native_ready_tenant_workbench_path() -> None:
    adr = read("docs/adr/0012-platform-neutral-tenant-workbench-architecture.md")

    assert "## Status\n\nAccepted" in adr
    assert "tenant_kinderhaus" in adr
    assert "kinderhaus-heuschrecken.cloud" in adr
    assert "React Native for Web / Expo-compatible boundaries" in adr
    assert "auth, navigation, offline behavior, push" in adr
    assert "device permissions" in adr
    assert "does not require shipping native apps in the current sprint" in adr


def test_platform_neutral_readiness_backlog_has_estimate_and_milestones() -> None:
    roadmap = read("docs/roadmap/platform-neutral-app-readiness.md")

    assert "Planning total: 17.5 implementation days." in roadmap
    assert "Recommended sprint allocation: 18 implementation days plus review buffer." in roadmap
    assert "### M1: Native-Ready Architecture Contract" in roadmap
    assert "### M2: Shared Workbench Foundation" in roadmap
    assert "### M3: Shared UI And Web Shell Migration" in roadmap
    assert "### M4: Native Proof And Gates" in roadmap
    assert "No new KHH feature work bypasses the shared architecture path." in roadmap


def test_repository_docs_route_khh_workbench_through_platform_neutral_plan() -> None:
    architecture = read("docs/reference/architecture.md")
    repository_roadmap = read("docs/reference/repository-roadmap.md")
    execution_queue = read("docs/roadmap/scas-execution-queue.md")
    docs_index = read("docs/README.md")

    for document in (architecture, repository_roadmap, execution_queue, docs_index):
        assert "platform-neutral" in document

    assert "ADR-0012" in architecture
    assert "docs/roadmap/platform-neutral-app-readiness.md" in architecture
    assert "Phase 9: Platform-Neutral Tenant Workbench Readiness" in repository_roadmap
    assert "tenant_kinderhaus" in repository_roadmap
    assert "Native-Ready Architecture Contract" in execution_queue
    assert "apps/khh-workbench/" in docs_index


def test_shared_khh_domain_has_no_react_next_dom_or_icon_imports() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((DOMAIN_ROOT / "src").glob("*.ts"))
    )

    forbidden = (
        "react",
        "next/",
        "lucide-react",
        "window",
        "document.",
        "document[",
        "localStorage",
        "<div",
        "<section",
    )
    for marker in forbidden:
        assert marker not in combined

    assert "iconId" in combined
    assert "privacyClass" in combined
    assert "tenant_kinderhaus" in combined
    assert "kinderhaus-heuschrecken" in combined


def test_shared_ui_contract_has_no_next_or_dom_imports() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((UI_ROOT / "src").glob("*.ts"))
    )

    for marker in ("next/", "next/image", "next/link", "HTMLElement", "<div", "<section"):
        assert marker not in combined

    assert "DashboardViewModel" in combined
    assert "SectionViewModel" in combined


def test_khh_web_shell_consumes_shared_domain_client_and_ui_contracts() -> None:
    page = read_path(KHH_WEB_ROOT / "src" / "app" / "page.tsx")
    section_page = read_path(KHH_WEB_ROOT / "src" / "app" / "[section]" / "page.tsx")
    sidebar = read_path(KHH_WEB_ROOT / "src" / "components" / "chrome" / "sidebar.tsx")
    bottom_nav = read_path(KHH_WEB_ROOT / "src" / "components" / "chrome" / "bottom-nav.tsx")
    workbench_data = read_path(KHH_WEB_ROOT / "src" / "lib" / "workbench-data.ts")

    assert "createKhhWorkbenchClient" in page
    assert "createDashboardViewModel" in page
    assert "createSectionViewModel" in section_page
    assert "createNavigationViewModel" in sidebar
    assert "createMobileNavigationViewModel" in bottom_nav
    assert "lucide-react" not in workbench_data
    assert "export * from \"@scas/tenant-workbench-domain\"" in workbench_data


def test_khh_docker_build_context_includes_shared_packages() -> None:
    dockerfile = read("deploy/khh-workbench/Dockerfile")

    assert "COPY packages ./packages" in dockerfile
    assert "RUN npm run --prefix apps/khh-workbench build" in dockerfile


def test_native_proof_shell_uses_same_khh_contracts_and_native_runtime_policy() -> None:
    app = read_path(KHH_NATIVE_PROOF_ROOT / "App.tsx")
    package_json = read_path(KHH_NATIVE_PROOF_ROOT / "package.json")
    readme = read_path(KHH_NATIVE_PROOF_ROOT / "README.md")

    assert '"expo": "~56.0.0"' in package_json
    assert '"react-native": "0.85.0"' in package_json
    assert "createKhhWorkbenchClient" in app
    assert "createDashboardViewModel" in app
    assert "readOnlySummaryOfflinePolicy" in app
    assert "khhNativePushPolicy" in app
    assert "tenant-scoped storage keys" in readme
    assert "no sensitive payloads" in readme


def test_shared_client_fails_closed_for_tenant_scope_and_native_storage() -> None:
    client = read_path(CLIENT_ROOT / "src" / "index.ts")
    native_contracts = read_path(CLIENT_ROOT / "src" / "native-contracts.ts")

    assert "TenantScopeError" in client
    assert "Tenant workbench scope mismatch" in client
    assert "assertTenantScopeMatches" in client
    assert "tenantId: scope.tenantId" in client
    assert "areaId: scope.areaId" in client
    assert "write-intents-not-enabled" in client
    assert "createTenantScopedStorageKey" in native_contracts
    assert "purgeOnLogout: true" in native_contracts
    assert "allowQueuedWrites: false" in native_contracts
    assert "sensitivePayloadsAllowed: false" in native_contracts


def test_khh_public_deploy_gate_requires_access_when_auth_mode_required() -> None:
    workflow = read(".github/workflows/tenant-ui-deploy.yml")

    assert 'default: required' in workflow
    assert 'if [ "${SCAS_UI_AUTH_MODE_TARGET}" = "required" ]; then' in workflow
    assert 'status="$(curl -sS -o /dev/null -w' in workflow
    assert "cloudflareaccess" + ".com" in workflow
    assert "/cdn-cgi/access/login/" in workflow
    assert "Leitungs-Cockpit" in workflow
