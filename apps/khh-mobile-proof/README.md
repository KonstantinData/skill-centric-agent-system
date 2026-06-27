# KHH Mobile Proof Shell

Minimal Expo proof shell for the KHH tenant workbench architecture.

It is not a production native app. It proves that the future iOS surface can
consume the same shared domain, client, state, and UI contracts as the web
shell.

## Native Contracts

- Auth: Cloudflare Access/OIDC claims enter through a native adapter and must
  match immutable `tenant_kinderhaus` and `kinderhaus-heuschrecken` scope.
- Offline: read-only cached summaries only, with tenant-scoped storage keys and
  purge on logout.
- Push: opt-in only, tenant-scoped topics, no sensitive payloads.
- Permissions: denied by default and role-gated before native feature use.

## Validation

```powershell
npm --prefix apps/khh-mobile-proof run check
```
