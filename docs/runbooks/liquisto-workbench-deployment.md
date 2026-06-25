# Liquisto Workbench Deployment

The Liquisto Workbench is deployed through the existing guarded
`Tenant UI Deploy` GitHub Actions workflow.

Use the `liquisto-workbench` UI app option for the Next.js workbench:

```powershell
gh workflow run tenant-ui-deploy.yml `
  --repo KonstantinData/skill-centric-agent-system `
  --ref codex/liquisto-cloud-cutover `
  -f target_environment=prod `
  -f tenant_id=liquisto `
  -f hostname=liquisto.cloud `
  -f control_api_url=https://scas-control-api-prod.still-butterfly-bbff.workers.dev `
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
  -f reverse_proxy_cert_hostname=liquisto.cloud
```

The workflow builds `deploy/liquisto-workbench/Dockerfile`, starts the
standalone Next.js server on container port `3000`, binds it to
`127.0.0.1:3027` on the target host, and optionally manages the Nginx server
block for `liquisto.cloud`.

Do not use the legacy Streamlit deployment mode for Liquisto Workbench.
