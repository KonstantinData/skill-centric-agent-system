# Daskuechenhaus Control API

Tenant-specific Cloudflare Worker for the Daskuechenhaus customer case manager.

## Scope

- D1-backed customer cases, customers, notes, tasks, documents, communications, appointments, and audit events.
- The database is Daskuechenhaus-specific. `tenant_id` remains in v1 tables as
  a backward-compatible technical guard, but the fachliche boundary is the
  dedicated database plus `TENANT_ID = "daskuechenhaus"`.
- Write requests require `X-Actor`. Streamlit sends the logged-in principal ID.
- Skill suggestions are represented with `source = "skill_suggestion"` and `confirmed_by = NULL` until a user confirms them.
- `case_notes` are immutable by schema trigger.

## Fachliche Felder

- `customer_number`: Kunden-Nr.; identifies the customer record.
- `case_number`: Vorgangs-Nr.; identifies one customer case and separates
  multiple kitchen/project cases for the same customer.
- `carat_order_number`: CARAT-Auftrags-Nr.; identifies the actual CARAT order
  after Auftragserteilung and stays separate from `case_number`.
- `created_by_user_id`: user who created the case.
- `responsible_user_id`: currently responsible user; the UI will choose from
  users configured in the admin area.
- `customer_participants`: one or more private/company Beteiligte under the
  same Kunden-Nr.; this supports two names on a contract or invoice without
  creating a second Kunden-Nr.
- `tax_number`, `vat_id`, `iso_country_code`, and the tax/communication flags
  (`is_nato`, `has_custom_vat`, `reverse_charge`, `marketing_allowed`,
  `e_invoice`) are stored with the customer and first participant in v1.2. The
  business functions behind those flags are intentionally implemented later.

All user-facing labels in the Daskuechenhaus UI are German. The API and schema
keep English identifiers for repository consistency.

## Local Checks

```powershell
npm install
npm run typecheck
npm run test
npm run d1:local
```

## D1 Bootstrap

Create the production D1 database once:

```powershell
npx wrangler d1 create daskuechenhaus-cases
```

Copy the returned `database_id` into `wrangler.toml`, then apply the schema:

```powershell
npx wrangler d1 execute daskuechenhaus-cases --remote --file=schema_v1.sql
```

Do not deploy the Worker while `wrangler.toml` still contains
`REPLACE_WITH_YOUR_D1_DATABASE_ID`.

For an existing Sprint-1 database, apply the one-time v1.1 migration before
deploying code that reads the new columns:

```powershell
npx wrangler d1 execute daskuechenhaus-cases --remote --file=schema_v1_1.sql
```

`schema_v1_1.sql` is intentionally a migration script, not an idempotent seed
file. Run it once per database.

After v1.1, apply the one-time v1.2 migration before deploying code that writes
the new tax and checkbox fields:

```powershell
npx wrangler d1 execute daskuechenhaus-cases --remote --file=schema_v1_2.sql
```

`schema_v1_2.sql` is also non-idempotent and must run only once per database.

For local D1 validation:

```powershell
npx wrangler d1 execute daskuechenhaus-cases --local --file=schema_v1.sql
```

Use migration files locally only against a copy of a database that was created
before the corresponding columns existed.

## Secret

`API_SECRET` must be configured as a Worker secret. Never commit it.

```powershell
npx wrangler secret put API_SECRET
```

## Browser CORS

Browser CORS is fail-closed by default. If a browser-hosted UI calls this Worker
directly, set `CORS_ALLOWED_ORIGINS` to a comma-separated list of exact HTTPS
origins in `wrangler.toml` or the target environment. Do not use `*` with the
bearer-authenticated case endpoints.
