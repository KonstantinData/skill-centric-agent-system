# DKH iOS CRM

Native iOS app for the productive DKH CRM tenant `daskuechenhaus`.

The browser CRM in `apps/dkh-crm/` remains available at
`https://es-daskuechenhaus.de` and `https://www.es-daskuechenhaus.de` behind
Cloudflare Access. Cloudflare Access remains unchanged for the browser hosts.
The iOS app does not start either website. It uses native SwiftUI screens and
one-time Apple device authorization against the dedicated mobile API at
`https://app.es-daskuechenhaus.de/api/mobile`.

## Current Scope

- Native SwiftUI app shell for overview, customers, appointments, tasks,
  e-mails, cases, purchase contract, invoice, and admin.
- No standalone app login area: after first device approval, unlocking the
  iPhone is enough for normal app entry.
- One-time iPhone device approval through Apple's native authorization sheet.
- Apple `identityToken` exchange through the DKH mobile API.
- Server-side Apple subject mapping to a DKH CRM user.
- The server-side Apple subject mapping is the durable access check after the
  first approved device authorization.
- Keychain storage for the short-lived DKH mobile session token.
- Keychain storage for the trusted-device user snapshot so the app opens
  directly after the iPhone is unlocked.
- No `SFSafariViewController`, no `WKWebView`, and no browser website startup.
- No Cloudflare Access verification in the iOS app path. Cloudflare Access
  remains unchanged for the browser hosts.
- No embedded Apple tokens, Cloudflare Access service tokens, customer records,
  raw API responses, documents, or Hetzner credentials.

## Tenant And App Boundaries

```text
tenant_id: daskuechenhaus
area_id: daskuechenhaus
web_app: apps/dkh-crm/
ios_app: apps/dkh-ios/
browser_hosts: es-daskuechenhaus.de, www.es-daskuechenhaus.de
mobile_api_host: app.es-daskuechenhaus.de
bundle_id: de.daskuechenhaus.crm
```

The iOS app may only talk to the DKH mobile API host. Browser URLs are not app
entrypoints. The server verifies the Apple identity token during the one-time
device approval and then resolves the stable Apple user subject to an active
DKH CRM user before returning a mobile session.

## Privacy And Runtime Limits

- The repository contains no CRM data export and no demo customer database.
- Customer data, document access, write actions, mail handling, purchase
  contracts, invoices, and admin functions stay behind the existing DKH server
  controls.
- The app does not store long-lived secrets in app code or repository files.
- Apple Developer credentials, provisioning profiles, session secrets, and API
  tokens belong outside the repository.

## Open In Xcode

```powershell
open apps/dkh-ios/DKHCRM.xcodeproj
```

Then select the `DKHCRM` scheme and an iPhone simulator.

The target includes Apple's authorization entitlement. Provisioning must use an
Apple Developer team where the bundle ID `de.daskuechenhaus.crm` has the Apple
authorization capability enabled.

## Command-Line Validation

```powershell
xcodebuild -list -project apps/dkh-ios/DKHCRM.xcodeproj
xcodebuild -project apps/dkh-ios/DKHCRM.xcodeproj -scheme DKHCRM -destination 'generic/platform=iOS Simulator' CODE_SIGNING_ALLOWED=NO build
python -m pytest tests/test_dkh_ios_app.py
```

## Not Part Of This App Yet

- Replacing the DKH browser CRM.
- Cloudflare Access verification inside the app.
- A separate app login area.
- Offline customer storage.
- Push notifications, background sync, TestFlight, or App Store release.
