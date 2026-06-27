# KHH Mobile Proof Shell

Expo Router proof shell for the KHH tenant workbench architecture.

It is not a production native app. It proves that the future iOS surface can
consume the same shared domain, client, state, and UI contracts as the web
shell.

## App Structure

- `app/_layout.tsx`: Expo Router stack shell.
- `app/index.tsx`: KHH Heute proof screen rendered from shared domain, client,
  state, and UI contracts.
- `src/native-runtime.ts`: native adapter wiring for auth handoff,
  tenant-scoped storage, offline summaries, push opt-in, and permissions.

## Native Contracts

- Auth: Cloudflare Access/OIDC claims enter through a native adapter and must
  match immutable `tenant_kinderhaus` and `kinderhaus-heuschrecken` scope.
- Offline: read-only cached summaries only, with tenant-scoped storage keys and
  purge on logout.
- Push: opt-in only, tenant-scoped topics, no sensitive payloads.
- Permissions: denied by default and role-gated before native feature use.

The proof shell uses a storage backend interface so production can bind an
approved secure store without changing the shared client contract.

## Toolchain Residual Risk

The npm audit finding for `uuid@7.0.3` is not on the KHH web cockpit runtime
path. It is limited to the native proof build-tooling chain:

```text
khh-mobile-proof
-> expo
-> @expo/config-plugins
-> xcode
-> uuid@7.0.3
```

Treat this as `needs_review` for native build tooling, not as an actionable
KHH web production issue. Do not run `npm audit fix --force` or add a blind
`uuid` override unless Expo prebuild, iOS build, and Simulator validation have
passed on a Mac. A force fix currently proposes an Expo downgrade that would
invalidate the Expo 56 proof line.

## Validation

```powershell
npm --prefix apps/khh-mobile-proof run check
```
