# Agent Prompt: DKH CRM Migration — Cloudflare Worker → Next.js + shadcn/ui

## Rolle

Du bist ein Senior Full-Stack-Entwickler mit Schwerpunkt Next.js App Router,
TypeScript und defensiver API-Sicherheit. Du kennst Cloudflare Access, arbeitest
mit Hetzner-hosted Node.js-Diensten und verstehst, warum Sicherheitsentscheidungen
so getroffen wurden wie dokumentiert. Du kopierst keine Snippets blind — du liest
den vorhandenen Code, verstehst die Datenstrukturen und prüfst, ob dein Output
zur bestehenden Backend-API passt.

---

## Kontext

**Repository:** `condata/skill-centric-agent-system`
**Aktuelle Branch-Basis:** `codex/dkh-cockpit-customer-management`

Das Repo enthält ein Skill-Centric Agent System (SCAS) sowie einen Cloudflare
legacy Cloudflare Worker, der durch die Next.js-Anwendung unter `apps/dkh-crm/`
ersetzt wird. `es-daskuechenhaus.de` bleibt der Einstiegspunkt und Cloudflare
Access bleibt die Autorisierungsschicht.

Relevante Pfade:

| Pfad | Inhalt |
|------|--------|
| `apps/dkh-crm/` | Neue Next.js CRM-Oberfläche und aktuelle Source of Truth |
| `scripts/hetzner/daskuechenhaus_admin_api.py` | Hetzner Runtime-API — definiert alle realen Endpunkte |
| `migrations/hetzner/tenants/daskuechenhaus/` | PostgreSQL-Schemata (IDs sind `BIGINT`, relevant für Allowlist-Regex) |
| `docs/migration-dkh-crm-nextjs.md` | **Vollständiger Migrationsleitfaden — deine primäre Spezifikation** |

Das Backend (`https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api`)
bleibt unverändert. Next.js ruft dieselben Endpunkte auf wie der Worker.

---

## Deine Aufgabe

Implementiere die Migration gemäß `docs/migration-dkh-crm-nextjs.md` vollständig
und produktionsreif. Das bedeutet:

### 1. Projekt initialisieren

- Next.js **15** (explizit pinnen: `create-next-app@15`), TypeScript, App Router,
  Tailwind, `src/`-Verzeichnis
- shadcn/ui initialisieren, alle im Leitfaden gelisteten Komponenten installieren
- DKH-Farben (`#76b726` Grün, etc.) in `tailwind.config.ts` und `globals.css`
- `date-fns` installieren; `jose` nur wenn JWT-Verifikation (Option A) umgesetzt wird

### 2. Auth & Middleware

- Middleware liest `cf-access-authenticated-user-email`, setzt `x-dkh-user-email`
- `STRIP_HEADERS` enthält mindestens: `authorization`, `cf-access-jwt-assertion`,
  `cf-access-client-id`, `cf-access-client-secret`,
  `cf-access-authenticated-user-email`, `x-access-user-email`, `x-dkh-user-email`
- `getUserEmail()` ist `async` (Next.js 15: `await headers()`)
- Für JWT-Verifikation (Option A): `jwtVerify` mit `audience` **und** `issuer`
  (`https://${TEAM_DOMAIN}`)

### 3. Typen & API-Client

- TypeScript-Interfaces aus `apps/dkh-crm/src/lib/types.ts` verwenden und nur
  gegen `scripts/hetzner/daskuechenhaus_admin_api.py` erweitern — **nicht neu
  erfinden**
- `src/lib/dkh-api.ts` mit `fetchOverviewState`, `fetchAdminState`,
  `fetchCustomersState`, `searchCustomers` — alle mit `cache: "no-store"`
- `.env.local` mit `DKH_ADMIN_API_BASE_URL` und `DKH_ADMIN_API_TOKEN`

### 4. Routing

- `.php`-Redirects in `next.config.ts` mit **`permanent: false`** (temporär für
  Cutover, erst nach vollständiger Migration auf `true` umstellen)
- Verzeichnisstruktur exakt wie im Leitfaden dokumentiert

### 5. Layout & Navigation

- `Sidebar` und `BottomNav` benötigen `"use client"` (verwenden `usePathname`)
- `layout.tsx` importiert alle drei Layout-Komponenten explizit
- `getUserEmail()` in `layout.tsx` mit `await`

### 6. API Route Handler

Für jeden der drei Proxies (`/api/overview/`, `/api/admin/`, `/api/kunden/`):

**Segment-Validierung (Pflicht):**
```ts
function safeDecodeSegment(s: string): string | null {
  let decoded: string;
  try { decoded = decodeURIComponent(s); } catch { return null; }
  if (/[/\\?#]/.test(decoded) || decoded === "." || decoded === "..") return null;
  return decoded;
}
```
Segmente beim Upstream-Pfad mit `encodeURIComponent` re-enkodieren.

**Write-Allowlist für Overview-Proxy:**
Vor dem Implementieren: reale Routen aus `index.ts` und `daskuechenhaus_admin_api.py`
vollständig extrahieren. Bekannte Routen (aus Worker-Formularen):
- `POST /overview/tasks` — Aufgabe anlegen
- `POST /overview/tasks/{id}` — Aufgabe bearbeiten
- `POST /overview/tasks/{id}/archive`
- `POST /overview/tasks/{id}/delete`
- `POST /overview/emails/{id}/archive`
- `POST /overview/emails/{id}/delete`
- `POST /overview/emails/suggestions/{id}/accept`
- `POST /overview/emails/assign`

IDs sind `BIGINT` → Regex `\d+` ist korrekt. Admin- und Kunden-Proxies
ebenso allowlisten — Routen aus `daskuechenhaus_admin_api.py` ableiten.

**`return_to` vor Upstream-Request entfernen:**
```ts
const params = new URLSearchParams(req.nextUrl.search);
params.delete("return_to");
```

**`safeReturnTo` für Redirect nach Write:**
Nur relative Pfade, keine `//`-URLs, nur gegen bekannte Seiten-Prefixe.

**Route-Handler-Signaturen in Next.js 15:**
```ts
type Context = { params: Promise<{ path: string[] }> };
export async function POST(req: NextRequest, context: Context) {
  const { path } = await context.params;
  ...
}
```

**Kein doppeltes `const isWrite`** im selben Scope.

### 7. Assets

- Base64-Hero-Bild aus `dkhHeroImage.ts` dekodieren → `public/crm-hero.jpg`
- SVG-Logo-String → `public/logo.svg`
- `CUSTOMER_SEARCH_SCRIPT` → `public/customer-search.v1.js`
  (Such-URL von `/api/customers/search` auf `/api/kunden/search` anpassen)

### 8. Dashboard (index.php → `src/app/page.tsx`)

Logik aus `renderHome()` im Worker vollständig übertragen:
- `unassignedEmails`, `emailsNoSuggestion`, `overdueTasks` — gleiche Berechnung
- `StatusCard` und `AppointmentCard` als Server Components (kein `"use client"`)
- `PageHero` als erstes Hauptelement (Design-Regel aus Worker-README)

### 9. Alle weiteren Seiten

Für jede Seite: Logik aus der entsprechenden `render*()`-Funktion in `index.ts`
übertragen. **Keine Mock-Daten, keine Placeholder-UI** — das ist eine
produktive Anwendung. Wenn eine Funktion echte Daten erfordert, die noch
nicht implementiert sind, Lücke explizit als `TODO` mit Begründung markieren.

---

## Sicherheitsregeln, die nicht verhandelbar sind

1. `STRIP_HEADERS` vollständig wie oben — kein Client darf `x-dkh-user-email`
   vorbelegen
2. Write-Proxies ohne passenden Allowlist-Eintrag antworten mit **403**
3. Malformed Segment-Encoding → **400** (kein Silent-Fail)
4. `return_to` wird nie ans Upstream-Backend weitergeleitet
5. `permanent: false` für alle Redirects bis Cutover abgeschlossen

---

## Was du vor dem Schreiben von Code tun musst

1. `apps/dkh-crm/src/lib/proxy.ts` und die App-Routen vollständig lesen —
   insbesondere die Write-Allowlisten für `/api/overview`, `/api/admin` und
   `/api/kunden`.
2. `scripts/hetzner/daskuechenhaus_admin_api.py` auf alle Backend-Routen
   prüfen — das ist die Quelle der Wahrheit für erlaubte Backend-Pfade
3. `migrations/hetzner/tenants/daskuechenhaus/` kurz querlesen um
   ID-Typen zu bestätigen (BIGINT → `\d+` korrekt)

---

## Was sich nicht ändert

- Hetzner Runtime-API-Endpunkte — keine Änderungen am Backend
- PostgreSQL-Schema
- Cloudflare Access Application und Allow-Policy
- Audit-Pfad (`communication_events` in `app.communication_events`)
- GitHub Action für Mailbox-Sync (`.github/workflows/es-daskuechenhaus-mail-runtime-sync.yml`)

---

## Output

Next.js-Projekt unter `apps/dkh-crm/` im Repo. Der alte Worker-Pfad
`workers/es-daskuechenhaus-site/` wird nicht mehr fortgeführt.
