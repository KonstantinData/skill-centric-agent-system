# Liquisto Workbench Deployment

The Liquisto Workbench is deployed through the existing guarded
`Tenant UI Deploy` GitHub Actions workflow.

Public access to the Workbench must be protected by Cloudflare Access. The
Access configuration is managed by `.github/workflows/liquisto-cloudflare-access.yml`
and must allow only `konstantin@liquisto.com` and `aernout@liquisto.com` through
Cloudflare Access One-Time PIN email verification.

Use the `liquisto-workbench` UI app option for the Next.js workbench:

```powershell
gh workflow run tenant-ui-deploy.yml `
  --repo KonstantinData/skill-centric-agent-system `
  --ref codex/liquisto-cloud-cutover `
  -f target_environment=prod `
  -f tenant_id=liquisto `
  -f hostname=liquisto.cloud `
  -f control_api_url=https://scas-control-api-prod.still-butterfly-bbff.workers.dev `
  -f upstream_auth_evidence_url=https://github.com/KonstantinData/skill-centric-agent-system/tree/codex/liquisto-cloud-cutover/apps/liquisto-workbench `
  -f ui_app=liquisto-workbench `
  -f auth_mode=required `
  -f apply_deploy=true `
  -f confirm_production=true `
  -f compose_project=liquisto `
  -f remote_override_path=/opt/liquisto/scas-liquisto-workbench.override.yml `
  -f service_name=app `
  -f local_health_port=3027 `
  -f manage_reverse_proxy=true `
  -f reverse_proxy_config_path=/etc/nginx/sites-available/liquisto `
  -f reverse_proxy_cert_hostname=liquisto.cloud `
  -f sync_cloudflare_dns=true
```

The workflow builds `deploy/liquisto-workbench/Dockerfile`, starts the
standalone Next.js server on container port `3000`, binds it to
`127.0.0.1:3027` on the target host, and optionally manages the Nginx server
block for `liquisto.cloud` and `www.liquisto.cloud`.

When `sync_cloudflare_dns=true`, the workflow updates the `liquisto.cloud`
Cloudflare apex and `www` records to the resolved deployment host without
printing the hidden origin IP in logs or evidence. The deploy is considered
successful only after the container, the Nginx origin routes for both apex and
`www`, and the public Cloudflare routes serve the Workbench content marker
`Liquisto workspace`.

After each production UI deploy, run or verify the Liquisto Cloudflare Access
workflow in apply mode so unauthenticated public requests redirect to
Cloudflare Access instead of serving Workbench HTML directly:

```powershell
gh workflow run liquisto-cloudflare-access.yml `
  --repo KonstantinData/skill-centric-agent-system `
  --ref main `
  -f apply_changes=true `
  -f confirm_production=true `
  -f hostnames="liquisto.cloud www.liquisto.cloud" `
  -f allowed_emails="konstantin@liquisto.com aernout@liquisto.com" `
  -f primary_hostname=liquisto.cloud `
  -f confirm_hostname=liquisto.cloud
```

Latest production apply evidence:

| Date | GitHub run | Result | Evidence |
| --- | --- | --- | --- |
| 2026-06-27 11:30 Europe/Berlin | `28285197010` | passed | Image `scas-liquisto-workbench:31f42d848c057fb7054b27529764ef94e7bda843`; Nginx managed at `/etc/nginx/sites-available/liquisto -> 127.0.0.1:3027` with server names `liquisto.cloud www.liquisto.cloud`; Cloudflare DNS synced to the deployment host; public content marker `Liquisto workspace` verified for apex and `www`; verified public HTML serves `Liquisto Workbench` and no `Liquisto Tenant Workbench` marker. |
| 2026-06-26 21:56 Europe/Berlin | `28261745148` | passed | Image `scas-liquisto-workbench:e0b2625673153e187d1668e5a0e71968fe375b34`; Nginx managed at `/etc/nginx/sites-available/liquisto -> 127.0.0.1:3027` with server names `liquisto.cloud www.liquisto.cloud`; Cloudflare DNS synced to the deployment host; public content marker `Liquisto workspace` verified for apex and `www`; checked that Cockpit serves no `Command Center`, `Search research tasks`, `Runtime Evidence`, `Evidence Timeline`, `Control Boundary`, or `Runtime Configuration` markers. |
| 2026-06-26 21:33 Europe/Berlin | `28260625014` | passed | Image `scas-liquisto-workbench:11077d14892640ca3a07886ee837e2aef40ce211`; Nginx managed at `/etc/nginx/sites-available/liquisto -> 127.0.0.1:3027` with server names `liquisto.cloud www.liquisto.cloud`; Cloudflare DNS synced to the deployment host; public content marker `Command Center` verified for apex and `www`; checked that Cockpit serves `Liquisto workspace` and no `Runtime Evidence`, `Evidence Timeline`, `Control Boundary`, `Runtime Configuration`, or `isolation evidence` markers. |
| 2026-06-26 21:16 Europe/Berlin | `28259785528` | passed | Image `scas-liquisto-workbench:ce8664c0c296655f8ab4ffa607d689532e94613b`; Nginx managed at `/etc/nginx/sites-available/liquisto -> 127.0.0.1:3027` with server names `liquisto.cloud www.liquisto.cloud`; Cloudflare DNS synced to the deployment host; public content marker `Command Center` verified for apex and `www`; checked that old Inventory/Monetization/Partner markers are absent. |
| 2026-06-26 07:19 Europe/Berlin | `28218809860` | passed | Image `scas-liquisto-workbench:6ceb8e91385f95e35496c0e149767ea770a4ff91`; Nginx managed at `/etc/nginx/sites-available/liquisto -> 127.0.0.1:3027` with server names `liquisto.cloud www.liquisto.cloud`; Cloudflare DNS synced to the deployment host; public content marker `Command Center` verified for apex and `www`. |
| 2026-06-25 22:56 Europe/Berlin | `28199866868` | passed | Image `scas-liquisto-workbench:f2572484724b3886c4cd3de08cc3945464e9348b`; Nginx managed at `/etc/nginx/sites-available/liquisto -> 127.0.0.1:3027`; Cloudflare DNS synced to the deployment host; public content marker `Command Center` verified. |

Do not add a second tenant UI deployment mode for Liquisto Workbench.
