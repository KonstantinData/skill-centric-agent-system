# DKH iOS CRM

Native SwiftUI companion app for the DKH CRM tenant `daskuechenhaus`.

The existing browser CRM in `apps/dkh-crm/` remains the protected production
Web App for `es-daskuechenhaus.de` and `www.es-daskuechenhaus.de`. This app is
an additional iOS surface beside the browser version, not a replacement.

## Current Scope

- Native SwiftUI dashboard for DKH CRM operational overview.
- Read-only status and navigation surface for overview, appointments, tasks,
  e-mails, customers, cases, templates, purchase contracts, invoices, and
  admin boundary awareness.
- Static DKH CRM snapshot derived from `apps/dkh-crm/` and DKH repository
  documentation.
- Tenant identity fixed to `daskuechenhaus` and area `daskuechenhaus`.
- No customer master-data records, no full contact details, no documents, no
  runtime API transport, and no local offline customer-data storage.
- No write intents, push notifications, App Store release configuration, or
  Cloudflare Access/OIDC handoff yet.

## Tenant And App Boundaries

```text
tenant_id: daskuechenhaus
area_id: daskuechenhaus
web_app: apps/dkh-crm/
ios_app: apps/dkh-ios/
production_web_hosts: es-daskuechenhaus.de, www.es-daskuechenhaus.de
```

The iOS app may display DKH CRM workflow structure and sanitized status labels.
It must not embed live customer records, private contact data, raw API
responses, object-storage documents, secrets, Cloudflare Access tokens, or
Hetzner runtime credentials.

## Privacy And Read-Only Limits

- Snapshot data is role/status/process oriented and contains no real customer
  names, e-mail addresses, phone numbers, postal addresses, document contents,
  or personal free text.
- Customer and case references must remain generic, count-based, or internally
  scoped until authenticated API, secure storage, redaction, and audit gates are
  implemented.
- The current app is read-only. Mutations, uploads, mail sending, appointment
  writes, purchase contract writes, invoice writes, and admin changes are out of
  scope.
- Apple Developer credentials, provisioning profiles, Cloudflare Access
  secrets, and API tokens belong outside the repository.

## Open In Xcode

```powershell
open apps/dkh-ios/DKHCRM.xcodeproj
```

Then select the `DKHCRM` scheme and an iPhone simulator.

## Command-Line Validation

```powershell
xcodebuild -list -project apps/dkh-ios/DKHCRM.xcodeproj
xcodebuild -project apps/dkh-ios/DKHCRM.xcodeproj -scheme DKHCRM -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
python -m pytest tests/test_dkh_ios_app.py
```

## Not Part Of This App Yet

- Replacing or modifying the DKH browser CRM.
- Live Hetzner Admin API integration.
- Cloudflare Access/OIDC mobile sign-in.
- Secure local persistence or offline customer summaries.
- Push notifications, background sync, TestFlight, or App Store release.
- Real customer, lead, staff, document, or communication detail data.
