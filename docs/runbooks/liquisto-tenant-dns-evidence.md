# Liquisto Tenant DNS Evidence

Last checked: 2026-06-17 22:40 Europe/Berlin

This evidence records public DNS observations for the SCAS Liquisto tenant.
Public DNS is routing evidence only. It is not an authorization boundary and it
does not prove the hidden Cloudflare origin configuration.

## Expected Tenant Routing

- Tenant ID: `liquisto`
- Area ID: `liquisto`
- Hostname: `liquisto.condata.io`
- Expected origin IP in tenant fixture: `178.105.62.169`
- Cloudflare proxy expected: `true`
- Runtime authority: server-side hostname resolution plus authenticated tenant
  membership and sealed runtime profile validation

## Public DNS Observation

Commands:

```powershell
Resolve-DnsName liquisto.condata.io -Type A
Resolve-DnsName liquisto.condata.io -Type A -Server 1.1.1.1
Resolve-DnsName liquisto.condata.io -Type A -Server 8.8.8.8
Resolve-DnsName condata.io -Type NS
```

Observed A records for `liquisto.condata.io`:

| Resolver | TTL | A records |
| --- | ---: | --- |
| System resolver | 300 | `172.67.186.195`, `104.21.36.65` |
| `1.1.1.1` | 300 | `104.21.36.65`, `172.67.186.195` |
| `8.8.8.8` | 300 | `104.21.36.65`, `172.67.186.195` |

Observed NS records for `condata.io`:

| Resolver | TTL | NS records |
| --- | ---: | --- |
| System resolver | 42874 | `dayana.ns.cloudflare.com`, `coby.ns.cloudflare.com` |

HTTP route observation:

| URL | Status | Server | Content-Type | Interpretation |
| --- | ---: | --- | --- | --- |
| `https://liquisto.condata.io/` | 200 | `cloudflare` | `text/html` | Public route is reachable and serves the Streamlit login shell. Post-login UI state was not verified. |

## Interpretation

The public A records are Cloudflare proxy IPs and are consistent across the
checked resolvers. This is consistent with a Cloudflare-proxied hostname whose
internal origin may be `178.105.62.169`.

Public DNS does not expose or prove the hidden origin record. Treat the origin
mapping as unverified until checked through the Cloudflare dashboard or an
authorized Cloudflare API read.

## Routing Requirements

- Unknown hostnames must fail closed.
- Disabled tenants must fail closed.
- `liquisto.condata.io` must map to exactly one tenant authority.
- Prompt-supplied tenant IDs must not override hostname-derived authority.
- Tenant admin routes require tenant-admin bearer authorization and
  `x-scas-tenant-hostname`.
- Runtime profiles must seal the Control Plane tenant authority before any
  tenant-scoped execution starts.

## Authoritative Cloudflare Evidence

Manual `Tenant Cloudflare Evidence` workflow runs on 2026-06-17 collected the
authoritative Cloudflare evidence for `liquisto.condata.io` without printing
the hidden origin record value.

| Environment | GitHub run | Result | Proxied A records | TLS mode | Worker routes | Worker route required |
| --- | --- | --- | ---: | --- | ---: | --- |
| staging | `27716489830` | passed | 1 | `full` | 0 | `false` |
| prod | `27716489895` | passed | 1 | `full` | 0 | `false` |

Runs with `require_worker_route=true` failed for both staging and production
because no Cloudflare Worker route exists for the tenant hostname:

| Environment | GitHub run | Result | Failure |
| --- | --- | --- | --- |
| staging | `27716338428` | failed | `No Cloudflare Worker route found for tenant hostname.` |
| prod | `27716338387` | failed | `No Cloudflare Worker route found for tenant hostname.` |

Current accepted routing state: `liquisto.condata.io` is a Cloudflare-proxied
DNS route to the Hetzner/Nginx/Streamlit runtime path. It is not a Cloudflare
Worker route. The tenant Control API remains on Cloudflare Workers, but this UI
hostname does not require a Worker route unless the deployment architecture is
changed explicitly.

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
`SCAS_STAGING_CLOUDFLARE_EVIDENCE_TOKEN` or
`SCAS_PROD_CLOUDFLARE_EVIDENCE_TOKEN`, not a deploy token. The token needs
read-only `Zone DNS`, `Zone Settings`, and `Zone Workers Routes` access on the
`condata.io` zone.
