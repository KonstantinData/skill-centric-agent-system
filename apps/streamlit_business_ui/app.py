from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from random import Random
from typing import Any
from urllib import request as urlrequest

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANTS_DIR = REPO_ROOT / "examples" / "tenants"


@dataclass(frozen=True)
class MonthlyKpi:
    month: str
    revenue_million_eur: float
    gross_margin_pct: float
    operating_cost_million_eur: float
    nps: int
    churn_pct: float
    lead_volume: int
    win_rate_pct: float


@dataclass(frozen=True)
class TenantShell:
    tenant_id: str
    area_id: str
    display_name: str
    status: str
    hostname: str
    admin_routes: tuple[str, ...]
    role_names: tuple[str, ...]
    data_sources: tuple[str, ...]
    isolation_summary: str


@dataclass(frozen=True)
class TenantAdminSection:
    users: tuple[dict[str, Any], ...]
    roles: tuple[dict[str, Any], ...]
    settings: dict[str, Any]


@dataclass(frozen=True)
class TenantAdminApiConfig:
    base_url: str
    token: str
    timeout_seconds: float = 8.0


MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

REGION_FACTORS = {
    "DACH": 1.0,
    "Nordics": 0.72,
    "Benelux": 0.61,
    "UK & Ireland": 1.15,
}

SCENARIO_FACTORS = {
    "Base": 1.0,
    "Conservative": 0.92,
    "Growth": 1.12,
}


def load_tenant_registry(tenants_dir: Path = TENANTS_DIR) -> dict[str, dict[str, Any]]:
    tenants: dict[str, dict[str, Any]] = {}
    for path in sorted(tenants_dir.glob("*.json")):
        tenant = json.loads(path.read_text(encoding="utf-8"))
        tenants[str(tenant["tenant_id"])] = tenant
    return tenants


def build_tenant_shell(tenant: dict[str, Any]) -> TenantShell:
    hostnames = tenant.get("hostnames", [])
    primary_hostname = hostnames[0]["hostname"] if hostnames else "unknown"
    admin_model = tenant.get("admin_model", {})
    role_bundles = tenant.get("role_bundles", [])
    data_sources = tenant.get("data_sources", [])
    return TenantShell(
        tenant_id=str(tenant["tenant_id"]),
        area_id=str(tenant["area_id"]),
        display_name=str(tenant["display_name"]),
        status=str(tenant["status"]),
        hostname=str(primary_hostname),
        admin_routes=tuple(str(route) for route in admin_model.get("admin_routes", [])),
        role_names=tuple(str(role["display_name"]) for role in role_bundles),
        data_sources=tuple(str(source["display_name"]) for source in data_sources),
        isolation_summary=(
            "Server-seitige Hostname-Autorität, Rollen statt Direktrechten, "
            "keine Cross-Tenant- oder Cross-Area-Freigaben."
        ),
    )


def build_tenant_admin_section(tenant: dict[str, Any]) -> TenantAdminSection:
    admin_model = tenant.get("admin_model", {})
    role_bundles = tuple(
        {
            "role": str(role["display_name"]),
            "role_id": str(role["id"]),
            "type": str(role["role_type"]),
            "capabilities": ", ".join(str(item) for item in role.get("capability_grants", [])),
            "data_sources": ", ".join(
                str(grant["data_source_id"]) for grant in role.get("data_source_grants", [])
            ),
        }
        for role in tenant.get("role_bundles", [])
    )
    initial_owner = admin_model.get("initial_owner")
    users = (
        {
            "user": "Initial owner pending",
            "status": "pending",
            "roles": "Tenant Owner",
        },
    )
    if initial_owner is not None:
        users = (
            {
                "user": str(initial_owner["email"]),
                "status": "planned",
                "roles": "Tenant Owner",
            },
        )
    return TenantAdminSection(
        users=users,
        roles=role_bundles,
        settings={
            "assignment_model": str(admin_model.get("assignment_model", "")),
            "admin_routes": ", ".join(str(route) for route in admin_model.get("admin_routes", [])),
            "shared_promotion_allowed": str(
                tenant.get("memory", {}).get("shared_promotion_allowed", False)
            ),
            "policy_bundle": ", ".join(str(policy) for policy in tenant.get("policy_bundle", [])),
        },
    )


def tenant_admin_api_config_from_env() -> TenantAdminApiConfig | None:
    base_url = os.environ.get("SCAS_CONTROL_API_URL", "").strip()
    token = os.environ.get("SCAS_TENANT_ADMIN_TOKEN", "").strip()
    if not base_url or not token:
        return None
    return TenantAdminApiConfig(base_url=base_url.rstrip("/"), token=token)


def load_tenant_admin_context_from_api(
    config: TenantAdminApiConfig,
    tenant_id: str,
    hostname: str,
) -> dict[str, Any]:
    api_request = urlrequest.Request(
        f"{config.base_url}/tenant-admin/tenants/{tenant_id}",
        headers={
            "authorization": f"Bearer {config.token}",
            "x-scas-tenant-hostname": hostname,
            "accept": "application/json",
        },
        method="GET",
    )
    with urlrequest.urlopen(api_request, timeout=config.timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def build_tenant_shell_from_admin_context(context: dict[str, Any]) -> TenantShell:
    tenant = context["tenant"]
    admin = context["admin"]
    return TenantShell(
        tenant_id=str(tenant["tenant_id"]),
        area_id=str(tenant["area_id"]),
        display_name=str(tenant["display_name"]),
        status=str(tenant["status"]),
        hostname=str(tenant["hostname"]["hostname"]),
        admin_routes=tuple(str(route) for route in admin.get("admin_routes", [])),
        role_names=tuple(str(role["display_name"]) for role in context.get("roles", [])),
        data_sources=tuple(
            str(source["display_name"]) for source in context.get("data_sources", [])
        ),
        isolation_summary=(
            "Backend-geprüfte Hostname-Autorität, Rollen statt Direktrechten, "
            "keine Cross-Tenant- oder Cross-Area-Freigaben."
        ),
    )


def build_tenant_admin_section_from_context(context: dict[str, Any]) -> TenantAdminSection:
    users = tuple(
        {
            "user": str(user["principal_id"]),
            "membership_id": str(user["membership_id"]),
            "status": str(user["status"]),
            "roles": ", ".join(str(role_id) for role_id in user.get("role_ids", [])),
        }
        for user in context.get("users", [])
    )
    roles = tuple(
        {
            "role": str(role["display_name"]),
            "role_id": str(role["id"]),
            "type": str(role["role_type"]),
            "capabilities": ", ".join(str(item) for item in role.get("capability_grants", [])),
            "data_sources": ", ".join(
                str(grant["data_source_id"]) for grant in role.get("data_source_grants", [])
            ),
        }
        for role in context.get("roles", [])
    )
    return TenantAdminSection(
        users=users,
        roles=roles,
        settings=dict(context.get("settings", {})),
    )


def generate_kpis(year: int, region_scale: float, scenario_factor: float) -> list[MonthlyKpi]:
    rng = Random(year * 97)
    base_revenue = 6.4 * region_scale * scenario_factor
    base_cost = 2.5 * region_scale
    records: list[MonthlyKpi] = []
    for index, month in enumerate(MONTHS):
        seasonality = 0.92 + (index / 30)
        revenue = base_revenue * seasonality + rng.uniform(-0.18, 0.18)
        gross_margin = max(45.0, min(67.0, 53 + index * 0.55 + rng.uniform(-1.2, 1.2)))
        operating_cost = base_cost * (0.97 + index / 80) + rng.uniform(-0.07, 0.07)
        nps = int(max(24, min(71, 44 + index + rng.randint(-2, 3))))
        churn = max(1.6, min(6.2, 4.9 - index * 0.18 + rng.uniform(-0.22, 0.22)))
        leads = int((1220 + index * 54) * region_scale * scenario_factor + rng.randint(-35, 35))
        win_rate = max(16.0, min(43.0, 23 + index * 0.75 + rng.uniform(-0.8, 0.8)))
        records.append(
            MonthlyKpi(
                month=month,
                revenue_million_eur=round(revenue, 2),
                gross_margin_pct=round(gross_margin, 1),
                operating_cost_million_eur=round(operating_cost, 2),
                nps=nps,
                churn_pct=round(churn, 2),
                lead_volume=leads,
                win_rate_pct=round(win_rate, 2),
            )
        )
    return records


def build_card(title: str, value: str, delta: str) -> str:
    return (
        "<div class='metric-card'>"
        f"<div class='metric-title'>{title}</div>"
        f"<div class='metric-value'>{value}</div>"
        f"<div class='metric-delta'>{delta}</div>"
        "</div>"
    )


def main() -> None:
    import streamlit as st

    st.set_page_config(
        page_title="SCAS Executive Dashboard",
        page_icon=":material/monitoring:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');
        .stApp {
            background: radial-gradient(
                1200px 500px at 10% -5%,
                #dcecff 0%,
                #f7f9fc 40%,
                #f4f7fb 100%
            );
        }
        h1, h2, h3, h4 { font-family: "Manrope", sans-serif; letter-spacing: -0.02em; }
        p, div, span, label { font-family: "Manrope", sans-serif; }
        [data-testid="stSidebar"] { background: linear-gradient(180deg, #10223f 0%, #1c365e 100%); }
        [data-testid="stSidebar"] * { color: #eef4ff !important; }
        .metric-card {
            border-radius: 14px;
            background: #ffffff;
            border: 1px solid #dbe4f0;
            padding: 14px 16px;
            box-shadow: 0 8px 22px rgba(28, 54, 94, 0.08);
        }
        .metric-title { color: #4d617f; font-size: 0.86rem; font-weight: 700; }
        .metric-value { color: #0b1b35; font-size: 1.55rem; font-weight: 800; margin-top: 4px; }
        .metric-delta { color: #21764e; font-size: 0.82rem; font-weight: 700; margin-top: 4px; }
        .hero-card {
            border-radius: 18px;
            background: linear-gradient(110deg, #0f2f52 0%, #15477a 60%, #266199 100%);
            color: #f5f9ff;
            padding: 18px 22px;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }
        .hero-kicker {
            font-size: 0.82rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            opacity: 0.82;
        }
        .hero-title { font-size: 1.7rem; font-weight: 800; margin: 4px 0 2px 0; }
        .hero-copy { font-size: 0.96rem; opacity: 0.9; max-width: 820px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    tenants = load_tenant_registry()

    st.sidebar.title("Steuerung")
    tenant_id = st.sidebar.selectbox(
        "Tenant",
        options=sorted(tenants),
        index=sorted(tenants).index("liquisto") if "liquisto" in tenants else 0,
    )
    selected_year = st.sidebar.selectbox("Geschäftsjahr", [2026, 2025, 2024], index=0)
    selected_regions = st.sidebar.multiselect(
        "Regionen",
        options=list(REGION_FACTORS.keys()),
        default=["DACH", "UK & Ireland"],
    )
    scenario = st.sidebar.radio("Szenario", options=list(SCENARIO_FACTORS.keys()), index=0)
    risk_tolerance = st.sidebar.slider("Risiko-Toleranz", 0, 100, 55, 5)

    region_scale = sum(REGION_FACTORS[region] for region in selected_regions) / max(
        len(selected_regions),
        1,
    )
    kpis = generate_kpis(selected_year, region_scale, SCENARIO_FACTORS[scenario])
    last = kpis[-1]
    first = kpis[0]
    months = [row.month for row in kpis]
    tenant_shell = build_tenant_shell(tenants[tenant_id])
    tenant_admin = build_tenant_admin_section(tenants[tenant_id])
    api_config = tenant_admin_api_config_from_env()
    if api_config is not None:
        try:
            admin_context = load_tenant_admin_context_from_api(
                api_config,
                tenant_shell.tenant_id,
                tenant_shell.hostname,
            )
            tenant_shell = build_tenant_shell_from_admin_context(admin_context)
            tenant_admin = build_tenant_admin_section_from_context(admin_context)
        except Exception as error:  # pragma: no cover - defensive Streamlit runtime fallback.
            st.warning(f"Tenant Admin API nicht erreichbar: {error}")

    st.title(tenant_shell.display_name)
    shell_cols = st.columns([1.1, 1.1, 1.1, 1.6])
    shell_cols[0].metric("Tenant", tenant_shell.tenant_id)
    shell_cols[1].metric("Status", tenant_shell.status)
    shell_cols[2].caption("Hostname")
    shell_cols[2].write(tenant_shell.hostname)
    shell_cols[3].info(tenant_shell.isolation_summary)

    admin_cols = st.columns(3)
    admin_cols[0].subheader("Admin")
    admin_cols[0].write(", ".join(tenant_shell.admin_routes))
    admin_cols[1].subheader("Rollen")
    admin_cols[1].write(", ".join(tenant_shell.role_names))
    admin_cols[2].subheader("Datenquellen")
    admin_cols[2].write(", ".join(tenant_shell.data_sources) or "Keine")

    users_tab, roles_tab, settings_tab = st.tabs(
        ["Admin Benutzer", "Admin Rollen", "Admin Einstellungen"]
    )
    with users_tab:
        st.table(list(tenant_admin.users))
    with roles_tab:
        st.table(list(tenant_admin.roles))
    with settings_tab:
        st.json(tenant_admin.settings)

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-kicker">SCAS Business Intelligence</div>
            <div class="hero-title">Executive Command Center</div>
            <div class="hero-copy">
                Stand: {date.today().strftime("%d.%m.%Y")} | Szenario: {scenario} |
                Fokusregionen:
                {", ".join(selected_regions) if selected_regions else "Keine Auswahl"}.
                Diese Ansicht verbindet Umsatz-, Operations- und Risiko-Indikatoren
                für schnelle Führungsentscheidungen.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(
        build_card(
            "Umsatz YTD",
            f"{sum(row.revenue_million_eur for row in kpis):.1f} Mio. EUR",
            f"{((last.revenue_million_eur / first.revenue_million_eur) - 1) * 100:+.1f}% vs Jan",
        ),
        unsafe_allow_html=True,
    )
    c2.markdown(
        build_card(
            "Rohertragsmarge",
            f"{last.gross_margin_pct:.1f}%",
            f"{last.gross_margin_pct - first.gross_margin_pct:+.1f} pp YTD",
        ),
        unsafe_allow_html=True,
    )
    c3.markdown(
        build_card(
            "Pipeline Leads",
            f"{last.lead_volume:,}".replace(",", "."),
            f"{last.win_rate_pct:.1f}% Win Rate",
        ),
        unsafe_allow_html=True,
    )
    c4.markdown(
        build_card(
            "Churn",
            f"{last.churn_pct:.2f}%",
            f"{first.churn_pct - last.churn_pct:+.2f} pp Improvement",
        ),
        unsafe_allow_html=True,
    )

    overview, growth, operations, risk = st.tabs(
        ["Management Overview", "Growth Engine", "Operations", "Risk & Compliance"]
    )

    with overview:
        left, right = st.columns([1.4, 1])
        left.subheader("Umsatzentwicklung (Mio. EUR)")
        overview_cost_revenue = {
            "Month": months,
            "Umsatz": [row.revenue_million_eur for row in kpis],
            "Kosten": [row.operating_cost_million_eur for row in kpis],
        }
        left.line_chart(
            overview_cost_revenue,
            x="Month",
            y_label="Mio. EUR",
            color=["#1d4d81", "#c77131"],
        )
        right.subheader("Profitabilität")
        overview_margin = {
            "Month": months,
            "Marge %": [row.gross_margin_pct for row in kpis],
        }
        right.area_chart(
            overview_margin,
            x="Month",
            y_label="%",
            color=["#2f7d4f"],
        )

    with growth:
        l_col, r_col = st.columns([1, 1])
        l_col.subheader("Demand Funnel")
        growth_funnel = {
            "Month": months,
            "Leads": [row.lead_volume for row in kpis],
            "Deals (approx.)": [int(row.lead_volume * row.win_rate_pct / 100) for row in kpis],
        }
        l_col.bar_chart(
            growth_funnel,
            x="Month",
            y_label="Volumen",
            color=["#2c5c94", "#399874"],
        )
        r_col.subheader("Customer Experience")
        growth_experience = {
            "Month": months,
            "NPS": [row.nps for row in kpis],
            "Churn %": [row.churn_pct * 10 for row in kpis],
        }
        r_col.line_chart(
            growth_experience,
            x="Month",
            y_label="Index",
            color=["#164170", "#c14f36"],
        )
        st.caption("Hinweis: `Churn %` ist für gemeinsame Skalierung im Chart x10 dargestellt.")

    with operations:
        st.subheader("Operative Steuerung")
        op_col1, op_col2, op_col3 = st.columns(3)
        op_col1.metric("Kosten letzter Monat", f"{last.operating_cost_million_eur:.2f} Mio. EUR")
        op_col2.metric(
            "Effizienzquote",
            f"{(last.revenue_million_eur / last.operating_cost_million_eur):.2f}x",
        )
        op_col3.metric("Delivery-Risikoindex", f"{max(8, 100 - risk_tolerance):.0f}/100")
        st.progress(min(100, int(last.win_rate_pct * 2.2)), text="Go-to-Market Readiness")
        st.progress(min(100, int(last.gross_margin_pct * 1.4)), text="Margin Resilience")

    with risk:
        st.subheader("Risikobewertung")
        risk_score = max(10, min(92, 80 - risk_tolerance + int(last.churn_pct * 3)))
        control_score = max(8, min(95, risk_tolerance + int(last.gross_margin_pct / 2)))
        risk_col1, risk_col2 = st.columns(2)
        risk_col1.metric("Risk Exposure", f"{risk_score}/100", delta="-5 vs Vorquartal")
        risk_col2.metric("Control Strength", f"{control_score}/100", delta="+7 vs Vorquartal")
        st.warning(
            "Empfehlung: Fokus auf Kundenbindung in Regionen mit hoher Wachstumsdynamik,"
            " wenn Risiko-Toleranz unter 60 gesetzt ist."
            if risk_tolerance < 60
            else (
                "Empfehlung: Kontrollniveau stabil; nächster Hebel liegt in der "
                "Skalierung des Demand Funnels."
            )
        )


if __name__ == "__main__":
    main()
