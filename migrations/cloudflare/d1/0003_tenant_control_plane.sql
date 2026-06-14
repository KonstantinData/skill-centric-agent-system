PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    area_id TEXT NOT NULL CHECK (area_id <> ''),
    display_name TEXT NOT NULL CHECK (display_name <> ''),
    legal_name TEXT NOT NULL CHECK (legal_name <> ''),
    status TEXT NOT NULL CHECK (status IN ('setup', 'active', 'disabled', 'archived')),
    default_locale TEXT NOT NULL CHECK (default_locale <> ''),
    contact_email TEXT NOT NULL CHECK (contact_email <> ''),
    contact_phone TEXT CHECK (contact_phone IS NULL OR contact_phone <> ''),
    contact_website TEXT CHECK (contact_website IS NULL OR contact_website <> ''),
    memory_area_brain_id TEXT NOT NULL CHECK (memory_area_brain_id <> ''),
    shared_promotion_allowed INTEGER NOT NULL CHECK (shared_promotion_allowed = 0),
    knowledge_scope_id TEXT NOT NULL CHECK (knowledge_scope_id <> ''),
    policy_bundle_json TEXT NOT NULL CHECK (json_valid(policy_bundle_json)),
    validators_json TEXT NOT NULL CHECK (json_valid(validators_json)),
    created_at TEXT NOT NULL CHECK (created_at <> ''),
    updated_at TEXT NOT NULL CHECK (updated_at <> '')
);

CREATE INDEX IF NOT EXISTS idx_tenants_status
    ON tenants (status);

CREATE TABLE IF NOT EXISTS tenant_hostnames (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    tenant_id TEXT NOT NULL,
    hostname TEXT NOT NULL UNIQUE CHECK (hostname <> ''),
    purpose TEXT NOT NULL CHECK (purpose IN ('primary-ui', 'api', 'admin')),
    expected_origin TEXT CHECK (expected_origin IS NULL OR expected_origin <> ''),
    cloudflare_proxy_expected INTEGER NOT NULL CHECK (cloudflare_proxy_expected IN (0, 1)),
    FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_hostnames_tenant
    ON tenant_hostnames (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_data_sources (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    tenant_id TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (
        source_type IN (
            'github_repository',
            'notion_page_tree',
            'google_drive_folder',
            'sharepoint_site',
            'hubspot_account',
            'website',
            'database',
            'other'
        )
    ),
    display_name TEXT NOT NULL CHECK (display_name <> ''),
    access_modes_json TEXT NOT NULL CHECK (json_valid(access_modes_json)),
    status TEXT NOT NULL CHECK (status IN ('planned', 'active', 'disabled', 'archived')),
    sensitivity TEXT NOT NULL CHECK (
        sensitivity IN ('public', 'internal', 'confidential', 'restricted')
    ),
    FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_data_sources_tenant_status
    ON tenant_data_sources (tenant_id, status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_data_sources_tenant_id_unique
    ON tenant_data_sources (tenant_id, id);

CREATE TABLE IF NOT EXISTS tenant_role_bundles (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    tenant_id TEXT NOT NULL,
    display_name TEXT NOT NULL CHECK (display_name <> ''),
    role_type TEXT NOT NULL CHECK (role_type IN ('system', 'tenant-custom')),
    assignable_to_users INTEGER NOT NULL CHECK (assignable_to_users IN (0, 1)),
    derived_skills_json TEXT NOT NULL CHECK (json_valid(derived_skills_json)),
    derived_workflows_json TEXT NOT NULL CHECK (json_valid(derived_workflows_json)),
    derived_tools_json TEXT NOT NULL CHECK (json_valid(derived_tools_json)),
    derived_policies_json TEXT NOT NULL CHECK (json_valid(derived_policies_json)),
    derived_validators_json TEXT NOT NULL CHECK (json_valid(derived_validators_json)),
    FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_role_bundles_tenant
    ON tenant_role_bundles (tenant_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_role_bundles_tenant_id_unique
    ON tenant_role_bundles (tenant_id, id);

CREATE TABLE IF NOT EXISTS tenant_memberships (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    tenant_id TEXT NOT NULL,
    principal_id TEXT NOT NULL CHECK (principal_id <> ''),
    status TEXT NOT NULL CHECK (status IN ('invited', 'active', 'disabled')),
    role_ids_json TEXT NOT NULL CHECK (json_valid(role_ids_json)),
    created_at TEXT NOT NULL CHECK (created_at <> ''),
    updated_at TEXT NOT NULL CHECK (updated_at <> ''),
    FOREIGN KEY (tenant_id) REFERENCES tenants (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_memberships_tenant_principal
    ON tenant_memberships (tenant_id, principal_id);

CREATE TABLE IF NOT EXISTS tenant_role_capability_grants (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    tenant_id TEXT NOT NULL,
    role_bundle_id TEXT NOT NULL,
    capability_id TEXT NOT NULL CHECK (capability_id <> ''),
    FOREIGN KEY (tenant_id) REFERENCES tenants (id),
    FOREIGN KEY (role_bundle_id) REFERENCES tenant_role_bundles (id),
    FOREIGN KEY (tenant_id, role_bundle_id) REFERENCES tenant_role_bundles (tenant_id, id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_role_capability_unique
    ON tenant_role_capability_grants (tenant_id, role_bundle_id, capability_id);

CREATE TABLE IF NOT EXISTS tenant_role_data_source_grants (
    id TEXT PRIMARY KEY CHECK (id <> ''),
    tenant_id TEXT NOT NULL,
    role_bundle_id TEXT NOT NULL,
    data_source_id TEXT NOT NULL,
    access_modes_json TEXT NOT NULL CHECK (json_valid(access_modes_json)),
    FOREIGN KEY (tenant_id) REFERENCES tenants (id),
    FOREIGN KEY (role_bundle_id) REFERENCES tenant_role_bundles (id),
    FOREIGN KEY (data_source_id) REFERENCES tenant_data_sources (id),
    FOREIGN KEY (tenant_id, role_bundle_id) REFERENCES tenant_role_bundles (tenant_id, id),
    FOREIGN KEY (tenant_id, data_source_id) REFERENCES tenant_data_sources (tenant_id, id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_role_data_source_unique
    ON tenant_role_data_source_grants (tenant_id, role_bundle_id, data_source_id);
