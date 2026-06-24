from __future__ import annotations

import importlib.util
import sys
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
API_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus_admin_api.py"
SERVICE_PATH = REPO_ROOT / "scripts" / "hetzner" / "daskuechenhaus-admin-api.service"
MIGRATION_PATH = (
    REPO_ROOT
    / "migrations"
    / "hetzner"
    / "tenants"
    / "daskuechenhaus"
    / "0001_admin_area.sql"
)


def test_daskuechenhaus_admin_api_runs_on_hetzner_runtime_plane_only() -> None:
    source = API_PATH.read_text(encoding="utf-8")
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "tenant_daskuechenhaus" in source
    assert "ThreadingHTTPServer((HOST, PORT), Handler)" in source
    assert '"127.0.0.1"' in source
    assert "psql" in source
    assert "ON_ERROR_STOP=1" in source
    assert "DKH_ADMIN_API_TOKEN_FILE" in source
    assert "x-dkh-admin-api-token" in source
    assert "x-access-user-email" in source
    assert "cloudflare_access" in source
    assert "User=tenant_daskuechenhaus_app" in service
    assert "DKH_ADMIN_API_HOST=127.0.0.1" in service
    assert "DKH_ADMIN_API_PORT=8715" in service
    assert "EnvironmentFile=-/etc/daskuechenhaus/object-storage.env" in service
    assert "DKH_OBJECT_STORAGE_BUCKET=dkh-crm-documents" in service
    assert "DKH_OBJECT_STORAGE_ENDPOINT=https://fsn1.your-objectstorage.com" in service


def test_daskuechenhaus_admin_api_exposes_required_admin_routes() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert 'parsed.path == "/admin/state"' in source
    assert 'parts == ["admin", "users"]' in source
    assert 'parts[:2] == ["admin", "users"]' in source
    assert 'parts[3] == "roles"' in source
    assert 'parts[3] == "workdays"' in source
    assert 'parts == ["admin", "company-settings"]' in source
    assert 'parts == ["admin", "integrations"]' in source


def test_daskuechenhaus_admin_api_exposes_required_overview_routes() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert 'parsed.path == "/overview/state"' in source
    assert 'parts == ["overview", "tasks"]' in source
    assert 'set_task_lifecycle(parts[2], "archive", access_email)' in source
    assert 'set_task_lifecycle(parts[2], "delete", access_email)' in source
    assert 'parts == ["overview", "emails", "assign"]' in source
    assert "decide_email_suggestion" in source
    assert 'parts[4] == "accept"' in source
    assert 'parts[4] in {"accept", "reject"}' not in source
    assert 'set_email_lifecycle(parts[2], "archive", access_email)' in source
    assert 'set_email_lifecycle(parts[2], "delete", access_email)' in source
    assert "current_user_context" in source
    assert "scope_user_ids" in source
    assert "user_delegations" in source
    assert source.count("ON CONFLICT (task_id, user_id) DO UPDATE") >= 2


def test_daskuechenhaus_admin_api_exposes_required_customer_routes() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert 'parsed.path == "/customers/state"' in source
    assert 'parsed.path == "/customers/search"' in source
    assert 'parts[3] == "export"' in source
    assert "customer_file_export" in source
    assert "write_binary" in source
    assert "application/zip" in source
    assert "simple_pdf" in source
    assert "CUSTOMER_EXPORT_SECTION_CODE" in source
    assert "CUSTOMER_EXPORT_CASE_FOLDERS" in source
    assert "CUSTOMER_EXPORT_DOCUMENT_CATEGORY_FOLDERS" in source
    assert "last_exported_at" in source
    assert "content-disposition" in source
    assert 'parts == ["customers", "customers"]' in source
    assert 'parts[:2] == ["customers", "customers"]' in source
    assert "customers_state" in source
    assert "assignable_users AS" in source
    assert "FROM assignable_users u" in source
    assert "if state is None:" in source
    assert '"customers": []' in source
    assert '"customer_cases": []' in source
    assert "search_customers" in source
    assert 'customer_filter: str = "all"' in source
    assert 'customer_filter in {"active", "closed", "all"}' in source
    assert 'params.get("status", ["all"])[0]' in source
    assert "WHEN :'phone_value' <> ''" in source
    assert "AND COALESCE(c.primary_phone_normalized, '') = :'phone_value'" in source
    assert "AND COALESCE(c.primary_mobile_normalized, '') = :'phone_value'" in source
    assert "app.customer_case_status_phases csp" in source
    assert "COALESCE(csp.is_terminal, FALSE) = TRUE" in source
    assert "LIMIT 20" in source
    assert "save_customer" in source
    assert "create_customer_case" in source
    assert 'parts == ["customers", "cases"]' in source
    assert "save_customer_section" in source
    assert "save_customer_case(" in source
    assert "save_customer_case_section" in source
    assert "save_customer_case_note" in source
    assert "create_customer_case_document_metadata" in source
    assert "parse_prjz_content" in source
    assert "store_carat_prjz_analysis" in source
    assert "select_carat_import_positions" in source
    assert 'parts[3] == "carat-imports"' in source
    assert "carat_action_invalid" in source
    assert "selection_status = 'transferred'" in source
    assert "selection_status IN ('selected', 'transferred')" in source
    assert "RETURNING import_id" in source
    assert "replace_latest_carat_project" in source
    assert 'data.get("carat_upload_mode", "")' in source
    assert "d.document_type = 'carat_project'" in source
    assert "d.is_current_version = TRUE" in source
    assert "replaced_carat_import AS" in source
    assert "canceled_replaced_supplier_orders AS" in source
    assert "so.source_carat_import_id IN" in source
    assert "JOIN app.customer_case_documents cd ON cd.id = ci.document_id" in source
    assert "AND cd.is_current_version = TRUE" in source
    assert "download_customer_case_document" in source
    assert "archive_customer_case_document" in source
    assert "app.customer_file_sections" in source
    assert "app.customer_case_sections" in source
    assert "app.customer_case_documents" in source
    assert 'parts[3] == "sections"' in source
    assert 'parts[3] == "notes"' in source
    assert 'parts[3] == "documents"' in source
    assert 'parts[5] == "download"' in source
    assert 'parts[5] == "archive"' in source
    assert "'documents', COALESCE((" in source
    assert "'register_code', d.register_code" in source
    assert "'document_category', d.document_category" in source
    assert '"from_customer"' in source
    assert '"planning"' in source
    assert '"order_processing"' in source
    assert '"delivery_installation"' in source
    assert '"complaint_service"' in source
    assert "DOCUMENT_CATEGORY_REGISTERS" in source
    assert '"invoice": "rechnung_abschluss"' in source
    assert "ALLOWED_DOCUMENT_FILE_TYPES" in source
    assert "object_storage_request(\"PUT\"" in source
    assert "object_storage_request(\"GET\"" in source
    assert "content_sha256" in source
    assert "storage_backend" in source
    assert "object_storage_key" in source
    assert "customer_case_carat_imports" in source
    assert "customer_case_carat_import_positions" in source
    assert "supplier_orders" in source
    assert "supplier_order_confirmations" in source
    assert "supplier_order_confirmation_exceptions" in source
    assert "supplier_communications" in source
    assert "supplier_follow_ups" in source
    assert "sync_supplier_orders_from_carat_selection" in source
    assert "is_carat_bilddaten_position" in source
    assert 'normalize_supplier_name(name) == "bilddaten"' in source
    assert "ignored_supplier_suffixes" in source
    assert "normalized_supplier_name" in source
    assert "<> 'bilddaten'" in source
    assert "COALESCE(cip.article_code, '') = '46000000000'" in source
    assert "create_supplier_order_confirmation" in source
    assert "recompute_supplier_confirmation_matching" in source
    assert "decide_supplier_confirmation_exception" in source
    assert "create_supplier_communication_draft" in source
    assert 'parts[3] == "confirmations"' in source
    assert 'parts[:2] == ["customers", "confirmations"]' in source
    assert "'carat_imports', COALESCE((" in source
    assert "'supplier_orders', COALESCE((" in source
    assert "'supplier_order_confirmations', COALESCE((" in source
    assert "'positions', COALESCE((" in source
    assert '".prjz": "application/zip"' in source
    assert '"document_type": (' in source
    assert '"carat_project"' in source
    assert 'document_category = "order_processing"' in source
    assert "'document_status', d.document_status" in source
    assert "customer_display_name" in source
    assert "app.customers" in source
    assert "app.customer_addresses" in source
    assert "app.customer_cases" in source
    assert "customer_name_required" in source
    assert "customer_not_found" in source
    assert "customer_duplicate_found" in source
    assert "customer_email_duplicate_found" in source
    assert "allow_duplicate_email" in source
    assert "match_scope: str = \"all\"" in source
    assert '{"matches": email_duplicate_matches}' in source
    assert "customer_duplicate_matches" in source
    assert '"object_customer_label":' in source
    assert '"tax_treatment": str(data.get("tax_treatment", "standard_de")).strip()' in source
    assert '"has_custom_vat": has_custom_vat' in source
    assert '"custom_vat_rate": custom_vat_rate' in source
    assert '"custom_vat_rate_label": str(data.get("custom_vat_rate_label", "")).strip()' in source
    assert "'has_custom_vat', c.has_custom_vat" in source
    assert "'custom_vat_rate', c.custom_vat_rate" in source
    assert "'custom_vat_rate_label', c.custom_vat_rate_label" in source
    assert "has_custom_vat = (data->>'has_custom_vat')::boolean" in source
    assert "custom_vat_rate = NULLIF(data->>'custom_vat_rate', '')::numeric" in source
    assert "custom_vat_rate_label = NULLIF(data->>'custom_vat_rate_label', '')" in source
    assert "app.customer_contacts" in source
    assert "contact_input AS" in source
    assert "inserted_contact AS" in source
    assert "normalize_phone_number" in source
    assert '"primary_email": str(data.get("primary_email", "")).strip().lower()' in source
    assert (
        '"primary_phone_normalized": normalize_phone_number(data.get("primary_phone", ""))'
        in source
    )
    assert (
        '"primary_mobile_normalized": normalize_phone_number(data.get("primary_mobile", ""))'
        in source
    )
    assert '"case_type": str(' in source
    assert '"kitchen_project_b2b"' in source
    assert "generate_customer_number(customer_type)" in source
    assert "generate_case_number() if create_case else" in source
    assert 'prefix = "OBJ-" if customer_type == "company" else "PRV-"' in source
    assert 'return generate_unique_number("V-", 8, "customer_cases", "case_number")' in source
    assert "CARAT_ORDER_NUMBER_PATTERN" in source
    assert "carat_order_number_invalid" in source
    assert "'customer_cases', COALESCE((" in source
    assert "'carat_order_number', cc.carat_order_number" in source
    assert "customer_number = NULLIF(data->>'customer_number', '')" not in source


def test_daskuechenhaus_admin_api_parses_carat_prjz_uploads() -> None:
    spec = importlib.util.spec_from_file_location("dkh_admin_api", API_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["dkh_admin_api"] = module
    spec.loader.exec_module(module)

    prj_lines = "\r\n".join(
        [
            "001| 000000000251200000000000000000000|V2026.2.1.2    |                2512|*",
            "001| 0020|Ben Ali                       |*",
            "001| 2150|EUR|*",
            (
                "002| 20000000000|Bilddaten                |"
                "Nicht zugeordnete Artikel|06/26          |18.06.26       |Z"
            ),
            (
                "002| 20006024011|NOBILIA K                |"
                "                         |17/26          |20.04.26       |K"
            ),
            "003| 9999.Artikel",
            (
                "003| 45000000000000|0000000002|00528482436|1|1|1|"
                "                    |0000000000|       0|00000000000|00000000000|"
                "00000000000|00000000000|00000000000|00000000000|00000000000|"
                "0000000000|0"
            ),
            "003| 4512         0|       300|      2500|*",
            (
                "003| 46000000000|00|Wand 1|                         |"
                "               |               |               |  |               |*"
            ),
            "003| 9999.Artikel",
            (
                "003| 45000000012011|0000000003|00528482436|1|1|1|"
                "                    |0000000000|       0|00000000000|00000000000|"
                "00000000000|00000000000|00000000000|00000000000|00000000000|"
                "0000000000|0"
            ),
            "003| 4512         0|       300|      2500|*",
            (
                "003| 46006024011|00|Unterschrank|                         |"
                "               |               |               |  |               |*"
            ),
            "003| 4627|20260617|KONSTANTIN|       2.00|0|*",
        ]
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("2512_05.PRJ", prj_lines.encode("cp1252"))

    result = module.parse_prjz_content(buffer.getvalue(), "2512_05.PRJZ")

    assert result["carat_version"] == "V2026.2.1.2"
    assert result["project_number"] == "2512"
    assert result["customer_name"] == "Ben Ali"
    assert result["currency"] == "EUR"
    assert [supplier["name"] for supplier in result["suppliers"]] == ["NOBILIA K"]
    assert len(result["positions"]) == 1
    assert result["positions"][0]["title"] == "Unterschrank"
    assert result["positions"][0]["quantity"] == 2.0
    assert result["positions"][0]["dimensions"]["width"] == 300.0
    assert result["positions"][0]["dimensions"]["depth"] == 2500.0


def test_daskuechenhaus_admin_api_parses_manual_confirmation_positions() -> None:
    spec = importlib.util.spec_from_file_location("dkh_admin_api", API_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["dkh_admin_api"] = module
    spec.loader.exec_module(module)

    rows = module.parse_confirmation_positions(
        "B123 | Unterschrank | 1 | 850,00 | KW 30 | 2026-07-22 | passt\n"
        "G456 | Gerät | 2 | 1200.50 | KW 31 |  | "
    )

    assert rows[0]["article_code"] == "B123"
    assert rows[0]["title"] == "Unterschrank"
    assert rows[0]["quantity"] == "1"
    assert rows[0]["confirmed_net_price"] == "850.00"
    assert rows[0]["confirmed_delivery_date"] == "2026-07-22"
    assert rows[1]["confirmed_net_price"] == "1200.50"
    assert rows[1]["confirmed_delivery_week"] == "KW 31"


def test_daskuechenhaus_admin_api_encodes_ab_cockpit_tolerance_policy() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert "matched_position_count == 0" in source
    assert '"context_revision_required"' in source
    assert "Liefertermin weicht mindestens eine Woche ab" in source
    assert "Netto-Preis weicht ab und muss bestätigt werden" in source
    assert "Bestellte Position fehlt in der AB" in source
    assert "AB-Position ist keiner bestellten Position zugeordnet" in source
    assert "supplier_order_confirmation_decisions" in source
    assert "waiting_for_supplier" in source
    assert "now() + interval '3 days'" in source


def test_daskuechenhaus_admin_api_keeps_cockpit_actions_human_confirmed() -> None:
    source = API_PATH.read_text(encoding="utf-8")

    assert "resolve_customer_case_id" in source
    assert "customer_case_search_ambiguous" in source
    assert "email_assignment_suggestions" in source
    assert "email_assignment_suggestion_accepted" in source
    assert "suggestion_decisions" in source
    assert "other_suggestions" in source
    assert "is_unassigned = FALSE" in source
    assert "em.archived_at IS NULL" in source
    assert "em.deleted_at IS NULL" in source
    assert "t.archived_at IS NULL" in source
    assert "t.deleted_at IS NULL" in source
    assert "communication_events" in source


def test_daskuechenhaus_admin_api_handles_task_uploads_on_hetzner() -> None:
    source = API_PATH.read_text(encoding="utf-8")
    service = SERVICE_PATH.read_text(encoding="utf-8")

    assert "multipart/form-data" in source
    assert "FileUpload" in source
    assert "ALLOWED_TASK_ATTACHMENT_TYPES" in source
    assert "save_task_attachment" in source
    assert "DKH_ADMIN_UPLOAD_ROOT=" in service
    assert "/var/lib/daskuechenhaus/uploads" in service
    assert "ReadWritePaths=/var/lib/daskuechenhaus/uploads" in service
    assert "object_storage_configured" in source
    assert "OBJECT_STORAGE_BUCKET" in source
    assert "OBJECT_STORAGE_ACCESS_KEY_ID" in source
    assert "AWS4-HMAC-SHA256" in source
    assert "x-amz-content-sha256" in source


def test_daskuechenhaus_admin_migration_seeds_initial_admin_and_company() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    assert "'k.milonas@schober-daskuechenhaus.de'" in migration
    assert "'Konstantin'" in migration
    assert "'Milonas'" in migration
    assert "INSERT INTO app.user_roles" in migration
    assert "INSERT INTO app.user_security_settings" in migration
    assert "INSERT INTO app.company_settings" in migration
