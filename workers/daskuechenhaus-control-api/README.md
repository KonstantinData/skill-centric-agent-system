# Daskuechenhaus Control API

Tenant-specific Cloudflare Worker for the Daskuechenhaus customer case manager.

## Scope

- D1-backed customer cases, customers, notes, tasks, documents, communications, appointments, and audit events.
- Tenant scoping is server-side through `TENANT_ID = "daskuechenhaus"`.
- Write requests require `X-Actor`. The Streamlit MVP may send `X-Actor: konstantin` until real UI auth is wired.
- Skill suggestions are represented with `source = "skill_suggestion"` and `confirmed_by = NULL` until a user confirms them.
- `case_notes` are immutable by schema trigger.

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

For local D1 validation:

```powershell
npx wrangler d1 execute daskuechenhaus-cases --local --file=schema_v1.sql
```

## Secret

`API_SECRET` must be configured as a Worker secret. Never commit it.

```powershell
npx wrangler secret put API_SECRET
```
