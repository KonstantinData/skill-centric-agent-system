# KHH iOS Workbench

Native SwiftUI shell for the Kinderhaus Heuschrecken workbench.

The existing browser workbench in `apps/khh-workbench` remains the production
web surface for `kinderhaus-heuschrecken.cloud`. This app is an additional iOS
surface, not a replacement for the browser version.

## Current Scope

- Native SwiftUI dashboard for the KHH Heute surface.
- Read-only leadership, deadline, risk, service, case, occupancy, development,
  document, and task navigation.
- Static KHH workbench snapshot aligned with the current shared web/domain
  foundation.
- No child, parent, or staff master-data records.
- No write intents, push notifications, offline secure storage, or App Store
  release configuration yet.

## Open In Xcode

```powershell
open apps/khh-ios/KHHWorkbench.xcodeproj
```

Then select the `KHHWorkbench` scheme and an iPhone simulator.

## Command-Line Validation

```powershell
xcodebuild -list -project apps/khh-ios/KHHWorkbench.xcodeproj
xcodebuild -project apps/khh-ios/KHHWorkbench.xcodeproj -scheme KHHWorkbench -destination 'generic/platform=iOS Simulator' build
python -m pytest tests/test_khh_ios_app.py
```

## Release Notes

Before TestFlight or App Store work, configure an Apple Developer team,
provisioning, Cloudflare Access/OIDC handoff, secure storage, and release
evidence. Do not store Apple credentials or provisioning secrets in the
repository.
