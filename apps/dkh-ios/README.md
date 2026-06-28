# DKH iOS CRM

Native iOS container for the productive DKH CRM tenant `daskuechenhaus`.

The CRM source of truth remains the production Web App in
`apps/dkh-crm/`, served through `https://es-daskuechenhaus.de` and
`https://www.es-daskuechenhaus.de`. The iOS app loads that same Web App in a
Safari-based in-app browser, so users see the same pages, content, design, and
server-side functions they use in the browser without an isolated WebView login
context.

## Current Scope

- Full Web App execution through `SFSafariViewController` against
  `https://es-daskuechenhaus.de`.
- Same routing, customer pages, appointment/task/e-mail/case/template/admin
  surfaces, purchase contract and invoice flows as the browser app.
- Same production backend, API proxy, object-storage document handling, and
  tenant database authority as `apps/dkh-crm/`.
- No duplicate static CRM snapshot and no native demo dashboard.
- No app-owned authentication screen, credential prompt, or user/session
  management. Device/user sign-in is handled outside the app code.
- No `WKWebView` startup against the protected host. The app uses the iOS
  SafariServices browser context to avoid the invalid login-session behavior
  seen in isolated embedded WebViews.
- Tenant identity fixed to `daskuechenhaus` through the production DKH host.

## Tenant And App Boundaries

```text
tenant_id: daskuechenhaus
area_id: daskuechenhaus
web_app: apps/dkh-crm/
ios_app: apps/dkh-ios/
production_web_hosts: es-daskuechenhaus.de, www.es-daskuechenhaus.de
```

The iOS app may only load the DKH production CRM hosts listed above. It must
not embed copied customer records, private contact data, raw API responses,
object-storage documents, secrets, access tokens, or Hetzner runtime
credentials in the repository. Live data remains behind the existing Web App
and its server-side controls.

## Privacy And Runtime Limits

- The repository contains no CRM data export, no demo customer database, and no
  copied page payloads from production.
- Customer data, document access, write actions, mail handling, purchase
  contracts, invoices, and admin functions stay in the existing Web App.
- The iOS app does not store tokens in app code or repository files.
- Apple Developer credentials, provisioning profiles, secrets, and API tokens
  belong outside the repository.

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
- A second native implementation of CRM screens.
- Local offline customer summaries or duplicated CRM storage.
- Push notifications, background sync, TestFlight, or App Store release.
