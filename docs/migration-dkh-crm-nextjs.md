# Migration: Cloudflare Worker → Next.js + shadcn/ui

## Status nach Cutover-Entscheid

Der produktive Einstiegspunkt bleibt `es-daskuechenhaus.de` bzw.
`www.es-daskuechenhaus.de`. Cloudflare Access bleibt als Autorisierungsschicht
erhalten. Das alte Cloudflare-Worker-UI-System wird nicht parallel weitergeführt
und wurde aus dem Repository entfernt. Source of Truth für die CRM-Oberfläche
ist jetzt `apps/dkh-crm/`.

## Ausgangslage

Der entfernte Cloudflare Worker (`src/index.ts`, ~5700 Zeilen) machte alles in einer einzigen Datei:
- HTML per String-Konkatenation rendern
- API-Requests an `daskuechenhaus.condata.io` proxyen
- Tenant-Assets (Logo, Hero-Bild, JS-Skript) ausliefern
- Auth-Email aus `cf-access-authenticated-user-email`-Header lesen

Das Backend bleibt unverändert: **Hetzner PostgreSQL + Runtime-API** unter
`https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api`.

---

## Zielarchitektur

```
Browser
  │
  ▼
Cloudflare Access (Auth-Gate, bleibt erhalten)
  │  setzt cf-access-authenticated-user-email Header
  ▼
Next.js App auf Hetzner (Node.js Server, Port 3000)
  │  ├── App Router Pages (Server Components)
  │  ├── API Routes (ersetzen Worker-Proxies)
  │  └── Middleware (liest CF-Access-Header, setzt x-dkh-user-email)
  │
  ▼
Hetzner Runtime-API
(PostgreSQL, unverändert)
```

Cloudflare Access bleibt als Schutzschicht. Next.js liest den von Cloudflare
gesetzten `cf-access-authenticated-user-email`-Header aus. **Wichtig: der
Hetzner-Server darf nicht direkt aus dem Internet erreichbar sein** — sonst
kann ein Angreifer diesen Header selbst setzen (siehe Phase 2).

---

## Phase 1 — Projekt aufsetzen

Next.js veröffentlicht regelmäßig neue Versionen; die offizielle Doku zeigt
aktuell **Next.js 16**. Zum Pinnen einer bestimmten Version die Versionsnummer
explizit angeben:

```bash
# Next.js 15 (stabil, empfohlen wenn Next 16 noch nicht getestet):
npx create-next-app@15 dkh-crm ...

# Next.js 16 (aktuelle offizielle Doku-Version):
npx create-next-app@16 dkh-crm ...
```

Vor Umsetzung prüfen, welche Version produktiv eingesetzt werden soll, und
dann konsequent diese pinnen. `@latest` zieht immer die neueste Major-Version
und kann Breaking Changes bringen.

Weitere Versionen: **shadcn/ui (aktuelle CLI)**, **Node 20+**.

### 1.1 Next.js-Projekt erstellen

```bash
npx create-next-app@15 dkh-crm \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"

cd dkh-crm
```

### 1.2 shadcn/ui initialisieren

```bash
npx shadcn@latest init
```

Antworten:
- Style: **Default**
- Base color: **Neutral** (Grün wird als Custom-Color hinzugefügt)
- CSS variables: **Yes**

Danach die benötigten Komponenten installieren:

```bash
npx shadcn@latest add card badge button dialog sheet table tabs
npx shadcn@latest add calendar popover select input label textarea
npx shadcn@latest add dropdown-menu avatar separator skeleton
```

### 1.3 Weitere Abhängigkeiten

```bash
npm install lucide-react
npm install date-fns   # Datum-Formatierung (ersetzt formatDateTime())
```

`jose` wird **nicht** benötigt, solange die Variante ohne JWT-Verifikation
gewählt wird (siehe Phase 2).

### 1.4 Daskuechenhaus-Farben in Tailwind eintragen

In `tailwind.config.ts`:

```ts
theme: {
  extend: {
    colors: {
      dkh: {
        green:        "#76b726",
        "green-dark": "#34591b",
        soft:         "#eef6e8",
        band:         "#f4f7f1",
        border:       "#d8dfd4",
        muted:        "#4f5b4a",
      },
    },
  },
},
```

In `src/app/globals.css` die shadcn-CSS-Variablen auf das DKH-Grün anpassen:

```css
:root {
  --primary: 96 54% 45%;          /* #76b726 als HSL */
  --primary-foreground: 0 0% 7%;  /* #111111 */
  --ring: 96 54% 45%;
}
```

---

## Phase 2 — Auth & Middleware

### Sicherheitsvoraussetzung: Hetzner-Server gegen direkten Zugriff sperren

Der `cf-access-authenticated-user-email`-Header wird von Cloudflare Access
gesetzt. Wenn Port 443 direkt aus dem Internet erreichbar ist, kann ein
Angreifer diesen Header selbst mitschicken und die Auth umgehen.

**Empfohlene Topologie:** Next.js lauscht nur auf `127.0.0.1:3000`. Ein
Reverse Proxy (nginx oder Caddy) auf Port 443 terminiert TLS und leitet intern
weiter. Port 3000 ist niemals öffentlich erreichbar.

```
Internet → Cloudflare (Access + Proxy) → Hetzner :443 (nginx) → 127.0.0.1:3000 (Next.js)
```

**Pflicht vor Go-Live:** Den Server so konfigurieren, dass nur Cloudflare-IPs
auf Port 443 zugreifen können. Cloudflare veröffentlicht beide Listen:

```bash
# ufw: Cloudflare IPv4-Ranges erlauben (https://www.cloudflare.com/ips-v4)
ufw default deny incoming
ufw allow from 173.245.48.0/20 to any port 443
ufw allow from 103.21.244.0/22 to any port 443
ufw allow from 103.22.200.0/22 to any port 443
ufw allow from 103.31.4.0/22   to any port 443
ufw allow from 141.101.64.0/18 to any port 443
ufw allow from 108.162.192.0/18 to any port 443
ufw allow from 190.93.240.0/20 to any port 443
ufw allow from 188.114.96.0/20 to any port 443
ufw allow from 197.234.240.0/22 to any port 443
ufw allow from 198.41.128.0/17 to any port 443
ufw allow from 162.158.0.0/15  to any port 443
ufw allow from 104.16.0.0/13   to any port 443
ufw allow from 104.24.0.0/14   to any port 443
ufw allow from 172.64.0.0/13   to any port 443
ufw allow from 131.0.72.0/22   to any port 443

# Cloudflare IPv6-Ranges erlauben (https://www.cloudflare.com/ips-v6)
# Wenn der Server eine AAAA-Adresse hat, reichen IPv4-Rules allein nicht!
ufw allow from 2400:cb00::/32  to any port 443
ufw allow from 2606:4700::/32  to any port 443
ufw allow from 2803:f800::/32  to any port 443
ufw allow from 2405:b500::/32  to any port 443
ufw allow from 2405:8100::/32  to any port 443
ufw allow from 2a06:98c0::/29  to any port 443
ufw allow from 2c0f:f248::/32  to any port 443

# SSH auf Admin-IP oder VPN beschränken, nicht global öffnen.
# Beispiel mit fester Admin-IP (anpassen):
ufw allow from <ADMIN-IP> to any port 22
ufw enable
```

**IP-Allowlist allein reicht für CRM-Daten nicht aus.** Eine Cloudflare-IP
beweist nur, dass die Anfrage durch das Cloudflare-Netzwerk lief — nicht, dass
sie durch die konkrete Access-Application autorisiert wurde. Ein Angreifer
könnte z.B. über eine andere Cloudflare-Property dieselben IP-Ranges nutzen.

Cloudflare empfiehlt deshalb eine der folgenden Zusatzmaßnahmen:

**Option A — Access-JWT validieren (empfohlen für CRM-Daten):**
Der Header `cf-access-jwt-assertion` enthält ein von Access signiertes JWT.
Die Middleware kann es mit `jose` gegen die JWKS-Endpoint verifizieren:

```ts
import { createRemoteJWKSet, jwtVerify } from "jose";

const TEAM_DOMAIN = process.env.CF_ACCESS_TEAM_DOMAIN!; // z.B. "daskuechenhaus.cloudflareaccess.com"
const AUD         = process.env.CF_ACCESS_AUD!;          // Application Audience Tag aus CF-Dashboard
const JWKS        = createRemoteJWKSet(
  new URL(`https://${TEAM_DOMAIN}/cdn-cgi/access/certs`)
);

export async function verifyAccessJwt(token: string): Promise<string | null> {
  try {
    const { payload } = await jwtVerify(token, JWKS, {
      audience: AUD,
      // issuer muss explizit geprüft werden; Cloudflare empfiehlt dies ausdrücklich.
      issuer: `https://${TEAM_DOMAIN}`,
    });
    return (payload.email as string) ?? null;
  } catch {
    return null;
  }
}
```

In `middleware.ts` dann statt `cf-access-authenticated-user-email` den JWT
verifizieren und die Email aus dem Payload lesen. `jose` als Dependency
hinzufügen: `npm install jose`.

**Option B — Authenticated Origin Pulls (einfacher, weniger Code):**
In Cloudflare SSL/TLS → Origin Server → Authenticated Origin Pulls aktivieren.
Der Origin-Server (nginx) prüft dann das von Cloudflare mitgeschickte
Client-Zertifikat. Anleitung:
`https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/`

**Wichtig:** Cloudflare unterscheidet drei AOP-Setups:

- **Globales AOP**: aktiviert für alle proxied Hostnames der Zone; verwendet ein
  von Cloudflare ausgestelltes Zertifikat, das über alle Cloudflare-Accounts geteilt
  wird. Beweist nur Cloudflare-Netzwerk — kein Schutz gegen andere Cloudflare-Kunden.
  Quelle: `https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/global/`
- **Zone-level AOP**: eigenes Zertifikat wird in die Zone hochgeladen; nur Anfragen
  mit diesem spezifischen Zertifikat werden akzeptiert. Stärkere Bindung als globales AOP.
  Quelle: `https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/zone-level/`
- **Per-hostname AOP**: Zertifikat wird pro Hostname konfiguriert; engste Bindung,
  empfohlen wenn AOP die primäre Absicherungsschicht ist.

Für einen internen Einzelmandanten mit per-hostname AOP **und** IP-Allowlist ist
das Risiko überschaubar. Für produktive CRM-Daten ist Option A (JWT-Validierung)
die belastbarere Wahl.

### 2.1 `src/middleware.ts`

Die Middleware liest den CF-Access-Header, setzt den internen
`x-dkh-user-email`-Header und entfernt sicherheitsrelevante Header, die nicht
an Next.js-Handler oder das Upstream-Backend durchgereicht werden sollen
(`authorization`, `cf-access-jwt-assertion` und weitere sensible `x-*`-Header).

```ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Header, die intern nicht weitergetragen werden sollen.
// Enthält auch die Auth-Quell-Header und potenzielle Spoofing-Vektoren,
// damit kein Client x-dkh-user-email oder x-access-user-email vorbelegen kann.
const STRIP_HEADERS = [
  "authorization",
  "cf-access-jwt-assertion",
  "cf-access-client-id",
  "cf-access-client-secret",
  "cf-access-authenticated-user-email",  // wird unten neu aus dem JWT/Header gesetzt
  "x-access-user-email",                 // internes Backend-Header, nicht vom Client
  "x-dkh-user-email",                    // wird unten neu gesetzt; vorherigen Wert verwerfen
];

export function middleware(request: NextRequest) {
  const userEmail =
    request.headers.get("cf-access-authenticated-user-email") ?? "";

  // In Production ohne gültige Email: Anfrage ablehnen.
  // Cloudflare Access sollte dies bereits verhindern; dies ist der letzte Fallback.
  if (!userEmail && process.env.NODE_ENV === "production") {
    return new NextResponse("Nicht autorisiert", { status: 401 });
  }

  const requestHeaders = new Headers(request.headers);

  // Sensible Header entfernen, bevor die Anfrage an Handler weitergeleitet wird.
  for (const name of STRIP_HEADERS) {
    requestHeaders.delete(name);
  }

  // Internen Auth-Header setzen.
  requestHeaders.set("x-dkh-user-email", userEmail);

  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  // Statische Assets und Next.js-Internals ausschließen
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico|logo\\.svg|crm-hero\\.jpg).*)"],
};
```

### 2.2 Helper zum Auslesen der User-Email

`headers()` ist in Next.js 15 eine asynchrone Funktion. Alle Aufrufer müssen
`await` verwenden.

`src/lib/auth.ts`:

```ts
import { headers } from "next/headers";

export async function getUserEmail(): Promise<string> {
  const h = await headers();
  return h.get("x-dkh-user-email") ?? "";
}
```

---

## Phase 3 — API-Client (ersetzt die fetch-Funktionen im Worker)

Der Worker enthält `fetchAdminState()`, `fetchOverviewState()`,
`fetchCustomersState()` sowie drei Proxy-Funktionen. Diese werden in
einen zentralen API-Client ausgelagert.

### 3.1 `src/lib/dkh-api.ts`

```ts
import type { AdminState, OverviewState, CustomersState } from "./types";

const BASE_URL = process.env.DKH_ADMIN_API_BASE_URL!;
const TOKEN    = process.env.DKH_ADMIN_API_TOKEN!;

function apiUrl(path: string): string {
  return `${BASE_URL.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

async function apiFetch<T>(
  path: string,
  userEmail: string,
  init?: RequestInit,
): Promise<T | null> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      "x-dkh-admin-api-token": TOKEN,
      "x-access-user-email":   userEmail,
      "content-type":          "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return res.json() as Promise<T>;
}

export async function fetchOverviewState(userEmail: string) {
  return apiFetch<OverviewState>("/overview/state", userEmail);
}

export async function fetchAdminState(userEmail: string) {
  return apiFetch<AdminState>("/admin/state", userEmail);
}

export async function fetchCustomersState(userEmail: string) {
  return apiFetch<CustomersState>("/customers/state", userEmail);
}

export async function searchCustomers(userEmail: string, q: string) {
  return apiFetch<{ customers: unknown[] }>(
    `/customers/search?q=${encodeURIComponent(q)}`,
    userEmail,
  );
}
```

Die Typen (`OverviewState`, `AdminState`, `CustomersState`) liegen nach dem
Cutover in `apps/dkh-crm/src/lib/types.ts`. Erweiterungen werden gegen
`scripts/hetzner/daskuechenhaus_admin_api.py` validiert, nicht mehr gegen einen
Worker-Quellstand.

### 3.2 `.env.local` für lokale Entwicklung

```env
DKH_ADMIN_API_BASE_URL=https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api
DKH_ADMIN_API_TOKEN=<token>
```

---

## Phase 4 — Routing & Seitenstruktur

### Mapping Worker-Routen → Next.js-Seiten

| Worker-Route       | Next.js-Seite                        |
|--------------------|--------------------------------------|
| `/index.php`       | `/` (Redirect von `/index.php`)      |
| `/termine.php`     | `/termine`                           |
| `/aufgaben.php`    | `/aufgaben`                          |
| `/emails.php`      | `/emails`                            |
| `/kunden.php`      | `/kunden`                            |
| `/vorgaenge.php`   | `/vorgaenge`                         |
| `/admin.php`       | `/admin`                             |
| `/admin-api/*`     | `/api/admin/[...path]` (Route Handler)    |
| `/overview-api/*`  | `/api/overview/[...path]`            |
| `/customers-api/*` | `/api/kunden/[...path]`              |

Für Rückwärtskompatibilität `.php`-Redirects in `next.config.ts`.
**Während Cutover und Parallelbetrieb `permanent: false` (307) verwenden**,
damit Browser und CDNs die Weiterleitungen nicht dauerhaft cachen. Erst nach
vollständiger Migration und ausreichend Beobachtungszeit auf `permanent: true`
(308) umstellen:

```ts
async redirects() {
  return [
    { source: "/index.php",    destination: "/",         permanent: false },
    { source: "/termine.php",  destination: "/termine",  permanent: false },
    { source: "/aufgaben.php", destination: "/aufgaben", permanent: false },
    { source: "/emails.php",   destination: "/emails",   permanent: false },
    { source: "/kunden.php",   destination: "/kunden",   permanent: false },
    { source: "/admin.php",    destination: "/admin",    permanent: false },
  ];
},
```

### Verzeichnisstruktur

```
src/
├── app/
│   ├── layout.tsx              ← Shell (Sidebar + TopBar + BottomNav)
│   ├── page.tsx                ← Dashboard (index.php)
│   ├── termine/page.tsx
│   ├── aufgaben/page.tsx
│   ├── emails/page.tsx
│   ├── kunden/
│   │   ├── page.tsx
│   │   └── [id]/page.tsx       ← Kundenakte
│   ├── vorgaenge/page.tsx
│   ├── admin/page.tsx
│   └── api/
│       ├── admin/[...path]/route.ts
│       ├── overview/[...path]/route.ts
│       └── kunden/
│           ├── [...path]/route.ts
│           └── search/route.ts
├── components/
│   ├── layout/
│   │   ├── sidebar.tsx         ← "use client" (usePathname)
│   │   ├── top-bar.tsx
│   │   └── bottom-nav.tsx      ← "use client" (usePathname), Mobile Tab Bar
│   ├── dashboard/
│   │   ├── status-card.tsx
│   │   └── appointment-card.tsx
│   ├── tasks/
│   ├── emails/
│   ├── customers/
│   └── ui/                     ← shadcn/ui (auto-generiert)
├── lib/
│   ├── dkh-api.ts
│   ├── auth.ts
│   ├── types.ts
│   └── utils.ts
└── middleware.ts
```

---

## Phase 5 — Layout & Navigation

### 5.1 Root Layout (`src/app/layout.tsx`)

```tsx
import { Sidebar } from "@/components/layout/sidebar";
import { TopBar } from "@/components/layout/top-bar";
import { BottomNav } from "@/components/layout/bottom-nav";
import { getUserEmail } from "@/lib/auth";

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const email = await getUserEmail();

  return (
    <html lang="de">
      <body className="bg-dkh-band">
        <div className="flex h-screen overflow-hidden">
          <Sidebar className="hidden md:flex" />
          <div className="flex flex-1 flex-col overflow-hidden">
            <TopBar userEmail={email} />
            <main className="flex-1 overflow-y-auto p-4 md:p-6">
              {children}
            </main>
          </div>
        </div>
        <BottomNav className="md:hidden" />
      </body>
    </html>
  );
}
```

### 5.2 Sidebar-Komponente

`usePathname` ist ein Client-Hook — die Komponente benötigt `"use client"`.

```tsx
// src/components/layout/sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Calendar, CheckSquare,
  Mail, Users, Settings,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/",         label: "Übersicht", icon: LayoutDashboard },
  { href: "/termine",  label: "Termine",   icon: Calendar        },
  { href: "/aufgaben", label: "Aufgaben",  icon: CheckSquare     },
  { href: "/emails",   label: "E-Mails",   icon: Mail            },
  { href: "/kunden",   label: "Kunden",    icon: Users           },
  { href: "/admin",    label: "Admin",     icon: Settings        },
];

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();

  return (
    <aside className={`w-64 border-r bg-white flex flex-col ${className}`}>
      <div className="p-4 border-b">
        <img src="/logo.svg" alt="das küchenhaus" className="h-10 w-auto" />
      </div>
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={`
              flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
              transition-colors
              ${pathname === href
                ? "bg-dkh-soft text-dkh-green-dark border-l-4 border-dkh-green"
                : "text-dkh-muted hover:bg-dkh-band hover:text-dkh-green-dark"
              }
            `}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
```

`BottomNav` folgt demselben Muster mit `"use client"` und `usePathname`.

---

## Phase 6 — Dashboard (index.php → `src/app/page.tsx`)

`getUserEmail()` ist jetzt async, daher `async` Page:

```tsx
// src/app/page.tsx
import { fetchOverviewState } from "@/lib/dkh-api";
import { getUserEmail } from "@/lib/auth";
import { StatusCard } from "@/components/dashboard/status-card";
import { AppointmentCard } from "@/components/dashboard/appointment-card";
import { PageHero } from "@/components/layout/page-hero";
import { isToday, isOverdue } from "@/lib/utils";

export default async function DashboardPage() {
  const email = await getUserEmail();
  const state = await fetchOverviewState(email);

  if (!state) {
    return <p className="text-red-600">Daten konnten nicht geladen werden.</p>;
  }

  const unassignedEmails   = state.emails.filter(e => e.is_unassigned).length;
  const emailsNoSuggestion = state.emails.filter(
    e => e.is_unassigned && e.suggestions.length === 0,
  ).length;
  const overdueTasks      = state.tasks.filter(t => isOverdue(t.due_at)).length;
  const todayAppointments = state.appointments.filter(a => isToday(a.starts_at));
  const emailSignal       = emailsNoSuggestion > 0 ? "red"
    : unassignedEmails > 0 ? "yellow" : "green";

  return (
    <div className="space-y-6">
      <PageHero
        title="Betriebsübersicht"
        lede={`Guten Tag, ${state.current_user.display_name || email}`}
      />

      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-dkh-muted mb-3">
          Aufgaben & Kommunikation
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatusCard
            title="Offene Aufgaben"
            count={state.tasks.filter(t => !t.status.startsWith("done")).length}
            signal={overdueTasks > 0 ? "red" : "green"}
            reason={overdueTasks > 0 ? `${overdueTasks} überfällig` : "Alle im Plan"}
            href="/aufgaben"
          />
          <StatusCard
            title="Neue E-Mails"
            count={unassignedEmails}
            signal={emailSignal}
            reason={emailsNoSuggestion > 0
              ? `${emailsNoSuggestion} ohne Fallzuordnung`
              : "Alle zugeordnet"}
            href="/emails"
          />
          <StatusCard
            title="Beschaffungssignale"
            count={state.tasks.filter(t =>
              t.title.toLowerCase().includes("bestellung"),
            ).length}
            signal="green"
            reason="Alle im Zeitplan"
            href="/aufgaben"
          />
          <StatusCard
            title="Event-Themen"
            count={state.news_items.length}
            signal={state.news_items.length > 0 ? "yellow" : "green"}
            reason={`${state.news_items.length} aktiv`}
            href="/aufgaben"
          />
        </div>
      </section>

      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-dkh-muted mb-3">
          Termine heute & nächster
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <AppointmentCard label="Heutige Termine" appointments={todayAppointments} />
          <AppointmentCard
            label="Montage-Termine"
            appointments={state.appointments.filter(a =>
              a.title.toLowerCase().includes("montage"),
            )}
          />
          <AppointmentCard
            label="Service-Termine"
            appointments={state.appointments.filter(a =>
              a.title.toLowerCase().includes("service") ||
              a.title.toLowerCase().includes("kundendienst"),
            )}
          />
        </div>
      </section>
    </div>
  );
}
```

### StatusCard-Komponente (Server Component, kein `"use client"` nötig)

```tsx
// src/components/dashboard/status-card.tsx
import Link from "next/link";
import { cn } from "@/lib/utils";

type Signal = "red" | "yellow" | "green" | "neutral";

const signalStyles: Record<Signal, string> = {
  red:     "border-l-red-600 bg-red-50 border-red-200",
  yellow:  "border-l-amber-500 bg-amber-50 border-amber-200",
  green:   "border-l-green-700 bg-green-50 border-green-200",
  neutral: "border-l-gray-400 bg-white border-gray-200",
};

const dotStyles: Record<Signal, string> = {
  red:     "bg-red-600",
  yellow:  "bg-amber-500",
  green:   "bg-green-700",
  neutral: "bg-gray-400",
};

interface StatusCardProps {
  title: string;
  count: number;
  signal: Signal;
  reason: string;
  href?: string;
}

export function StatusCard({ title, count, signal, reason, href }: StatusCardProps) {
  const content = (
    <div className={cn(
      "rounded-lg border border-l-4 p-4 flex gap-3 items-start",
      signalStyles[signal],
      href && "hover:shadow-md transition-shadow",
    )}>
      <div className={cn("w-2.5 h-2.5 rounded-full mt-1.5 shrink-0", dotStyles[signal])} />
      <div className="min-w-0">
        <p className="text-xs font-bold uppercase tracking-wide text-dkh-muted">{title}</p>
        <p className="text-3xl font-semibold leading-none mt-1">{count}</p>
        <p className="text-xs text-dkh-muted mt-1.5 leading-snug">{reason}</p>
      </div>
    </div>
  );

  if (href) return <Link href={href}>{content}</Link>;
  return content;
}
```

---

## Phase 7 — API Route Handler (ersetzen Worker-Proxies)

Die drei Proxy-Funktionen werden zu Next.js Route Handlers. Das Beispiel
implementiert GET, POST, PUT und DELETE. PATCH und HEAD werden vom
Hetzner-Backend nicht verwendet und können bei Bedarf nach demselben Muster
ergänzt werden. `return_to`-Validierung ist ebenfalls enthalten.

### Hilfsfunktion: `return_to` absichern

Ein offener Redirect über `return_to` ist eine bekannte Schwachstelle.
Nur erlaubte Pfade dürfen als Redirect-Ziel akzeptiert werden:

```ts
// src/lib/return-to.ts
const ALLOWED_PREFIXES = ["/", "/aufgaben", "/emails", "/kunden", "/termine", "/vorgaenge", "/admin"];

export function safeReturnTo(value: string | null, fallback: string): string {
  if (!value) return fallback;
  // Nur relative Pfade, keine Protocol-relative URLs (//)
  if (!value.startsWith("/") || value.startsWith("//")) return fallback;
  const path = value.split("?")[0];
  if (!ALLOWED_PREFIXES.some(prefix => path === prefix || path.startsWith(prefix + "/"))) {
    return fallback;
  }
  return value;
}
```

### Overview-Proxy (vollständige Implementierung)

```ts
// src/app/api/overview/[...path]/route.ts
import { headers } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { safeReturnTo } from "@/lib/return-to";

const BASE  = process.env.DKH_ADMIN_API_BASE_URL!;
const TOKEN = process.env.DKH_ADMIN_API_TOKEN!;

// Erlaubte Write-Routen als Regex-Muster.
// Dynamische IDs sind numerisch (\d+). Weitere Routen hier ergänzen.
// Quelle nach Cutover: scripts/hetzner/daskuechenhaus_admin_api.py
const ALLOWED_OVERVIEW_WRITE_PATTERNS: RegExp[] = [
  /^tasks$/,                              // POST /overview/tasks          (anlegen)
  /^tasks\/\d+$/,                         // POST /overview/tasks/{id}     (bearbeiten)
  /^tasks\/\d+\/archive$/,                // POST /overview/tasks/{id}/archive
  /^tasks\/\d+\/delete$/,                 // POST /overview/tasks/{id}/delete
  /^emails\/\d+\/archive$/,               // POST /overview/emails/{id}/archive
  /^emails\/\d+\/delete$/,                // POST /overview/emails/{id}/delete
  /^emails\/suggestions\/\d+\/accept$/,   // POST /overview/emails/suggestions/{id}/accept
  /^emails\/assign$/,                     // POST /overview/emails/assign
];

// Segment sicher dekodieren: wirft bei malformed Encoding statt zu crashen.
// Lehnt Zeichen ab, die Pfad oder Query semantisch verändern können.
function safeDecodeSegment(s: string): string | null {
  let decoded: string;
  try {
    decoded = decodeURIComponent(s);
  } catch {
    return null; // malformed percent-encoding
  }
  // Ablehnen: Traversal, Pfadtrenner, Query- und Fragment-Zeichen
  if (/[/\\?#]/.test(decoded) || decoded === "." || decoded === "..") {
    return null;
  }
  return decoded;
}

async function proxy(req: NextRequest, segments: string[]): Promise<Response> {
  const h         = await headers();
  const userEmail = h.get("x-dkh-user-email") ?? "";

  // Segmente dekodieren und validieren.
  const decodedSegments: string[] = [];
  for (const s of segments) {
    const decoded = safeDecodeSegment(s);
    if (decoded === null) {
      return NextResponse.json({ error: "Ungültiger Pfad" }, { status: 400 });
    }
    decodedSegments.push(decoded);
  }

  // Für Writes: nur explizit allowgelistete Routen durchlassen.
  const isWrite  = req.method !== "GET" && req.method !== "HEAD";
  const actionKey = decodedSegments.join("/");
  if (isWrite && !ALLOWED_OVERVIEW_WRITE_PATTERNS.some((p) => p.test(actionKey))) {
    return NextResponse.json({ error: "Aktion nicht erlaubt" }, { status: 403 });
  }

  // Segmente beim Bauen des Upstream-Pfads erneut enkodieren (sicher).
  const upstreamPath = `/overview/${decodedSegments.map(encodeURIComponent).join("/")}`;

  // `return_to` ist nur für den lokalen Redirect nach einem Write gedacht
  // und soll nicht ans Backend weitergeleitet werden.
  const upstreamSearch = (() => {
    const params = new URLSearchParams(req.nextUrl.search);
    params.delete("return_to");
    const s = params.toString();
    return s ? `?${s}` : "";
  })();
  const upstreamUrl = `${BASE}${upstreamPath}${upstreamSearch}`;

  const upstream = await fetch(upstreamUrl, {
    method: req.method,
    headers: {
      "x-dkh-admin-api-token": TOKEN,
      "x-access-user-email":   userEmail,
      // Content-Type nur für Writes durchreichen
      ...(isWrite
        ? { "content-type": req.headers.get("content-type") ?? "application/x-www-form-urlencoded" }
        : {}),
    },
    body: isWrite ? req.body : undefined,
    // body streamen, nicht puffern
    duplex: "half",
  } as RequestInit);

  if (isWrite) {
    if (!upstream.ok) {
      return NextResponse.json(
        { error: "Speichern nicht möglich", status: upstream.status },
        { status: upstream.status },
      );
    }
    const returnTo = safeReturnTo(req.nextUrl.searchParams.get("return_to"), "/");
    return NextResponse.redirect(new URL(returnTo, req.url));
  }

  // GET: Antwort transparent weiterreichen
  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}

// In Next.js 15 sind params in Route Handlers async.
type Context = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(req, path);
}
export async function POST(req: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(req, path);
}
export async function PUT(req: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(req, path);
}
export async function DELETE(req: NextRequest, context: Context) {
  const { path } = await context.params;
  return proxy(req, path);
}
```

Das gleiche Muster für `/api/admin/[...path]/route.ts` (Präfix `/admin/`)
und `/api/kunden/[...path]/route.ts` (Präfix `/customers/`).

### Kunden-Suche (GET-only)

```ts
// src/app/api/kunden/search/route.ts
import { headers } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const BASE  = process.env.DKH_ADMIN_API_BASE_URL!;
const TOKEN = process.env.DKH_ADMIN_API_TOKEN!;

export async function GET(req: NextRequest) {
  const h         = await headers();
  const userEmail = h.get("x-dkh-user-email") ?? "";
  const q         = req.nextUrl.searchParams.get("q") ?? "";

  if (q.length < 3) {
    return NextResponse.json({ customers: [] });
  }

  const res = await fetch(
    `${BASE}/customers/search?q=${encodeURIComponent(q)}`,
    {
      headers: {
        "x-dkh-admin-api-token": TOKEN,
        "x-access-user-email":   userEmail,
        accept: "application/json",
      },
      cache: "no-store",
    },
  );

  if (!res.ok) {
    return NextResponse.json({ error: "Suche nicht verfügbar" }, { status: res.status });
  }

  const data = await res.json();
  return NextResponse.json(data);
}
```

Im Frontend ändert sich die URL von `/api/customers/search?q=...`
auf `/api/kunden/search?q=...`. Das `customer-search.v1.js`-Skript
entsprechend anpassen (eine Zeile).

---

## Phase 8 — Assets

| Aktuell im Worker                                  | In Next.js                           |
|----------------------------------------------------|--------------------------------------|
| Base64-Hero-Bild in `dkhHeroImage.ts`              | `public/crm-hero.jpg` (echte Datei)  |
| SVG-Logo als String in `DKH_TENANT_UI.brandAssets` | `public/logo.svg`                    |
| `CUSTOMER_SEARCH_SCRIPT` als Inline-String         | `public/customer-search.v1.js`       |

Vorgehen:
1. Das Base64-Hero-Bild aus `dkhHeroImage.ts` dekodieren und als `public/crm-hero.jpg` ablegen
2. Den SVG-Logo-String als `public/logo.svg` ablegen
3. Das `CUSTOMER_SEARCH_SCRIPT` als `public/customer-search.v1.js` ablegen und die Such-URL auf `/api/kunden/search` anpassen

In der `PageHero`-Komponente dann einfach:

```tsx
<div
  className="relative rounded-xl overflow-hidden"
  style={{ backgroundImage: "url('/crm-hero.jpg')" }}
>
```

---

## Phase 9 — Deployment auf Hetzner

### 9.1 `next.config.ts`

```ts
const nextConfig = {
  output: "standalone",   // Minimales Node.js-Bundle für Hetzner
};
export default nextConfig;
```

### 9.2 Build & Start

```bash
npm run build
node .next/standalone/server.js
```

Oder mit PM2:

```bash
pm2 start .next/standalone/server.js --name dkh-crm
```

### 9.3 Cloudflare-Seite

- DNS: `es-daskuechenhaus.de` → Hetzner-IP (weiterhin über Cloudflare DNS, **Proxy aktiviert**)
- **Cloudflare Proxy (orange Wolke) muss aktiviert sein** — nur so setzt
  Cloudflare Access den Auth-Header und der Traffic läuft durch die Firewall-Regeln
- Cloudflare Access: Application weiterhin auf `es-daskuechenhaus.de/*` mit
  dem gleichen Allow-Policy
- Es darf keine Cloudflare-Worker-Route mehr für `es-daskuechenhaus.de/*` oder
  `www.es-daskuechenhaus.de/*` existieren; beide Hostnames müssen über
  Cloudflare Access auf den Hetzner/Next.js-Origin zeigen.

### 9.4 Umgebungsvariablen auf Hetzner

```bash
# /etc/daskuechenhaus/crm.env
DKH_ADMIN_API_BASE_URL=https://daskuechenhaus.condata.io/_daskuechenhaus-admin-api
DKH_ADMIN_API_TOKEN=<secret>
NODE_ENV=production
PORT=3000
```

---

## Phase 10 — Migrationsreihenfolge (empfohlen)

Der frühere Parallelbetrieb mit dem Worker ist aufgehoben. Die Umsetzung zielt
direkt auf `apps/dkh-crm/` als einzige CRM-Oberfläche hinter
`es-daskuechenhaus.de`.

1. **Projekt & Auth** (Phase 1–2) — ca. 1 Tag
2. **API-Client & Typen** (Phase 3) — ca. 0.5 Tage
3. **Layout & Navigation** (Phase 5) — ca. 0.5 Tage
4. **Dashboard** (Phase 6) — ca. 1 Tag
5. **Aufgaben-Seite** — ca. 1 Tag
6. **E-Mail-Seite** — ca. 1 Tag
7. **Kunden-Seite** — ca. 2 Tage
8. **Kalender** (`/termine`) — ca. 2 Tage (`react-big-calendar` empfohlen)
9. **Admin-Seite** — ca. 1 Tag
10. **Cutover** — DNS/Cloudflare auf Hetzner/Next.js, keine Worker-Route, Monitoring

**Geschätzter Gesamtaufwand:** 10–12 Entwicklertage

---

## Was sich NICHT ändert

- **Hetzner Runtime-API** — alle Endpunkte bleiben unverändert
- **Cloudflare Access** — gleiche Application, gleiches Allow-Policy
- **PostgreSQL-Schema** — keine Datenbankänderungen
- **Audit-Pfad** (`communication_events`) — bleibt unverändert
- **Mailbox-Sync** (GitHub Action) — unverändert

---

## Schnellcheck: Was aus dem Worker direkt übernehmen?

| Worker-Code                 | Next.js-Äquivalent                                       |
|-----------------------------|----------------------------------------------------------|
| `accessEmail(request)`      | `await getUserEmail()` (liest `x-dkh-user-email`)        |
| `fetchOverviewState()`      | `fetchOverviewState()` in `dkh-api.ts`                   |
| `isToday()`, `isOverdue()`  | `src/lib/utils.ts` (identische Logik)                    |
| `formatDateTime()`          | `date-fns` `format()` mit `de` Locale                    |
| `truncateText()`            | `src/lib/utils.ts`                                       |
| `priorityLabel()`           | `src/lib/utils.ts`                                       |
| TypeScript-Interfaces       | 1:1 nach `src/lib/types.ts` kopieren                     |
| `CUSTOMER_SEARCH_SCRIPT`    | `public/customer-search.v1.js` (Such-URL anpassen)       |
| `renderStatusTile()`        | `<StatusCard>` Komponente                                |
| `renderHome()`              | `src/app/page.tsx` (Server Component)                    |
