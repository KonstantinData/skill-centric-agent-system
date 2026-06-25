# Liquisto Tenant DNS Evidence

Last checked: 2026-06-25 21:56 Europe/Berlin

This evidence records public DNS observations for the SCAS Liquisto tenant.
Public DNS is routing evidence only. It is not an authorization boundary and it
does not prove the hidden Cloudflare origin configuration.

## Expected Tenant Routing

- Tenant ID: `liquisto`
- Area ID: `liquisto`
- Hostname: `liquisto.cloud`
- Expected origin IP in tenant fixture: `145.239.222.45`
- Cloudflare proxy expected: `true`
- Runtime authority: server-side hostname resolution plus authenticated tenant
  membership and sealed runtime profile validation

## Public DNS Observation

Commands:

```powershell
Resolve-DnsName liquisto.cloud -Type A
Resolve-DnsName liquisto.cloud -Type A -Server 1.1.1.1
Resolve-DnsName liquisto.cloud -Type A -Server 8.8.8.8
Resolve-DnsName liquisto.cloud -Type NS
```

Observed A records for `liquisto.cloud`:

| Resolver | TTL | A records |
| --- | ---: | --- |
| `1.1.1.1` | 300 | `172.67.207.208`, `104.21.45.21` |

Observed NS records for `liquisto.cloud`:

| Resolver | TTL | NS records |
| --- | ---: | --- |
| System resolver | pending | pending |

HTTP route observation:

| URL | Status | Server | Content-Type | Interpretation |
| --- | ---: | --- | --- | --- |
| `https://liquisto.cloud/` | 200 | `cloudflare` | `text/html` | Public route is reachable through the Cloudflare proxy. |
| `https://www.liquisto.cloud/` | 200 | `cloudflare` | `text/html` | `www` route is reachable through the Cloudflare proxy. |

## Interpretation

The public A records must be Cloudflare proxy IPs and must be consistent across
the checked resolvers. This is consistent with a Cloudflare-proxied hostname
whose internal origin is hidden.

Public DNS does not expose or prove the hidden origin record. Treat the origin
mapping as unverified until checked through the Cloudflare dashboard or an
authorized Cloudflare API read.

## Routing Requirements

- Unknown hostnames must fail closed.
- Disabled tenants must fail closed.
- `liquisto.cloud` must map to exactly one tenant authority.
- Prompt-supplied tenant IDs must not override hostname-derived authority.
- Tenant admin routes require tenant-admin bearer authorization and
  `x-scas-tenant-hostname`.
- Runtime profiles must seal the Control Plane tenant authority before any
  tenant-scoped execution starts.

## Authoritative Cloudflare Evidence

Apply or plan the Cloudflare DNS cutover with:

```bash
gh workflow run tenant-cloudflare-dns-cutover.yml \
  --ref codex/liquisto-cloud-cutover \
  -f hostname=liquisto.cloud \
  -f origin_ipv4=145.239.222.45 \
  -f apply_changes=true \
  -f confirm_hostname=liquisto.cloud
```

The workflow must create or update:

- proxied apex `A` record for `liquisto.cloud`,
- proxied `www.liquisto.cloud` CNAME to `liquisto.cloud`.

The manual `Tenant Cloudflare Evidence` workflow must collect authoritative
Cloudflare evidence for `liquisto.cloud` without printing the hidden origin
record value.

| Environment | GitHub run | Result | Proxied A records | TLS mode | Worker routes | Worker route required |
| --- | --- | --- | ---: | --- | ---: | --- |
| liquisto | `28196655630` | passed | 1 | `full` | 0 | `false` |

The same run applied the DNS cutover before verification:

- Apex A record: `created`.
- WWW CNAME record: `created`.
- Origin record content: not printed in the evidence artifact.

Current target routing state: `liquisto.cloud` is a Cloudflare-proxied DNS route
to the approved origin for the Liquisto UI. It is not a Cloudflare Worker route
unless the deployment architecture is changed explicitly. The tenant Control API
remains on Cloudflare Workers, but this UI hostname does not require a Worker
route for the current architecture.

## Follow-Up

- Keep the authoritative Cloudflare evidence workflow artifact URLs linked from
  the launch gate and Notion launch records.
- Re-run `Tenant Cloudflare Evidence` after any DNS, TLS, proxy, or routing
  change.
- If the UI hostname is moved behind a Cloudflare Worker route in the future,
  run the evidence workflow with `require_worker_route=true` and update this
  runbook and the release gate before treating the Worker route as required.

The manual `Tenant Cloudflare Evidence` workflow
(`.github/workflows/tenant-cloudflare-evidence.yml`) records authoritative
Cloudflare DNS proxy, TLS mode, and optional Worker route evidence without
printing the hidden origin record content. It must use
`LIQUISTO_CLOUDFLARE_API_TOKEN` and `LIQUISTO_CLOUDFLARE_ZONE_ID`. The token
must be scoped to the `liquisto.cloud` zone and the owning Cloudflare account.
