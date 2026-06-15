# Liquisto Tenant DNS Evidence

Last checked: 2026-06-15 12:33 Europe/Berlin

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
| `1.1.1.1` | 300 | `172.67.186.195`, `104.21.36.65` |
| `8.8.8.8` | 300 | `172.67.186.195`, `104.21.36.65` |

Observed NS records for `condata.io`:

| Resolver | TTL | NS records |
| --- | ---: | --- |
| System resolver | 21600 | `dayana.ns.cloudflare.com`, `coby.ns.cloudflare.com` |

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

## Follow-Up

- Confirm the internal Cloudflare DNS record for `liquisto.condata.io` through
  an authoritative Cloudflare source before marking production routing complete.
- Confirm TLS mode and Worker route binding for the tenant hostname before
  production release.
