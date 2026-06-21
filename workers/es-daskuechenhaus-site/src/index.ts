interface Env {
  DKH_ADMIN_API_BASE_URL: string;
  DKH_ADMIN_API_TOKEN: string;
}

type Role = {
  code: string;
  name: string;
};

type Workday = {
  weekday: number;
  is_working_day: boolean;
  morning_start_time: string | null;
  morning_end_time: string | null;
  afternoon_start_time: string | null;
  afternoon_end_time: string | null;
};

type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone: string | null;
  job_title: string | null;
  department: string | null;
  is_active: boolean;
  timezone: string;
  security: {
    mfa_required: boolean;
    password_login_enabled: boolean;
    external_identity_provider: string;
  };
  roles: string[];
  workdays: Workday[];
};

type CompanySettings = Record<string, string | undefined>;

type AdminState = {
  users: User[];
  roles: Role[];
  company_settings: CompanySettings;
  integrations: Array<{
    id: number;
    code: string;
    name: string;
    is_enabled: boolean;
    connections: Array<{
      id: number;
      display_name: string;
      status: string;
      secret_reference: string | null;
    }>;
  }>;
};

type OverviewState = {
  current_user: {
    primary_user_id: number | null;
    display_name: string;
    email: string;
    is_admin: boolean;
    user_ids: number[];
    delegated_user_ids: number[];
    scope_user_ids: number[];
  };
  users: Array<{
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    roles: string[];
  }>;
  task_statuses: Array<{
    code: string;
    name: string;
    is_terminal: boolean;
  }>;
  customer_cases: Array<{
    id: number;
    case_number: string | null;
    customer_display_name: string;
    customer_number: string | null;
    customer_email: string | null;
    status_phase: number | null;
  }>;
  tasks: Array<{
    id: number;
    title: string;
    description: string | null;
    status: string;
    status_name: string;
    priority: string;
    due_at: string | null;
    reminder_at: string | null;
    reminder_email_enabled: boolean;
    reminder_overview_enabled: boolean;
    case: {
      id: number;
      case_number: string | null;
      customer_display_name: string;
      status_phase: number | null;
    } | null;
    assigned_users: Array<{ id: number; name: string }>;
    attachment_count: number;
  }>;
  emails: Array<{
    id: number;
    subject: string;
    snippet: string | null;
    direction: string;
    received_at: string | null;
    is_unassigned: boolean;
    assigned_user_id: number | null;
    participants: Array<{
      type: string;
      display_name: string | null;
      email_address: string;
    }>;
    cases: Array<{
      id: number;
      case_number: string | null;
      customer_display_name: string;
    }>;
    suggestions: Array<{
      id: number;
      confidence: number;
      reason: string | null;
      case: {
        id: number;
        case_number: string | null;
        customer_display_name: string;
      } | null;
    }>;
  }>;
  appointments: Array<{
    id: number;
    title: string;
    starts_at: string;
    location: string | null;
    case: { id: number; customer_display_name: string } | null;
  }>;
  news_items: Array<{
    id: number;
    title: string;
    body: string | null;
    category: string;
    starts_on: string | null;
    ends_on: string | null;
  }>;
  goal_events: Array<{
    id: number;
    goal: string;
    note: string | null;
    achieved_at: string;
    achieved_by: string | null;
  }>;
  delegations: Array<{
    id: number;
    represented_user: string;
    starts_at: string;
    ends_at: string;
    scope: string;
  }>;
  communication_events?: Array<{
    id: number;
    event_type: string;
    title: string;
    body: string | null;
    occurred_at: string;
    customer_case: {
      id: number;
      case_number: string | null;
      customer_display_name: string;
    } | null;
    actor: string | null;
  }>;
};

type CustomerAddress = {
  street: string | null;
  house_number: string | null;
  address_extra: string | null;
  postal_code: string | null;
  city: string | null;
  country: string | null;
};

type CustomerRecord = {
  id: number;
  customer_number: string | null;
  customer_type: string;
  display_name: string;
  salutation: string | null;
  title: string | null;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  primary_email: string | null;
  primary_phone: string | null;
  primary_mobile: string | null;
  preferred_contact_channel: string;
  notes: string | null;
  owner_user_id: number | null;
  address: CustomerAddress | null;
  case_count: number;
  updated_at: string | null;
};

type CustomersState = {
  current_user: OverviewState["current_user"];
  users: OverviewState["users"];
  customers: CustomerRecord[];
  status_phases: Array<{
    phase: number;
    name: string;
    is_terminal: boolean;
  }>;
};

const EMPTY_STATE: AdminState = {
  users: [],
  roles: [
    { code: "admin", name: "Admin" },
    { code: "employee", name: "Mitarbeiter" },
    { code: "sales", name: "Verkauf" },
  ],
  company_settings: {},
  integrations: [],
};

const EMPTY_OVERVIEW_STATE: OverviewState = {
  current_user: {
    primary_user_id: null,
    display_name: "",
    email: "",
    is_admin: false,
    user_ids: [],
    delegated_user_ids: [],
    scope_user_ids: [],
  },
  users: [],
  task_statuses: [
    { code: "new", name: "Neu", is_terminal: false },
    { code: "planned", name: "Geplant", is_terminal: false },
    { code: "in_progress", name: "In Arbeit", is_terminal: false },
    { code: "waiting", name: "Wartet auf Rueckmeldung", is_terminal: false },
    { code: "done", name: "Erledigt", is_terminal: true },
    { code: "cancelled", name: "Abgebrochen", is_terminal: true },
  ],
  customer_cases: [],
  tasks: [],
  emails: [],
  appointments: [],
  news_items: [],
  goal_events: [],
  delegations: [],
  communication_events: [],
};

const EMPTY_CUSTOMERS_STATE: CustomersState = {
  current_user: EMPTY_OVERVIEW_STATE.current_user,
  users: [],
  customers: [],
  status_phases: [],
};

type TenantTheme = {
  background: string;
  surface: string;
  text: string;
  secondaryText: string;
  accent: string;
  border: string;
};

type TenantBrandAssets = {
  logoPath: string;
  logoRoute: string;
  logoMimeType: string;
  logoBody: string;
  faviconPath: string | null;
  appIconPath: string | null;
  assetScope: "tenant-owned";
};

type TenantUiProfile = {
  tenantId: "daskuechenhaus";
  displayName: string;
  experienceStandard: "sota-2026-tenant-crm";
  brandAssets: TenantBrandAssets;
  theme: TenantTheme;
};

const DKH_TENANT_UI: TenantUiProfile = {
  tenantId: "daskuechenhaus",
  displayName: "das kuechenhaus",
  experienceStandard: "sota-2026-tenant-crm",
  brandAssets: {
    logoPath: "assets/images/daskuechenhaus/logo_daskuechenhaus.png",
    logoRoute: "/tenant-assets/daskuechenhaus/logo.svg",
    logoMimeType: "image/svg+xml; charset=utf-8",
    logoBody:
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 88" role="img" aria-label="das kuechenhaus"><rect width="260" height="88" rx="8" fill="#fff"/><path d="M22 20h54v48H22z" fill="#76b726"/><path d="M33 31h32v8H33zm0 15h32v8H33z" fill="#fff"/><text x="92" y="38" fill="#111" font-family="Arial,sans-serif" font-size="18" font-weight="700">das</text><text x="92" y="62" fill="#111" font-family="Arial,sans-serif" font-size="24" font-weight="700">kuechenhaus</text></svg>',
    faviconPath: null,
    appIconPath: null,
    assetScope: "tenant-owned",
  },
  theme: {
    background: "#f4f7f1",
    surface: "#ffffff",
    text: "#111111",
    secondaryText: "#4f5b4a",
    accent: "#76b726",
    border: "#d8dfd4",
  },
};

const SECURITY_HEADERS: Record<string, string> = {
  "content-security-policy":
    "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
  "x-robots-tag": "noindex, nofollow, noarchive",
  "permissions-policy": "camera=(), microphone=(), geolocation=()",
  "cache-control": "no-store",
};

function htmlResponse(body: string, status = 200): Response {
  return new Response(body, {
    status,
    headers: {
      ...SECURITY_HEADERS,
      "content-type": "text/html; charset=utf-8",
    },
  });
}

function assetResponse(body: string, contentType: string): Response {
  return new Response(body, {
    headers: {
      ...SECURITY_HEADERS,
      "content-type": contentType,
      "cache-control": "public, max-age=3600",
    },
  });
}

function redirectResponse(location: string): Response {
  return new Response(null, {
    status: 303,
    headers: {
      ...SECURITY_HEADERS,
      location,
    },
  });
}

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function selectedAttribute(current: string | undefined, value: string): string {
  return current === value ? " selected" : "";
}

function accessEmail(request: Request): string {
  return (
    request.headers.get("cf-access-authenticated-user-email") ??
    request.headers.get("cf-access-user-email") ??
    ""
  );
}

function adminApiUrl(env: Env, path: string): string {
  return `${env.DKH_ADMIN_API_BASE_URL.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

function renderTenantThemeVars(profile: TenantUiProfile): string {
  return `--text: ${profile.theme.text};
      --muted: ${profile.theme.secondaryText};
      --line: ${profile.theme.border};
      --green: ${profile.theme.accent};
      --surface: ${profile.theme.surface};
      --band: ${profile.theme.background};`;
}

function renderTenantLogo(profile: TenantUiProfile): string {
  return `<img class="tenant-logo" src="${escapeHtml(profile.brandAssets.logoRoute)}" alt="${escapeHtml(profile.displayName)}">`;
}

function serveTenantAsset(pathname: string): Response | null {
  if (pathname !== DKH_TENANT_UI.brandAssets.logoRoute) {
    return null;
  }
  if (
    DKH_TENANT_UI.brandAssets.assetScope !== "tenant-owned" ||
    !DKH_TENANT_UI.brandAssets.logoPath.startsWith("assets/images/daskuechenhaus/")
  ) {
    return htmlResponse("<!doctype html><title>Nicht gefunden</title><h1>Nicht gefunden</h1>", 404);
  }
  return assetResponse(
    DKH_TENANT_UI.brandAssets.logoBody,
    DKH_TENANT_UI.brandAssets.logoMimeType,
  );
}

function parseDate(value: string | null): Date | null {
  if (!value) {
    return null;
  }
  const parsed = new Date(value.replace(" ", "T"));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDateTime(value: string | null): string {
  const parsed = parseDate(value);
  if (!parsed) {
    return value ?? "";
  }
  return new Intl.DateTimeFormat("de-DE", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function datetimeLocalValue(value: string | null): string {
  if (!value) {
    return "";
  }
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  return normalized.slice(0, 16);
}

function truncateText(value: string | null | undefined, maxLength: number): string {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}...`;
}

function priorityLabel(priority: string): string {
  const labels: Record<string, string> = {
    low: "Niedrig",
    normal: "Normal",
    high: "Hoch",
    urgent: "Dringend",
  };
  return labels[priority] ?? priority;
}

function priorityClass(priority: string): string {
  if (priority === "urgent") {
    return " danger";
  }
  if (priority === "high") {
    return " warning";
  }
  return "";
}

function isOverdue(value: string | null): boolean {
  const due = parseDate(value);
  return Boolean(due && due.getTime() < Date.now());
}

async function fetchAdminState(env: Env, request: Request): Promise<AdminState> {
  const response = await fetch(adminApiUrl(env, "/admin/state"), {
    headers: {
      "x-dkh-admin-api-token": env.DKH_ADMIN_API_TOKEN,
      "x-access-user-email": accessEmail(request),
    },
  });
  if (!response.ok) {
    return EMPTY_STATE;
  }
  return (await response.json()) as AdminState;
}

async function fetchOverviewState(env: Env, request: Request): Promise<OverviewState> {
  const response = await fetch(adminApiUrl(env, "/overview/state"), {
    headers: {
      "x-dkh-admin-api-token": env.DKH_ADMIN_API_TOKEN,
      "x-access-user-email": accessEmail(request),
    },
  });
  if (!response.ok) {
    return EMPTY_OVERVIEW_STATE;
  }
  return (await response.json()) as OverviewState;
}

async function fetchCustomersState(env: Env, request: Request): Promise<CustomersState> {
  const response = await fetch(adminApiUrl(env, "/customers/state"), {
    headers: {
      "x-dkh-admin-api-token": env.DKH_ADMIN_API_TOKEN,
      "x-access-user-email": accessEmail(request),
    },
  });
  if (!response.ok) {
    return EMPTY_CUSTOMERS_STATE;
  }
  return (await response.json()) as CustomersState;
}

async function proxyAdminApi(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const response = await fetch(adminApiUrl(env, url.pathname.replace(/^\/admin-api/, "/admin")), {
    method: request.method,
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/x-www-form-urlencoded",
      "x-dkh-admin-api-token": env.DKH_ADMIN_API_TOKEN,
      "x-access-user-email": accessEmail(request),
    },
    body: request.method === "GET" || request.method === "HEAD" ? null : request.body,
  });
  if (request.method !== "GET") {
    if (!response.ok) {
      return htmlResponse("<!doctype html><title>Fehler</title><h1>Speichern nicht moeglich</h1>", response.status);
    }
    return redirectResponse(url.searchParams.get("return_to") ?? "/admin.php?modal=users");
  }
  return new Response(response.body, {
    status: response.status,
    headers: {
      ...SECURITY_HEADERS,
      "content-type": response.headers.get("content-type") ?? "application/json; charset=utf-8",
    },
  });
}

async function proxyOverviewApi(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const response = await fetch(adminApiUrl(env, url.pathname.replace(/^\/overview-api/, "/overview")), {
    method: request.method,
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/x-www-form-urlencoded",
      "x-dkh-admin-api-token": env.DKH_ADMIN_API_TOKEN,
      "x-access-user-email": accessEmail(request),
    },
    body: request.method === "GET" || request.method === "HEAD" ? null : request.body,
  });
  if (request.method !== "GET") {
    if (!response.ok) {
      return htmlResponse("<!doctype html><title>Fehler</title><h1>Speichern nicht moeglich</h1>", response.status);
    }
    return redirectResponse(url.searchParams.get("return_to") ?? "/index.php");
  }
  return new Response(response.body, {
    status: response.status,
    headers: {
      ...SECURITY_HEADERS,
      "content-type": response.headers.get("content-type") ?? "application/json; charset=utf-8",
    },
  });
}

async function proxyCustomersApi(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const response = await fetch(adminApiUrl(env, url.pathname.replace(/^\/customers-api/, "/customers")), {
    method: request.method,
    headers: {
      "content-type": request.headers.get("content-type") ?? "application/x-www-form-urlencoded",
      "x-dkh-admin-api-token": env.DKH_ADMIN_API_TOKEN,
      "x-access-user-email": accessEmail(request),
    },
    body: request.method === "GET" || request.method === "HEAD" ? null : request.body,
  });
  if (request.method !== "GET") {
    if (!response.ok) {
      return htmlResponse("<!doctype html><title>Fehler</title><h1>Speichern nicht moeglich</h1>", response.status);
    }
    return redirectResponse(url.searchParams.get("return_to") ?? "/kunden.php");
  }
  return new Response(response.body, {
    status: response.status,
    headers: {
      ...SECURITY_HEADERS,
      "content-type": response.headers.get("content-type") ?? "application/json; charset=utf-8",
    },
  });
}

function renderSideNav(active: "overview" | "customers" | "tasks" | "emails" | "admin", isAdmin: boolean): string {
  return `<nav aria-label="Bereiche">
    <a href="/index.php"${active === "overview" ? ' aria-current="page"' : ""}>Uebersicht</a>
    <a href="/kunden.php"${active === "customers" ? ' aria-current="page"' : ""}>Kunden</a>
    <a href="/aufgaben.php"${active === "tasks" ? ' aria-current="page"' : ""}>Aufgaben</a>
    <a href="/emails.php"${active === "emails" ? ' aria-current="page"' : ""}>E-Mails</a>
    ${isAdmin ? `<a href="/admin.php"${active === "admin" ? ' aria-current="page"' : ""}>Admin Bereich</a>` : ""}
  </nav>`;
}

type NavTarget = "overview" | "customers" | "tasks" | "emails" | "admin";

function renderBottomNav(active: NavTarget): string {
  const items: Array<{ key: NavTarget; href: string; label: string; icon: string }> = [
    {
      key: "overview",
      href: "/index.php",
      label: "Steuerung",
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    },
    {
      key: "customers",
      href: "/kunden.php",
      label: "Kunden",
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/></svg>',
    },
    {
      key: "tasks",
      href: "/aufgaben.php",
      label: "Aufgaben",
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 11l3 3 8-8"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
    },
    {
      key: "emails",
      href: "/emails.php",
      label: "E-Mails",
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>',
    },
  ];
  return `<nav class="tab-bar" aria-label="Hauptbereiche">${items
    .map(
      (item) =>
        `<a href="${item.href}"${active === item.key ? ' aria-current="page"' : ""}>${item.icon}<span>${escapeHtml(item.label)}</span></a>`,
    )
    .join("")}</nav>`;
}

function renderFab(): string {
  return `<details class="fab">
    <summary aria-label="Schnellaktionen"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg></summary>
    <div class="fab-menu" aria-label="Schnellaktionen">
      <a href="/aufgaben.php#task-create">Aufgabe anlegen</a>
      <a href="/kunden.php?new=1">Kunde anlegen</a>
      <a href="/kunden.php">Kunde suchen</a>
    </div>
  </details>`;
}

function renderChromeStyles(): string {
  return `
    .tab-bar {
      position: fixed;
      inset: auto 0 0 0;
      z-index: 20;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      background: var(--surface);
      border-top: 1px solid var(--line);
      padding-bottom: env(safe-area-inset-bottom);
      box-shadow: 0 -4px 16px rgba(24, 38, 18, 0.10);
    }
    .tab-bar a {
      display: grid;
      gap: 3px;
      justify-items: center;
      align-content: center;
      min-height: 56px;
      padding: 7px 4px;
      color: var(--muted);
      font-size: 0.7rem;
      font-weight: 700;
      text-decoration: none;
    }
    .tab-bar a span { line-height: 1; }
    .tab-bar a svg { width: 24px; height: 24px; }
    .tab-bar a[aria-current="page"] { color: var(--green-dark); }
    .fab {
      position: fixed;
      right: clamp(14px, 4vw, 22px);
      bottom: calc(76px + env(safe-area-inset-bottom));
      z-index: 25;
    }
    .fab > summary {
      list-style: none;
      display: grid;
      place-items: center;
      width: 56px;
      height: 56px;
      border-radius: 999px;
      background: var(--green);
      color: #102000;
      cursor: pointer;
      box-shadow: 0 10px 24px rgba(24, 38, 18, 0.28);
      transition: transform 140ms ease, background 140ms ease;
    }
    .fab > summary::-webkit-details-marker { display: none; }
    .fab > summary svg { width: 26px; height: 26px; }
    .fab[open] > summary {
      background: var(--green-dark);
      color: #ffffff;
      transform: rotate(45deg);
    }
    .fab-menu {
      position: absolute;
      right: 0;
      bottom: 68px;
      display: grid;
      gap: 8px;
      min-width: 210px;
    }
    .fab-menu a {
      display: flex;
      align-items: center;
      min-height: 48px;
      padding: 11px 14px;
      border-radius: 10px;
      background: var(--surface);
      border: 1px solid var(--line);
      color: var(--text);
      font-weight: 700;
      text-decoration: none;
      box-shadow: 0 8px 20px rgba(24, 38, 18, 0.14);
    }
    @media (min-width: 768px) {
      .tab-bar { display: none; }
      .fab { display: none; }
    }
  `;
}

type CommandCenterMetrics = {
  overdueTasks: number;
  unassignedEmails: number;
  activeCases: number;
};

function isToday(value: string | null): boolean {
  const parsed = parseDate(value);
  if (!parsed) {
    return false;
  }
  const now = new Date();
  return (
    parsed.getFullYear() === now.getFullYear() &&
    parsed.getMonth() === now.getMonth() &&
    parsed.getDate() === now.getDate()
  );
}

function renderCockpitList(items: string[], emptyText: string): string {
  if (items.length === 0) {
    return `<div class="empty">${escapeHtml(emptyText)}</div>`;
  }
  return `<ul class="cockpit-list">${items.map((item) => `<li>${item}</li>`).join("")}</ul>`;
}

function renderCommandCenter(
  metrics: CommandCenterMetrics,
): string {
  return `<section class="command-center" aria-label="Command Center">
    <form class="command-search" action="/kunden.php" method="get">
      <label for="command-search">Suche</label>
      <input id="command-search" name="q" type="search" autocomplete="off" placeholder="Kunde, Vorgang, E-Mail oder Aufgabe suchen">
      <button type="submit">Suchen</button>
    </form>
    <div class="command-actions" aria-label="Schnellaktionen">
      <a href="/aufgaben.php">Aufgaben <span>${metrics.overdueTasks} ueberfaellig</span></a>
      <a href="/emails.php">E-Mails <span>${metrics.unassignedEmails} ohne Vorgang</span></a>
      <a href="/kunden.php">Vorgaenge <span>${metrics.activeCases} aktiv</span></a>
    </div>
  </section>`;
}

function renderCockpitTasks(state: OverviewState): string {
  const relevantTasks = [...state.tasks]
    .sort((left, right) => {
      const leftTime = parseDate(left.due_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
      const rightTime = parseDate(right.due_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
      return leftTime - rightTime;
    })
    .slice(0, 5);
  return renderCockpitList(
    relevantTasks.map((task) => {
      const assigned = task.assigned_users.map((user) => user.name).join(", ") || "ohne Zustaendigen";
      const caseLabel = task.case?.customer_display_name ?? "ohne Vorgang";
      const dueLabel = task.due_at ? ` · ${formatDateTime(task.due_at)}` : "";
      return `<a href="/aufgaben.php">${escapeHtml(task.title)}</a><span>${escapeHtml(caseLabel)} · ${escapeHtml(assigned)}${escapeHtml(dueLabel)}</span>`;
    }),
    "Keine offenen Aufgaben in deiner aktuellen Ansicht.",
  );
}

function renderCockpitEmails(state: OverviewState): string {
  const relevantEmails = [...state.emails]
    .sort((left, right) => {
      const leftTime = parseDate(left.received_at)?.getTime() ?? 0;
      const rightTime = parseDate(right.received_at)?.getTime() ?? 0;
      return rightTime - leftTime;
    })
    .slice(0, 5);
  return renderCockpitList(
    relevantEmails.map((email) => {
      const sender =
        email.participants.find((participant) => participant.type === "from") ??
        email.participants[0];
      const fit = email.suggestions[0]?.case;
      const assignment = email.is_unassigned
        ? fit
          ? `Vorschlag: wahrscheinlich ${fit.case_number ? `${fit.case_number} · ` : ""}${fit.customer_display_name}`
          : "Kein Treffer: Vorgang suchen und bestaetigen"
        : email.cases.map((entry) => entry.customer_display_name).join(", ") || "zugeordnet";
      return `<a href="/emails.php">${escapeHtml(email.subject || "(ohne Betreff)")}</a><span>${escapeHtml(sender?.display_name || sender?.email_address || "Unbekannt")} · ${escapeHtml(assignment)}</span>`;
    }),
    "Keine neuen E-Mail-Eingaenge in deiner aktuellen Ansicht.",
  );
}

function renderCapacity(state: OverviewState): string {
  const loads = new Map<string, number>();
  for (const task of state.tasks) {
    if (task.assigned_users.length === 0) {
      loads.set("Ohne Zustaendigen", (loads.get("Ohne Zustaendigen") ?? 0) + 1);
    }
    for (const user of task.assigned_users) {
      loads.set(user.name, (loads.get(user.name) ?? 0) + 1);
    }
  }
  return renderCockpitList(
    [...loads.entries()]
      .sort((left, right) => right[1] - left[1])
      .slice(0, 6)
      .map(([name, count]) => `<a href="/aufgaben.php">${escapeHtml(name)}</a><span>${count} offene Aufgaben</span>`),
    "Keine Aufgabenlast in der aktuellen Ansicht.",
  );
}

type DecisionItem = {
  urgency: "critical" | "warning" | "normal";
  label: string;
  title: string;
  meta: string;
  href: string;
  action: string;
};

function renderDecisionQueue(items: DecisionItem[]): string {
  if (items.length === 0) {
    return '<div class="empty">Keine offenen Entscheidungen in deiner aktuellen Ansicht.</div>';
  }
  return `<div class="decision-list">${items
    .slice(0, 9)
    .map(
      (item) => `<a class="decision-row ${item.urgency}" href="${escapeHtml(item.href)}">
        <span class="decision-marker" aria-hidden="true"></span>
        <span class="decision-copy">
          <span class="decision-label">${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.title)}</strong>
          <small>${escapeHtml(item.meta)}</small>
        </span>
        <span class="decision-action">${escapeHtml(item.action)}</span>
      </a>`,
    )
    .join("")}</div>`;
}

function renderCustomerFocus(state: OverviewState): string {
  if (state.customer_cases.length === 0) {
    return '<div class="empty">Noch keine aktiven Kundenvorgaenge sichtbar.</div>';
  }
  return `<div class="data-table customer-focus">
    <div class="data-row data-head"><span>Vorgang</span><span>Kunde</span><span>Phase</span><span>Naechste Aktion</span></div>
    ${state.customer_cases
      .slice(0, 7)
      .map((customerCase) => {
        const relatedTasks = state.tasks.filter((task) => task.case?.id === customerCase.id);
        const nextTask = [...relatedTasks].sort((left, right) => {
          const leftTime = parseDate(left.due_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
          const rightTime = parseDate(right.due_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
          return leftTime - rightTime;
        })[0];
        const phase = customerCase.status_phase ? `Phase ${customerCase.status_phase}` : "offen";
        const nextStep = nextTask
          ? `${nextTask.title}${nextTask.due_at ? ` (${formatDateTime(nextTask.due_at)})` : ""}`
          : "Naechste Aktion anlegen";
        return `<a class="data-row" href="/kunden.php">
          <span data-label="Vorgang">${escapeHtml(customerCase.case_number ?? "-")}</span>
          <strong>${escapeHtml(customerCase.customer_display_name)}</strong>
          <span data-label="Phase">${escapeHtml(phase)}</span>
          <span data-label="Naechste Aktion">${escapeHtml(truncateText(nextStep, 84))}</span>
        </a>`;
      })
      .join("")}
  </div>`;
}

function renderAuditTrail(state: OverviewState): string {
  const events = (state.communication_events ?? []).slice(0, 8);
  if (events.length === 0) {
    return '<div class="empty">Noch kein Audit-Trail fuer sichtbare Vorgaenge vorhanden.</div>';
  }
  return `<ol class="audit-list">${events
    .map((event) => {
      const caseLabel = event.customer_case
        ? `${event.customer_case.case_number ? `${event.customer_case.case_number} · ` : ""}${event.customer_case.customer_display_name}`
        : "ohne Vorgang";
      return `<li>
        <time>${escapeHtml(formatDateTime(event.occurred_at))}</time>
        <strong>${escapeHtml(event.title)}</strong>
        <span>${escapeHtml(caseLabel)} · ${escapeHtml(event.actor ?? "System")}</span>
      </li>`;
    })
    .join("")}</ol>`;
}

function renderHome(state: OverviewState): string {
  const overdueTasks = state.tasks.filter((task) => isOverdue(task.due_at)).length;
  const unassignedEmails = state.emails.filter((email) => email.is_unassigned).length;
  const tasksWithoutAssignee = state.tasks.filter((task) => task.assigned_users.length === 0).length;
  const urgentTasks = state.tasks.filter((task) => task.priority === "urgent").length;
  const todayTasks = state.tasks.filter((task) => isToday(task.due_at)).length;
  const todayAppointments = state.appointments.filter((appointment) => isToday(appointment.starts_at)).length;
  const emailsWithSuggestions = state.emails.filter((email) => email.is_unassigned && email.suggestions.length > 0).length;
  const hasRed = overdueTasks > 0 || urgentTasks > 0 || tasksWithoutAssignee > 0;
  const hasYellow = unassignedEmails > 0 || state.customer_cases.length === 0 || todayTasks > 0 || todayAppointments > 0;
  const overall = hasRed ? "Sofort handeln" : hasYellow ? "Heute steuern" : "Stabil";
  const decisionItems: DecisionItem[] = [
    ...state.tasks
      .filter((task) => isOverdue(task.due_at) || task.priority === "urgent" || task.assigned_users.length === 0)
      .map((task) => ({
        urgency: isOverdue(task.due_at) || task.priority === "urgent" ? "critical" as const : "warning" as const,
        label: task.assigned_users.length === 0 ? "Zustaendigkeit" : "Aufgabe",
        title: task.title,
        meta: `${task.case?.customer_display_name ?? "ohne Vorgang"} · ${task.assigned_users.map((user) => user.name).join(", ") || "nicht zugeordnet"}${task.due_at ? ` · ${formatDateTime(task.due_at)}` : ""}`,
        href: "/aufgaben.php",
        action: task.assigned_users.length === 0 ? "zuweisen" : "bearbeiten",
      })),
    ...state.emails
      .filter((email) => email.is_unassigned)
      .map((email) => {
        const sender = email.participants.find((participant) => participant.type === "from") ?? email.participants[0];
        const fit = email.suggestions[0]?.case;
        return {
          urgency: email.suggestions.length > 0 ? "warning" as const : "normal" as const,
          label: "E-Mail",
          title: email.subject || "(ohne Betreff)",
          meta: `${sender?.display_name || sender?.email_address || "Unbekannt"} · ${fit ? `Vorschlag: ${fit.customer_display_name}` : "Vorgang manuell suchen"}`,
          href: "/emails.php",
          action: "zuordnen",
        };
      }),
  ];
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="tenant-id" content="${escapeHtml(DKH_TENANT_UI.tenantId)}">
  <meta name="experience-standard" content="${escapeHtml(DKH_TENANT_UI.experienceStandard)}">
  <title>Uebersicht | ${escapeHtml(DKH_TENANT_UI.displayName)}</title>
  <style>
    ${renderChromeStyles()}
    :root {
      color-scheme: light;
      ${renderTenantThemeVars(DKH_TENANT_UI)}
      --line-strong: #c1cbb9;
      --green-dark: #34591b;
      --soft: #eef6e8;
      --warning: #9a5b00;
      --warning-bg: #fff6df;
      --danger: #9b1c1c;
      --danger-bg: #fff0f0;
      --ok: #276738;
      --ok-bg: #edf8ef;
      --ink-soft: #263326;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--band);
      padding-bottom: calc(64px + env(safe-area-inset-bottom));
    }
    .shell {
      min-height: 100vh;
    }
    aside {
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      padding: 12px 18px;
    }
    .tenant-logo {
      display: block;
      width: min(58%, 208px);
      height: auto;
      aspect-ratio: 260 / 88;
      margin-bottom: 0;
    }
    aside nav {
      display: none;
      gap: 8px;
    }
    aside nav a {
      color: var(--text);
      text-decoration: none;
      padding: 11px 12px;
      border-left: 3px solid transparent;
    }
    aside nav a:hover {
      background: #f6f8f4;
    }
    aside nav a[aria-current="page"] {
      border-left-color: var(--green);
      background: var(--soft);
      font-weight: 700;
    }
    main {
      padding: clamp(16px, 4vw, 24px) clamp(14px, 4vw, 30px) 32px;
      min-width: 0;
    }
    .topline {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    .badge {
      border: 1px solid #abc98f;
      background: #eef8e7;
      color: var(--green-dark);
      padding: 6px 10px;
      font-size: 0.85rem;
      font-weight: 700;
    }
    h1 {
      margin: 0;
      font-size: clamp(1.4rem, 5vw, 1.8rem);
      line-height: 1.1;
      letter-spacing: 0;
    }
    .lede {
      max-width: 920px;
      color: var(--muted);
      font-size: 0.95rem;
      line-height: 1.45;
      margin: 8px 0 0;
    }
    .command-center {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      align-items: stretch;
      margin: 14px 0 18px;
    }
    .command-search,
    .command-actions {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
    }
    .command-search {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      align-items: center;
      padding: 8px;
    }
    .command-search label {
      color: var(--green-dark);
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .command-search input {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
    }
    .command-search button {
      border: 0;
      border-radius: 6px;
      background: var(--green);
      color: #fff;
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      padding: 10px 12px;
    }
    .command-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1px;
      overflow: hidden;
    }
    .command-actions a {
      display: grid;
      gap: 2px;
      color: var(--text);
      padding: 9px 10px;
      text-decoration: none;
      background: #fbfcfa;
      min-width: 0;
    }
    .command-actions a:hover {
      background: var(--soft);
    }
    .command-actions span {
      color: var(--muted);
      font-size: 0.78rem;
      line-height: 1.35;
    }
    .status-strip {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin: 18px 0;
    }
    .status-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      min-height: 74px;
    }
    .status-card.red {
      border-color: #e2b8b8;
      background: var(--danger-bg);
    }
    .status-card.yellow {
      border-color: #e0c48d;
      background: var(--warning-bg);
    }
    .status-card.green {
      border-color: #bad7bf;
      background: var(--ok-bg);
    }
    .metric {
      font-size: clamp(1.35rem, 5vw, 1.55rem);
      font-weight: 800;
      line-height: 1.1;
    }
    .metric-label,
    .metric-sub,
    .risk-copy small,
    .command-link span,
    .cockpit-list span,
    .muted {
      color: var(--muted);
      line-height: 1.45;
    }
    .operations-board {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
      margin-bottom: 16px;
      align-items: stretch;
    }
    .board-section {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }
    .board-section.primary {
      border-color: ${hasRed ? "#d79a9a" : hasYellow ? "#d7b66f" : "#a9cfb0"};
    }
    .decision-list {
      display: grid;
      gap: 6px;
      margin-top: 12px;
    }
    .decision-row {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr);
      gap: 10px;
      align-items: center;
      padding: 10px;
      color: var(--text);
      text-decoration: none;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--surface);
      transition: transform 100ms ease, box-shadow 120ms ease, border-color 120ms ease;
    }
    .decision-row:hover {
      transform: translateY(-1px);
      box-shadow: 0 8px 20px rgba(24, 38, 18, 0.08);
    }
    .decision-row:active {
      transform: translateY(0);
      box-shadow: none;
    }
    .decision-row.critical { border-left: 4px solid var(--danger); }
    .decision-row.warning { border-left: 4px solid #c77c12; }
    .decision-row.normal { border-left: 4px solid var(--ok); }
    .decision-marker {
      width: 13px;
      height: 13px;
      border-radius: 999px;
    }
    .critical .decision-marker { background: var(--danger); }
    .warning .decision-marker { background: #c77c12; }
    .normal .decision-marker { background: var(--ok); }
    .decision-copy,
    .decision-copy strong,
    .decision-copy small,
    .decision-label {
      display: block;
    }
    .decision-label {
      color: var(--muted);
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .decision-copy strong {
      margin-top: 2px;
      font-size: 0.98rem;
      line-height: 1.25;
    }
    .decision-copy small {
      margin-top: 3px;
      font-size: 0.82rem;
      color: var(--muted);
    }
    .decision-action {
      color: var(--green-dark);
      font-size: 0.8rem;
      font-weight: 800;
      grid-column: 2;
      white-space: normal;
    }
    .cockpit-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
      align-items: start;
    }
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }
    .panel.wide {
      grid-column: 1 / -1;
    }
    .panel-split {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }
    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 10px;
    }
    .data-table {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #ffffff;
    }
    .data-row {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      align-items: center;
      color: var(--text);
      padding: 10px 12px;
      text-decoration: none;
      border-bottom: 1px solid var(--line);
    }
    .data-row:last-child { border-bottom: 0; }
    .data-row:hover { background: #f8fbf5; }
    .data-head {
      display: none;
      background: var(--soft);
      color: var(--green-dark);
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .data-row span[data-label]::before {
      content: attr(data-label) ": ";
      color: var(--muted);
      font-weight: 700;
    }
    .audit-list {
      display: grid;
      gap: 0;
      margin: 0;
      padding: 0;
      list-style: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .audit-list li {
      display: grid;
      grid-template-columns: 1fr;
      gap: 6px;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }
    .audit-list li:last-child { border-bottom: 0; }
    .audit-list time,
    .audit-list span {
      color: var(--muted);
      font-size: 0.84rem;
    }
    h2 {
      margin: 0;
      font-size: 1rem;
      letter-spacing: 0;
    }
    .section-kicker {
      color: var(--muted);
      font-size: 0.75rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .panel-link {
      color: var(--green-dark);
      font-size: 0.82rem;
      font-weight: 800;
      text-decoration: none;
      white-space: nowrap;
    }
    .panel-link:hover {
      text-decoration: underline;
    }
    .cockpit-list {
      display: grid;
      gap: 8px;
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .cockpit-list li {
      display: grid;
      gap: 3px;
      padding: 9px 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fbfcfa;
    }
    .cockpit-list a {
      color: var(--text);
      font-weight: 800;
      text-decoration: none;
      overflow-wrap: anywhere;
    }
    .cockpit-list a:hover {
      color: var(--green-dark);
      text-decoration: underline;
    }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 14px;
      color: var(--muted);
      background: #fbfcfa;
    }
    .list {
      display: grid;
      gap: 8px;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      background: #ffffff;
    }
    .item-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }
    .item-top h3 {
      margin: 0;
      font-size: 0.92rem;
      letter-spacing: 0;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      border: 1px solid #abc98f;
      background: var(--soft);
      color: var(--green-dark);
      font-size: 0.75rem;
      font-weight: 800;
      padding: 3px 7px;
      white-space: nowrap;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 7px;
      color: var(--muted);
      font-size: 0.8rem;
    }
    .preview {
      margin: 7px 0 0;
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.38;
    }
    .quick-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 9px;
      margin-top: 18px;
    }
    .ui-button {
      border: 1px solid #75a83b;
      background: var(--green);
      color: #111111;
      border-radius: 6px;
      padding: 9px 13px;
      min-height: 48px;
      display: inline-flex;
      align-items: center;
      font-weight: 800;
      text-decoration: none;
      cursor: pointer;
      width: fit-content;
      transition: transform 120ms ease, filter 120ms ease, box-shadow 120ms ease;
    }
    .ui-button.secondary {
      background: #ffffff;
      color: var(--green-dark);
    }
    .ui-button:hover {
      filter: brightness(0.96);
      box-shadow: 0 2px 0 rgba(52, 89, 27, 0.2);
    }
    .ui-button:active {
      transform: translateY(1px);
      box-shadow: none;
    }
    @media (min-width: 768px) {
      body { padding-bottom: 0; }
      .shell { display: grid; grid-template-columns: 252px minmax(0, 1fr); }
      aside { border-right: 1px solid var(--line); border-bottom: 0; padding: 24px 18px; }
      aside nav { display: grid; }
      .tenant-logo { width: min(100%, 208px); margin-bottom: 28px; }
      .topline { flex-direction: row; align-items: center; }
      .command-center { grid-template-columns: minmax(280px, 1fr) minmax(280px, 1.1fr); }
      .command-search { grid-template-columns: auto minmax(0, 1fr) auto; }
      .command-actions { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .status-strip { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .cockpit-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .panel-split { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .decision-row { grid-template-columns: auto minmax(0, 1fr) auto; }
      .decision-action { grid-column: auto; white-space: nowrap; }
      .data-head { display: grid; }
      .data-row span[data-label]::before { content: none; }
      .data-row { grid-template-columns: minmax(90px, 0.55fr) minmax(140px, 0.95fr) minmax(70px, 0.45fr) minmax(180px, 1.2fr); }
      .audit-list li { grid-template-columns: 150px minmax(170px, 0.8fr) minmax(220px, 1fr); }
    }
    @media (min-width: 1100px) {
      .status-strip { grid-template-columns: repeat(5, minmax(128px, 1fr)); }
      .operations-board { grid-template-columns: minmax(0, 1.35fr) minmax(330px, 0.65fr); }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      ${renderTenantLogo(DKH_TENANT_UI)}
      ${renderSideNav("overview", state.current_user.is_admin)}
    </aside>
    <main>
      <div class="topline">
        <div>
          <h1>Steuerung</h1>
        </div>
        <span class="badge">${escapeHtml(overall)}</span>
      </div>
      ${renderCommandCenter({
        overdueTasks,
        unassignedEmails,
        activeCases: state.customer_cases.length,
      })}
      <div class="status-strip">
        <div class="status-card ${hasRed ? "red" : hasYellow ? "yellow" : "green"}">
          <div class="metric">${escapeHtml(overall)}</div>
          <div class="metric-label">Prioritaet</div>
          <div class="metric-sub">${escapeHtml(overall)}</div>
        </div>
        <div class="status-card${overdueTasks > 0 ? " red" : ""}"><div class="metric">${state.tasks.length}</div><div class="metric-label">offene Aufgaben</div><div class="metric-sub">${overdueTasks} ueberfaellig · ${urgentTasks} dringend</div></div>
        <div class="status-card${unassignedEmails > 0 ? " yellow" : ""}"><div class="metric">${state.emails.length}</div><div class="metric-label">E-Mail Eingang</div><div class="metric-sub">${unassignedEmails} ohne Vorgang · ${emailsWithSuggestions} Zuordnungsvorschlaege</div></div>
        <div class="status-card"><div class="metric">${state.customer_cases.length}</div><div class="metric-label">aktive Vorgaenge</div><div class="metric-sub">Kundenarbeit im Blick</div></div>
        <div class="status-card"><div class="metric">${todayAppointments}</div><div class="metric-label">Termine heute</div><div class="metric-sub">${todayTasks} Aufgaben faellig</div></div>
      </div>
      <section class="operations-board" aria-label="CRM Entscheidungszentrale">
        <div class="board-section primary">
          <div class="panel-head"><div><h2>Jetzt bearbeiten</h2></div><a class="panel-link" href="/aufgaben.php">Arbeitsebene</a></div>
          ${renderDecisionQueue(decisionItems)}
        </div>
      </section>
      <div class="cockpit-grid">
        <section class="panel">
          <div class="panel-head"><div><h2>Aktive Vorgaenge steuern</h2></div><a class="panel-link" href="/kunden.php">Kunden</a></div>
          ${renderCustomerFocus(state)}
        </section>
        <section class="panel">
          <div class="panel-head"><div><h2>Team, Auslastung und Termine</h2></div><a class="panel-link" href="/aufgaben.php">Details</a></div>
          ${renderCapacity(state)}
          <div style="margin-top:10px">${renderOverviewDelegations(state)}</div>
          ${renderOverviewAppointments(state)}
          <div style="margin-top:10px">${renderOverviewNews(state)}</div>
        </section>
        <section class="panel">
          <div class="panel-head"><div><h2>Faellige Aufgaben</h2></div><a class="panel-link" href="/aufgaben.php">Oeffnen</a></div>
          ${renderCockpitTasks(state)}
        </section>
        <section class="panel">
          <div class="panel-head"><div><h2>E-Mail-Eingang und Zuordnung</h2></div><a class="panel-link" href="/emails.php">Oeffnen</a></div>
          ${renderCockpitEmails(state)}
        </section>
        <section class="panel wide">
          <div class="panel-head"><div><h2>Nachvollziehbare Aenderungen</h2></div><a class="panel-link" href="/kunden.php">Kundenmappe</a></div>
          ${renderAuditTrail(state)}
        </section>
      </div>
      <div class="quick-actions">
        <a class="ui-button" href="/kunden.php">Kunde anlegen</a>
        <a class="ui-button secondary" href="/aufgaben.php">Aufgabe anlegen</a>
        <a class="ui-button secondary" href="/emails.php">E-Mails zuordnen</a>
      </div>
    </main>
  </div>
  ${renderFab()}
  ${renderBottomNav("overview")}
</body>
</html>`;
}

function renderOverviewTasks(state: OverviewState, returnTo = "/index.php"): string {
  if (state.tasks.length === 0) {
    return '<div class="empty">Keine offenen Aufgaben in deiner aktuellen Ansicht.</div>';
  }
  const visibleTasks = [...state.tasks]
    .sort((left, right) => {
      const leftTime = parseDate(left.due_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
      const rightTime = parseDate(right.due_at)?.getTime() ?? Number.MAX_SAFE_INTEGER;
      return leftTime - rightTime;
    })
    .slice(0, 8);
  const hiddenCount = Math.max(0, state.tasks.length - visibleTasks.length);
  return `<div class="list">${visibleTasks
    .map((task) => {
      const assigned = task.assigned_users.map((user) => user.name).join(", ") || "nicht zugeordnet";
      const caseLabel = task.case
        ? `${task.case.case_number ? `${task.case.case_number} · ` : ""}${task.case.customer_display_name}`
        : "ohne Vorgang";
      const dueLabel = task.due_at ? formatDateTime(task.due_at) : "";
      const isLate = isOverdue(task.due_at);
      const itemClass = task.priority === "urgent" ? " urgent" : task.priority === "high" ? " high" : "";
      return `<article class="item${itemClass}">
        <div class="item-top">
          <h3>${escapeHtml(truncateText(task.title, 96))}</h3>
          <span class="pill${priorityClass(task.priority)}">${escapeHtml(priorityLabel(task.priority))}</span>
        </div>
        ${task.description ? `<p class="preview">${escapeHtml(truncateText(task.description, 170))}</p>` : ""}
        <div class="meta">
          <span>${escapeHtml(task.status_name)}</span>
          <span>${escapeHtml(assigned)}</span>
          <span>${escapeHtml(caseLabel)}</span>
          ${dueLabel ? `<span>${isLate ? "Ueberfaellig" : "Faellig"}: ${escapeHtml(dueLabel)}</span>` : ""}
          ${task.attachment_count > 0 ? `<span>${task.attachment_count} Anlagen</span>` : ""}
        </div>
        <div class="item-actions">
          <form class="inline-form" method="post" action="/overview-api/tasks/${task.id}/archive?return_to=${escapeHtml(returnTo)}">
            <button class="ui-button secondary" type="submit">Archivieren</button>
          </form>
          <form class="inline-form" method="post" action="/overview-api/tasks/${task.id}/delete?return_to=${escapeHtml(returnTo)}">
            <button class="ui-button danger" type="submit">In Papierkorb</button>
          </form>
        </div>
        <details class="editor">
          <summary>Bearbeiten</summary>
          ${renderTaskEditForm(task, state, returnTo)}
        </details>
      </article>`;
    })
    .join("")}</div>${hiddenCount > 0 ? `<div class="more-note">+ ${hiddenCount} weitere Aufgaben</div>` : ""}`;
}

function renderOverviewEmails(state: OverviewState, returnTo = "/index.php"): string {
  if (state.emails.length === 0) {
    return '<div class="empty">Keine E-Mail-Eingaenge in deiner aktuellen Ansicht.</div>';
  }
  const visibleEmails = [...state.emails]
    .sort((left, right) => {
      const leftTime = parseDate(left.received_at)?.getTime() ?? 0;
      const rightTime = parseDate(right.received_at)?.getTime() ?? 0;
      return rightTime - leftTime;
    })
    .slice(0, 10);
  const hiddenCount = Math.max(0, state.emails.length - visibleEmails.length);
  return `<div class="list">${visibleEmails
    .map((email) => {
      const sender =
        email.participants.find((participant) => participant.type === "from") ??
        email.participants[0];
      const caseLabel =
        email.cases.map((entry) => `${entry.case_number ? `${entry.case_number} · ` : ""}${entry.customer_display_name}`).join(", ") ||
        "";
      return `<article class="item compact">
        <div class="item-top">
          <h3>${escapeHtml(truncateText(email.subject || "(ohne Betreff)", 88))}</h3>
          <span class="pill${email.is_unassigned ? " warning" : ""}">${email.is_unassigned ? "zuordnen" : "zugeordnet"}</span>
        </div>
        <div class="meta">
          ${sender ? `<span>${escapeHtml(sender.display_name || sender.email_address)}</span>` : ""}
          ${email.received_at ? `<span>${escapeHtml(formatDateTime(email.received_at))}</span>` : ""}
          ${caseLabel ? `<span>${escapeHtml(caseLabel)}</span>` : ""}
        </div>
        ${email.snippet ? `<p class="preview">${escapeHtml(truncateText(email.snippet, 150))}</p>` : ""}
        ${renderEmailSuggestions(email, returnTo)}
        ${email.is_unassigned ? renderEmailAssignmentForm(email, returnTo) : ""}
        <div class="item-actions">
          <form class="inline-form" method="post" action="/overview-api/emails/${email.id}/archive?return_to=${escapeHtml(returnTo)}">
            <button class="ui-button secondary" type="submit">Archivieren</button>
          </form>
          <form class="inline-form" method="post" action="/overview-api/emails/${email.id}/delete?return_to=${escapeHtml(returnTo)}">
            <button class="ui-button danger" type="submit">In Papierkorb</button>
          </form>
        </div>
      </article>`;
    })
    .join("")}</div>${hiddenCount > 0 ? `<div class="more-note">+ ${hiddenCount} weitere E-Mails</div>` : ""}`;
}

function renderEmailSuggestions(email: OverviewState["emails"][number], returnTo = "/index.php"): string {
  if (email.suggestions.length === 0) {
    return "";
  }
  return `<div class="list">${email.suggestions
    .map((suggestion) => {
      const suggestedCase = suggestion.case;
      const confidence = Math.round(Number(suggestion.confidence) * 100);
      return `<div class="item compact">
        <div class="item-top">
          <h3>${suggestedCase ? escapeHtml(`${suggestedCase.case_number ? `${suggestedCase.case_number} · ` : ""}${suggestedCase.customer_display_name}`) : "Kein Vorgang"}</h3>
          <span class="pill warning">${confidence}% Vorschlag</span>
        </div>
        ${suggestion.reason ? `<p class="preview">${escapeHtml(truncateText(suggestion.reason, 120))}</p>` : ""}
        <div class="item-actions">
          <form class="inline-form" method="post" action="/overview-api/emails/suggestions/${suggestion.id}/accept?return_to=${escapeHtml(returnTo)}">
            <button class="ui-button" type="submit">Zuordnung bestaetigen</button>
          </form>
        </div>
      </div>`;
    })
    .join("")}</div>`;
}

function renderEmailAssignmentForm(email: OverviewState["emails"][number], returnTo = "/index.php"): string {
  const noSuggestionHint = email.suggestions.length === 0
    ? '<p class="field-hint">Kein Treffer: Vorgang suchen, auswaehlen und bestaetigen.</p>'
    : "";
  return `<form method="post" action="/overview-api/emails/assign?return_to=${escapeHtml(returnTo)}">
    <input name="email_message_id" type="hidden" value="${email.id}">
    <div class="form-grid">
      <label>Vorgang suchen
        <input name="customer_case_search" list="customer-case-options" type="search" required autocomplete="off" placeholder="Name, Vorgangs-Nr., Kundennr.">
      </label>
      ${noSuggestionHint}
    </div>
    <button class="ui-button" type="submit">E-Mail zuordnen</button>
  </form>`;
}

function customerCaseOptionValue(customerCase: OverviewState["customer_cases"][number]): string {
  const parts = [
    customerCase.case_number,
    customerCase.customer_number,
    customerCase.customer_display_name,
    customerCase.customer_email,
  ].filter(Boolean);
  return `${parts.join(" · ")} [id:${customerCase.id}]`;
}

function renderCustomerCaseDatalist(state: OverviewState): string {
  return `<datalist id="customer-case-options">
    ${state.customer_cases
      .map(
        (customerCase) =>
          `<option value="${escapeHtml(customerCaseOptionValue(customerCase))}"></option>`,
      )
      .join("")}
  </datalist>`;
}

function renderTaskEditForm(task: OverviewState["tasks"][number], state: OverviewState, returnTo = "/index.php"): string {
  const assignedUserId = task.assigned_users[0]?.id ?? state.current_user.primary_user_id ?? "";
  const selectedCase = state.customer_cases.find((customerCase) => customerCase.id === task.case?.id);
  return `<form method="post" action="/overview-api/tasks/${task.id}?return_to=${escapeHtml(returnTo)}" enctype="multipart/form-data">
    <label>Aufgabe
      <input name="title" type="text" required value="${escapeHtml(task.title)}">
    </label>
    <label>Beschreibung
      <textarea name="description">${escapeHtml(task.description ?? "")}</textarea>
    </label>
    <div class="form-grid">
      <label>Status
        <select name="status_code">
          ${state.task_statuses
            .map((status) => `<option value="${escapeHtml(status.code)}"${selectedAttribute(task.status, status.code)}>${escapeHtml(status.name)}</option>`)
            .join("")}
        </select>
      </label>
      <label>Zustaendig
        <select name="assigned_user_id">
          ${state.users
            .map((user) => {
              const selected = String(user.id) === String(assignedUserId) ? " selected" : "";
              return `<option value="${user.id}"${selected}>${escapeHtml(`${user.first_name} ${user.last_name}`)}</option>`;
            })
            .join("")}
        </select>
      </label>
      <label>Vorgang
        <input name="customer_case_search" list="customer-case-options" type="search" value="${escapeHtml(selectedCase ? customerCaseOptionValue(selectedCase) : "")}" autocomplete="off">
      </label>
      <label>Faellig am
        <input name="due_at" type="datetime-local" value="${escapeHtml(datetimeLocalValue(task.due_at))}">
      </label>
      <label>Erinnerung
        <input name="reminder_at" type="datetime-local" value="${escapeHtml(datetimeLocalValue(task.reminder_at))}">
      </label>
      <label>Prioritaet
        <select name="priority">
          <option value="normal"${selectedAttribute(task.priority, "normal")}>Normal</option>
          <option value="high"${selectedAttribute(task.priority, "high")}>Hoch</option>
          <option value="urgent"${selectedAttribute(task.priority, "urgent")}>Dringend</option>
          <option value="low"${selectedAttribute(task.priority, "low")}>Niedrig</option>
        </select>
      </label>
    </div>
    <label>Anlage ergaenzen
      <input name="attachment" type="file" accept=".pdf,.jpg,.jpeg,.png,.xlsx">
    </label>
    <label class="check-row">
      <input name="reminder_overview_enabled" type="checkbox"${checkedAttribute(task.reminder_overview_enabled)}>
      Erinnerung auf der Uebersicht
    </label>
    <label class="check-row">
      <input name="reminder_email_enabled" type="checkbox"${checkedAttribute(task.reminder_email_enabled)}>
      Erinnerung per E-Mail
    </label>
    <button class="ui-button" type="submit">Aenderungen speichern</button>
  </form>`;
}

function renderOverviewAppointments(state: OverviewState): string {
  if (state.appointments.length === 0) {
    return '<div class="empty">Keine anstehenden Termine in deiner aktuellen Ansicht.</div>';
  }
  return `<div class="list">${state.appointments
    .map(
      (appointment) => `<article class="item compact">
        <div class="item-top">
          <h3>${escapeHtml(truncateText(appointment.title, 70))}</h3>
          <span class="pill">${escapeHtml(formatDateTime(appointment.starts_at))}</span>
        </div>
        <div class="meta">
          ${appointment.location ? `<span>${escapeHtml(appointment.location)}</span>` : ""}
          ${appointment.case ? `<span>${escapeHtml(appointment.case.customer_display_name)}</span>` : ""}
        </div>
      </article>`,
    )
    .join("")}</div>`;
}

function renderOverviewNews(state: OverviewState): string {
  if (state.news_items.length === 0) {
    return '<div class="empty">Keine Neuigkeiten in deiner aktuellen Ansicht.</div>';
  }
  return `<div class="list">${state.news_items
    .map(
      (item) => `<article class="item compact">
        <div class="item-top">
          <h3>${escapeHtml(truncateText(item.title, 70))}</h3>
          <span class="pill">${escapeHtml(item.category)}</span>
        </div>
        ${item.body ? `<p class="preview">${escapeHtml(truncateText(item.body, 130))}</p>` : ""}
      </article>`,
    )
    .join("")}</div>`;
}

function renderOverviewGoals(state: OverviewState): string {
  if (state.goal_events.length === 0) {
    return '<div class="empty">Noch keine erreichten Ziele in deiner aktuellen Ansicht.</div>';
  }
  return `<div class="list">${state.goal_events
    .map(
      (event) => `<article class="item compact">
        <div class="item-top">
          <h3>${escapeHtml(truncateText(event.goal, 70))}</h3>
          <span class="pill">${escapeHtml(formatDateTime(event.achieved_at))}</span>
        </div>
        <div class="meta">${event.achieved_by ? `<span>${escapeHtml(event.achieved_by)}</span>` : ""}</div>
        ${event.note ? `<p class="preview">${escapeHtml(truncateText(event.note, 130))}</p>` : ""}
      </article>`,
    )
    .join("")}</div>`;
}

function renderOverviewDelegations(state: OverviewState): string {
  if (state.delegations.length === 0) {
    return '<div class="empty">Keine aktive Urlaubsvertretung.</div>';
  }
  return `<div class="list">${state.delegations
    .map(
      (delegation) => `<article class="item compact">
        <div class="item-top">
          <h3>${escapeHtml(truncateText(delegation.represented_user, 70))}</h3>
          <span class="pill">${escapeHtml(delegation.scope)}</span>
        </div>
        <div class="meta">
          <span>${escapeHtml(formatDateTime(delegation.starts_at))}</span>
          <span>${escapeHtml(formatDateTime(delegation.ends_at))}</span>
        </div>
      </article>`,
    )
    .join("")}</div>`;
}

function renderTaskCreateForm(state: OverviewState, returnTo = "/index.php"): string {
  const primaryUserId = state.current_user.primary_user_id ?? "";
  return `<form method="post" action="/overview-api/tasks?return_to=${escapeHtml(returnTo)}" enctype="multipart/form-data">
    <label>Aufgabe
      <input name="title" type="text" required placeholder="Was ist zu erledigen?">
    </label>
    <label>Beschreibung
      <textarea name="description"></textarea>
    </label>
    <div class="form-grid">
      <label>Status
        <select name="status_code">
          ${state.task_statuses
            .filter((status) => !status.is_terminal)
            .map((status) => `<option value="${escapeHtml(status.code)}">${escapeHtml(status.name)}</option>`)
            .join("")}
        </select>
      </label>
      <label>Zustaendig
        <select name="assigned_user_id">
          ${state.users
            .map((user) => {
              const selected = String(user.id) === String(primaryUserId) ? " selected" : "";
              return `<option value="${user.id}"${selected}>${escapeHtml(`${user.first_name} ${user.last_name}`)}</option>`;
            })
            .join("")}
        </select>
      </label>
      <label>Faellig am
        <input name="due_at" type="datetime-local">
      </label>
      <label>Vorgang
        <input name="customer_case_search" list="customer-case-options" type="search" autocomplete="off" placeholder="optional: Name, Vorgangs-Nr., Kundennr.">
      </label>
      <label>Erinnerung
        <input name="reminder_at" type="datetime-local">
      </label>
    </div>
    <div class="form-grid">
      <label>Prioritaet
        <select name="priority">
          <option value="normal">Normal</option>
          <option value="high">Hoch</option>
          <option value="urgent">Dringend</option>
          <option value="low">Niedrig</option>
        </select>
      </label>
      <label>Anlage
        <input name="attachment" type="file" accept=".pdf,.jpg,.jpeg,.png,.xlsx">
      </label>
    </div>
    <label class="check-row">
      <input name="reminder_overview_enabled" type="checkbox" checked>
      Erinnerung auf der Uebersicht
    </label>
    <label class="check-row">
      <input name="reminder_email_enabled" type="checkbox">
      Erinnerung per E-Mail
    </label>
    <button class="ui-button" type="submit">Aufgabe anlegen</button>
  </form>`;
}

function renderWorkspaceStyles(): string {
  return `
    ${renderChromeStyles()}
    :root {
      color-scheme: light;
      ${renderTenantThemeVars(DKH_TENANT_UI)}
      --line-strong: #c1cbb9;
      --green-dark: #34591b;
      --soft: #eef6e8;
      --warning: #9a5b00;
      --warning-bg: #fff6df;
      --danger: #9b1c1c;
      --danger-bg: #fff0f0;
      --shadow: 0 10px 24px rgba(24, 38, 18, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--band);
      padding-bottom: calc(64px + env(safe-area-inset-bottom));
    }
    .shell {
      min-height: 100vh;
    }
    aside {
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      padding: 12px 18px;
    }
    .tenant-logo {
      display: block;
      width: min(58%, 208px);
      height: auto;
      aspect-ratio: 260 / 88;
      margin-bottom: 0;
    }
    aside nav {
      display: none;
      gap: 8px;
    }
    aside nav a {
      color: var(--text);
      text-decoration: none;
      padding: 11px 12px;
      border-left: 3px solid transparent;
    }
    aside nav a:hover {
      background: #f6f8f4;
    }
    aside nav a[aria-current="page"] {
      border-left-color: var(--green);
      background: var(--soft);
      font-weight: 700;
    }
    main {
      padding: clamp(16px, 4vw, 24px) clamp(14px, 4vw, 30px) 32px;
      min-width: 0;
    }
    .topline {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 18px;
    }
    h1 {
      margin: 0;
      font-size: clamp(1.4rem, 5vw, 1.8rem);
      line-height: 1.1;
      letter-spacing: 0;
    }
    h2 {
      margin: 0;
      font-size: 1rem;
      letter-spacing: 0;
    }
    h3 {
      margin: 0;
      font-size: 0.95rem;
      letter-spacing: 0;
      line-height: 1.25;
    }
    .lede {
      max-width: 880px;
      color: var(--muted);
      font-size: 0.95rem;
      line-height: 1.45;
      margin: 8px 0 0;
    }
    .command-center {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
      align-items: stretch;
      margin: 0 0 18px;
    }
    .command-search,
    .command-actions {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
    }
    .command-search {
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      align-items: center;
      padding: 8px;
    }
    .command-search label {
      color: var(--green-dark);
      font-size: 0.78rem;
      font-weight: 900;
      text-transform: uppercase;
    }
    .command-search input {
      min-width: 0;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 10px;
      font: inherit;
    }
    .command-search button {
      border: 0;
      border-radius: 6px;
      background: var(--green);
      color: #fff;
      cursor: pointer;
      font: inherit;
      font-weight: 800;
      padding: 10px 12px;
    }
    .command-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1px;
      overflow: hidden;
    }
    .command-actions a {
      display: grid;
      gap: 2px;
      color: var(--text);
      padding: 9px 10px;
      text-decoration: none;
      background: #fbfcfa;
      min-width: 0;
    }
    .command-actions a:hover {
      background: var(--soft);
    }
    .command-actions span {
      color: var(--muted);
      font-size: 0.78rem;
      line-height: 1.35;
    }
    .workspace {
      display: grid;
      grid-template-columns: 1fr;
      gap: 22px;
      align-items: start;
    }
    .stack { display: grid; gap: 20px; min-width: 0; }
    .workspace-section,
    .task-form {
      min-width: 0;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .task-form {
      border-color: var(--line-strong);
      box-shadow: var(--shadow);
    }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 14px;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--line);
    }
    .section-title { display: grid; gap: 2px; }
    .section-kicker {
      color: var(--muted);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .list {
      display: grid;
      gap: 8px;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px 12px;
      background: #ffffff;
      box-shadow: 0 1px 0 rgba(24, 38, 18, 0.03);
    }
    .item.compact { padding: 9px 10px; }
    .item.urgent { border-left: 4px solid var(--danger); }
    .item.high { border-left: 4px solid var(--warning); }
    .item-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }
    .item-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 10px;
      align-items: center;
    }
    details.editor {
      margin-top: 10px;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }
    details.editor summary {
      color: var(--green-dark);
      cursor: pointer;
      font-weight: 800;
      width: fit-content;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      border: 1px solid #abc98f;
      background: var(--soft);
      color: var(--green-dark);
      font-size: 0.78rem;
      font-weight: 700;
      padding: 3px 7px;
      white-space: nowrap;
    }
    .pill.warning {
      border-color: #e0b66b;
      background: var(--warning-bg);
      color: var(--warning);
    }
    .pill.danger {
      border-color: #e1a1a1;
      background: var(--danger-bg);
      color: var(--danger);
    }
    .count-pill,
    .preview,
    .meta,
    .muted,
    p {
      color: var(--muted);
      line-height: 1.45;
    }
    .preview {
      margin: 7px 0 0;
      font-size: 0.88rem;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 7px;
      font-size: 0.8rem;
    }
    .field-hint {
      margin: 0;
      color: var(--warning);
      font-size: 0.78rem;
      font-weight: 700;
    }
    form { display: grid; gap: 10px; }
    .form-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }
    label {
      display: grid;
      gap: 5px;
      color: var(--muted);
      font-size: 0.88rem;
      font-weight: 650;
    }
    input,
    select,
    textarea {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 9px;
      color: var(--text);
      background: #ffffff;
      font: inherit;
    }
    textarea {
      min-height: 72px;
      resize: vertical;
    }
    .check-row {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text);
      font-weight: 600;
    }
    .check-row input {
      width: auto;
      min-height: 0;
    }
    .ui-button {
      border: 1px solid #75a83b;
      background: var(--green);
      color: #111111;
      border-radius: 6px;
      padding: 9px 13px;
      min-height: 48px;
      display: inline-flex;
      align-items: center;
      font-weight: 800;
      text-decoration: none;
      cursor: pointer;
      width: fit-content;
      transition: transform 120ms ease, filter 120ms ease, box-shadow 120ms ease;
    }
    .ui-button.secondary {
      background: #ffffff;
      color: var(--green-dark);
    }
    .ui-button.danger {
      border-color: #d8a3a3;
      background: var(--danger-bg);
      color: var(--danger);
    }
    .inline-form { display: inline; }
    .inline-form .ui-button {
      min-height: 34px;
      padding: 7px 10px;
    }
    .ui-button:hover {
      filter: brightness(0.96);
      box-shadow: 0 2px 0 rgba(52, 89, 27, 0.2);
    }
    .ui-button:active {
      transform: translateY(1px);
      box-shadow: none;
    }
    .table {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      background: #ffffff;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      align-items: center;
      padding: 12px;
      border-bottom: 1px solid var(--line);
    }
    .row:last-child { border-bottom: 0; }
    .row.header {
      background: var(--soft);
      font-weight: 800;
    }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 14px;
      color: var(--muted);
      background: #fbfcfa;
    }
    .filter-note {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--soft);
      color: var(--green-dark);
      font-size: 0.9rem;
      margin: 0 0 18px;
      padding: 9px 10px;
    }
    .more-note {
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.82rem;
      text-align: right;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #ffffff;
      box-shadow: 0 1px 0 rgba(24, 38, 18, 0.03);
      overflow: hidden;
    }
    .card + .card { margin-top: 8px; }
    .card > summary {
      list-style: none;
      cursor: pointer;
      display: grid;
      gap: 4px;
      padding: 12px 14px;
    }
    .card > summary::-webkit-details-marker { display: none; }
    .card > summary .card-title {
      font-weight: 800;
      font-size: 0.98rem;
      overflow-wrap: anywhere;
    }
    .card > summary .card-sub {
      color: var(--muted);
      font-size: 0.84rem;
      display: flex;
      flex-wrap: wrap;
      gap: 6px 12px;
    }
    .card[open] > summary { border-bottom: 1px solid var(--line); }
    .card-body {
      display: grid;
      gap: 10px;
      padding: 12px 14px;
    }
    .contact-actions {
      display: grid;
      gap: 8px;
    }
    .contact-actions a {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 48px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfa;
      color: var(--text);
      font-weight: 700;
      text-decoration: none;
      overflow-wrap: anywhere;
    }
    .contact-actions a small {
      color: var(--muted);
      font-weight: 600;
    }
    @media (min-width: 768px) {
      body { padding-bottom: 0; }
      .shell { display: grid; grid-template-columns: 252px minmax(0, 1fr); }
      aside { border-right: 1px solid var(--line); border-bottom: 0; padding: 24px 18px; }
      aside nav { display: grid; }
      .tenant-logo { width: min(100%, 208px); margin-bottom: 28px; }
      main { padding: 24px 30px 42px; }
      .topline { flex-direction: row; align-items: center; }
      .command-center { grid-template-columns: minmax(280px, 1fr) minmax(280px, 1.1fr); }
      .command-search { grid-template-columns: auto minmax(0, 1fr) auto; }
      .command-actions { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .form-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (min-width: 960px) {
      .workspace { grid-template-columns: minmax(0, 1.05fr) minmax(360px, 0.95fr); }
    }
  `;
}

function renderTasksPage(state: OverviewState): string {
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="tenant-id" content="${escapeHtml(DKH_TENANT_UI.tenantId)}">
  <meta name="experience-standard" content="${escapeHtml(DKH_TENANT_UI.experienceStandard)}">
  <title>Aufgaben | ${escapeHtml(DKH_TENANT_UI.displayName)}</title>
  <style>${renderWorkspaceStyles()}</style>
</head>
<body>
  <div class="shell">
    <aside>
      ${renderTenantLogo(DKH_TENANT_UI)}
      ${renderSideNav("tasks", state.current_user.is_admin)}
    </aside>
    <main>
      <div class="topline">
        <div>
          <h1>Aufgaben</h1>
          <p class="lede">Aufgaben werden hier priorisiert, zugeordnet, bearbeitet und revisionssicher abgeschlossen.</p>
        </div>
        <a class="ui-button" href="#task-create">Aufgabe anlegen</a>
      </div>
      ${renderCommandCenter({
        overdueTasks: state.tasks.filter((task) => isOverdue(task.due_at)).length,
        unassignedEmails: state.emails.filter((email) => email.is_unassigned).length,
        activeCases: state.customer_cases.length,
      })}
      ${renderCustomerCaseDatalist(state)}
      <div class="workspace">
        <section class="workspace-section">
          <div class="section-head"><div class="section-title"><h2>Offene Aufgaben</h2></div><span class="count-pill">${state.tasks.length} Aufgaben</span></div>
          ${renderOverviewTasks(state, "/aufgaben.php")}
        </section>
        <section class="workspace-section task-form" id="task-create">
          <div class="section-head"><div class="section-title"><h2>Aufgabe anlegen</h2></div></div>
          ${renderTaskCreateForm(state, "/aufgaben.php")}
        </section>
      </div>
    </main>
  </div>
  ${renderFab()}
  ${renderBottomNav("tasks")}
</body>
</html>`;
}

function renderEmailsPage(state: OverviewState): string {
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="tenant-id" content="${escapeHtml(DKH_TENANT_UI.tenantId)}">
  <meta name="experience-standard" content="${escapeHtml(DKH_TENANT_UI.experienceStandard)}">
  <title>E-Mails | ${escapeHtml(DKH_TENANT_UI.displayName)}</title>
  <style>${renderWorkspaceStyles()}</style>
</head>
<body>
  <div class="shell">
    <aside>
      ${renderTenantLogo(DKH_TENANT_UI)}
      ${renderSideNav("emails", state.current_user.is_admin)}
    </aside>
    <main>
      <div class="topline">
        <div>
          <h1>E-Mails</h1>
          <p class="lede">E-Mails werden hier gesichtet, Kundenvorgaengen zugeordnet, archiviert oder revisionssicher entfernt.</p>
        </div>
        <a class="ui-button" href="#emails">E-Mails pruefen</a>
      </div>
      ${renderCommandCenter({
        overdueTasks: state.tasks.filter((task) => isOverdue(task.due_at)).length,
        unassignedEmails: state.emails.filter((email) => email.is_unassigned).length,
        activeCases: state.customer_cases.length,
      })}
      ${renderCustomerCaseDatalist(state)}
      <div class="workspace">
        <section class="workspace-section" id="emails">
          <div class="section-head"><div class="section-title"><h2>E-Mail-Eingang</h2></div><span class="count-pill">${state.emails.length} Nachrichten</span></div>
          ${renderOverviewEmails(state, "/emails.php")}
        </section>
      </div>
    </main>
  </div>
  ${renderFab()}
  ${renderBottomNav("emails")}
</body>
</html>`;
}

function customerValue(customer: CustomerRecord | null, key: keyof CustomerRecord): string {
  return escapeHtml(customer?.[key] ?? "");
}

function addressValue(customer: CustomerRecord | null, key: keyof CustomerAddress): string {
  return escapeHtml(customer?.address?.[key] ?? "");
}

function customerMatchesQuery(customer: CustomerRecord, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }
  const searchable = [
    customer.customer_number,
    customer.display_name,
    customer.primary_email,
    customer.primary_phone,
    customer.primary_mobile,
    customer.address?.city,
    customer.address?.postal_code,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return searchable.includes(normalizedQuery);
}

function telHref(value: string): string {
  const trimmed = value.trim();
  const prefix = trimmed.startsWith("+") ? "+" : "";
  const digits = trimmed.replace(/[^0-9]/g, "");
  return `${prefix}${digits}`;
}

function formatAddressLine(address: CustomerAddress | null): string {
  if (!address) {
    return "";
  }
  const street = [address.street, address.house_number].filter(Boolean).join(" ");
  const city = [address.postal_code, address.city].filter(Boolean).join(" ");
  return [street, address.address_extra, city, address.country].filter(Boolean).join(", ");
}

function renderContactLinks(customer: CustomerRecord): string {
  const phoneIcon =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/></svg>';
  const mailIcon =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>';
  const mapIcon =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 10c0 7-9 12-9 12s-9-5-9-12a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>';
  const links: string[] = [];
  if (customer.primary_phone) {
    links.push(
      `<a href="tel:${escapeHtml(telHref(customer.primary_phone))}">${phoneIcon}<span>Anrufen <small>${escapeHtml(customer.primary_phone)}</small></span></a>`,
    );
  }
  if (customer.primary_mobile) {
    links.push(
      `<a href="tel:${escapeHtml(telHref(customer.primary_mobile))}">${phoneIcon}<span>Mobil <small>${escapeHtml(customer.primary_mobile)}</small></span></a>`,
    );
  }
  if (customer.primary_email) {
    links.push(
      `<a href="mailto:${escapeHtml(customer.primary_email)}">${mailIcon}<span>E-Mail <small>${escapeHtml(customer.primary_email)}</small></span></a>`,
    );
  }
  const addressLine = formatAddressLine(customer.address);
  if (addressLine) {
    links.push(
      `<a href="https://www.google.com/maps/search/?api=1&amp;query=${encodeURIComponent(addressLine)}" target="_blank" rel="noopener">${mapIcon}<span>Route <small>${escapeHtml(addressLine)}</small></span></a>`,
    );
  }
  if (links.length === 0) {
    return '<p class="muted">Keine Kontaktdaten hinterlegt.</p>';
  }
  return `<div class="contact-actions">${links.join("")}</div>`;
}

function renderCustomerRows(state: CustomersState): string {
  if (state.customers.length === 0) {
    return '<div class="empty">Noch keine Kunden angelegt.</div>';
  }
  return `<div class="card-list">
    ${state.customers
      .map((customer) => {
        const primaryContact =
          customer.primary_phone ?? customer.primary_mobile ?? customer.primary_email ?? "Kein Kontakt";
        return `<details class="card">
          <summary>
            <span class="card-title">${escapeHtml(customer.display_name)}${customer.customer_number ? ` · ${escapeHtml(customer.customer_number)}` : ""}</span>
            <span class="card-sub">
              <span>${customer.case_count} Vorgaenge</span>
              <span>${escapeHtml(primaryContact)}</span>
            </span>
          </summary>
          <div class="card-body">
            ${renderContactLinks(customer)}
            <a class="ui-button secondary" href="/kunden.php?edit=${customer.id}">Bearbeiten</a>
          </div>
        </details>`;
      })
      .join("")}
  </div>`;
}

function renderCustomerForm(state: CustomersState, customer: CustomerRecord | null): string {
  const isEdit = Boolean(customer);
  const action = isEdit
    ? `/customers-api/customers/${customer?.id}?return_to=/kunden.php?edit=${customer?.id}`
    : "/customers-api/customers?return_to=/kunden.php";
  const ownerUserId = customer?.owner_user_id ?? state.current_user.primary_user_id ?? "";
  return `<form method="post" action="${action}">
    <div class="form-grid">
      <label>Kundentyp
        <select name="customer_type">
          <option value="private"${selectedAttribute(customer?.customer_type, "private")}>Privatkunde</option>
          <option value="company"${selectedAttribute(customer?.customer_type, "company")}>Firma</option>
        </select>
      </label>
      <label>Kundennummer
        <input name="customer_number" type="text" value="${customerValue(customer, "customer_number")}">
      </label>
      <label>Anrede
        <input name="salutation" type="text" value="${customerValue(customer, "salutation")}">
      </label>
      <label>Titel
        <input name="title" type="text" value="${customerValue(customer, "title")}">
      </label>
      <label>Vorname
        <input name="first_name" type="text" value="${customerValue(customer, "first_name")}">
      </label>
      <label>Nachname
        <input name="last_name" type="text" value="${customerValue(customer, "last_name")}">
      </label>
      <label>Firma
        <input name="company_name" type="text" value="${customerValue(customer, "company_name")}">
      </label>
      <label>E-Mail
        <input name="primary_email" type="email" value="${customerValue(customer, "primary_email")}">
      </label>
      <label>Telefon
        <input name="primary_phone" type="text" value="${customerValue(customer, "primary_phone")}">
      </label>
      <label>Mobil
        <input name="primary_mobile" type="text" value="${customerValue(customer, "primary_mobile")}">
      </label>
      <label>Kontaktweg
        <select name="preferred_contact_channel">
          <option value="email"${selectedAttribute(customer?.preferred_contact_channel, "email")}>E-Mail</option>
          <option value="phone"${selectedAttribute(customer?.preferred_contact_channel, "phone")}>Telefon</option>
          <option value="mobile"${selectedAttribute(customer?.preferred_contact_channel, "mobile")}>Mobil</option>
          <option value="post"${selectedAttribute(customer?.preferred_contact_channel, "post")}>Post</option>
          <option value="none"${selectedAttribute(customer?.preferred_contact_channel, "none")}>Kein bevorzugter Weg</option>
        </select>
      </label>
      <label>Verantwortlich
        <select name="owner_user_id">
          ${state.users
            .map((user) => {
              const selected = String(user.id) === String(ownerUserId) ? " selected" : "";
              return `<option value="${user.id}"${selected}>${escapeHtml(`${user.first_name} ${user.last_name}`)}</option>`;
            })
            .join("")}
        </select>
      </label>
      <label>Strasse
        <input name="street" type="text" value="${addressValue(customer, "street")}">
      </label>
      <label>Hausnummer
        <input name="house_number" type="text" value="${addressValue(customer, "house_number")}">
      </label>
      <label>PLZ
        <input name="postal_code" type="text" value="${addressValue(customer, "postal_code")}">
      </label>
      <label>Ort
        <input name="city" type="text" value="${addressValue(customer, "city")}">
      </label>
    </div>
    <label>Notizen
      <textarea name="notes">${customerValue(customer, "notes")}</textarea>
    </label>
    <details class="editor"${isEdit ? "" : " open"}>
      <summary>Vorgang direkt anlegen</summary>
      <label class="check-row">
        <input name="create_case" type="checkbox"${isEdit ? "" : " checked"}>
        Ersten Kundenvorgang anlegen
      </label>
      <div class="form-grid">
        <label>Vorgangsnummer
          <input name="case_number" type="text">
        </label>
        <label>Vorgangstitel
          <input name="case_title" type="text" placeholder="z. B. Kuechenplanung">
        </label>
        <label>Statusphase
          <select name="status_phase_id">
            ${state.status_phases
              .map((phase) => `<option value="${phase.phase}">${phase.phase}. ${escapeHtml(phase.name)}</option>`)
              .join("")}
          </select>
        </label>
        <label>Vorgang verantwortlich
          <select name="responsible_user_id">
            ${state.users
              .map((user) => {
                const selected = String(user.id) === String(ownerUserId) ? " selected" : "";
                return `<option value="${user.id}"${selected}>${escapeHtml(`${user.first_name} ${user.last_name}`)}</option>`;
              })
              .join("")}
          </select>
        </label>
      </div>
    </details>
    <div class="item-actions">
      <a class="ui-button secondary" href="/kunden.php">Zurueck</a>
      <button class="ui-button" type="submit">Speichern</button>
    </div>
  </form>`;
}

function renderCustomersPage(
  state: CustomersState,
  editCustomerId: string | null,
  isNew: boolean,
  searchQuery: string,
): string {
  const visibleCustomers = state.customers.filter((customer) => customerMatchesQuery(customer, searchQuery));
  const visibleState: CustomersState = { ...state, customers: visibleCustomers };
  const editCustomer = state.customers.find((customer) => String(customer.id) === editCustomerId) ?? null;
  const showForm = isNew || Boolean(editCustomer);
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="tenant-id" content="${escapeHtml(DKH_TENANT_UI.tenantId)}">
  <meta name="experience-standard" content="${escapeHtml(DKH_TENANT_UI.experienceStandard)}">
  <title>Kunden | ${escapeHtml(DKH_TENANT_UI.displayName)}</title>
  <style>${renderWorkspaceStyles()}</style>
</head>
<body>
  <div class="shell">
    <aside>
      ${renderTenantLogo(DKH_TENANT_UI)}
      ${renderSideNav("customers", state.current_user.is_admin)}
    </aside>
    <main>
      <div class="topline">
        <div>
          <h1>Kunden</h1>
          <p class="lede">Kunden, Kontaktdaten, Verantwortlichkeiten und Vorgangsstart werden hier eindeutig gepflegt.</p>
        </div>
        <a class="ui-button" href="/kunden.php?new=1">Kunde anlegen</a>
      </div>
      ${renderCommandCenter({
        overdueTasks: 0,
        unassignedEmails: 0,
        activeCases: state.customers.reduce((total, customer) => total + customer.case_count, 0),
      })}
      ${searchQuery ? `<div class="filter-note">Suche: <strong>${escapeHtml(searchQuery)}</strong> · ${visibleCustomers.length} Treffer</div>` : ""}
      <div class="workspace">
        <section class="workspace-section">
          <div class="section-head"><div class="section-title"><h2>Aktuell angelegte Kunden</h2></div><span class="count-pill">${visibleCustomers.length} Kunden</span></div>
          ${renderCustomerRows(visibleState)}
        </section>
        <section class="workspace-section task-form">
          <div class="section-head"><div class="section-title"><h2>${showForm && editCustomer ? escapeHtml(editCustomer.display_name) : "Kunde anlegen"}</h2></div></div>
          ${showForm ? renderCustomerForm(state, editCustomer) : '<div class="empty">Waehle einen Kunden zum Bearbeiten aus oder lege einen neuen Kunden an.</div>'}
        </section>
      </div>
    </main>
  </div>
  ${renderFab()}
  ${renderBottomNav("customers")}
</body>
</html>`;
}

function renderAdmin(state: AdminState, activeModal: string, editUserId: string | null): string {
  const modalNone = activeModal ? "" : " checked";
  const modalUsers = activeModal === "users" ? " checked" : "";
  const modalSettings = activeModal === "settings" ? " checked" : "";
  const modalIntegrations = activeModal === "integrations" ? " checked" : "";
  const primaryUser =
    state.users.find((user) => String(user.id) === editUserId) ?? state.users[0];
  const employeeOverviewChecked = editUserId ? "" : " checked";
  const employeeEditChecked = editUserId ? " checked" : "";
  const employeeRows = renderEmployeeRows(state);
  const company = state.company_settings;
  const integrationRows = renderIntegrationRows(state);
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="tenant-id" content="${escapeHtml(DKH_TENANT_UI.tenantId)}">
  <meta name="experience-standard" content="${escapeHtml(DKH_TENANT_UI.experienceStandard)}">
  <title>Admin Bereich | ${escapeHtml(DKH_TENANT_UI.displayName)}</title>
  <style>
    ${renderChromeStyles()}
    :root {
      color-scheme: light;
      ${renderTenantThemeVars(DKH_TENANT_UI)}
      --green-dark: #34591b;
      --soft: #eef6e8;
      --focus: #1f5f9b;
      --shadow: 0 20px 70px rgba(17, 24, 39, 0.22);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--band);
      padding-bottom: calc(64px + env(safe-area-inset-bottom));
    }
    .shell {
      min-height: 100vh;
    }
    aside {
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      padding: 12px 18px;
    }
    .tenant-logo {
      display: block;
      width: min(58%, 240px);
      height: auto;
      aspect-ratio: 260 / 88;
      margin-bottom: 0;
    }
    aside nav {
      display: none;
      gap: 8px;
    }
    aside nav a {
      color: var(--text);
      text-decoration: none;
      padding: 11px 12px;
      border-left: 3px solid transparent;
    }
    aside nav a[aria-current="page"] {
      border-left-color: var(--green);
      background: var(--soft);
      font-weight: 700;
    }
    main {
      padding: clamp(16px, 4vw, 30px) clamp(14px, 4vw, 34px) 40px;
    }
    h1 {
      margin: 0;
      font-size: clamp(2rem, 3vw, 3.2rem);
      line-height: 1;
      letter-spacing: 0;
    }
    .lede {
      max-width: 760px;
      color: var(--muted);
      font-size: 1.02rem;
      line-height: 1.5;
      margin: 12px 0 26px;
    }
    .tab-control {
      position: absolute;
      opacity: 0;
      pointer-events: none;
    }
    .tile-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
      max-width: 1040px;
    }
    .tile,
    .ui-action,
    button {
      transition: background 120ms ease, border-color 120ms ease, box-shadow 120ms ease, transform 80ms ease;
    }
    .tile {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      cursor: pointer;
      min-height: 142px;
      padding: 18px;
      outline: none;
    }
    .tile:hover {
      background: var(--soft);
      border-color: var(--green);
      box-shadow: 0 10px 28px rgba(52, 89, 27, 0.13);
      transform: translateY(-1px);
    }
    .tile:active,
    .ui-action:active,
    button:active {
      box-shadow: inset 0 2px 5px rgba(17, 24, 39, 0.22);
      transform: translateY(1px);
    }
    .tile:focus,
    .ui-action:focus,
    button:focus {
      box-shadow: 0 0 0 3px rgba(31, 95, 155, 0.18);
      border-color: var(--focus);
    }
    .tile strong {
      display: block;
      font-size: 1.08rem;
      margin-bottom: 9px;
    }
    .tile span {
      color: var(--muted);
      display: block;
      line-height: 1.42;
    }
    .modal {
      display: none;
      position: fixed;
      inset: 0;
      z-index: 10;
    }
    .modal-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(17, 24, 39, 0.42);
      cursor: pointer;
    }
    .modal-window {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      left: 50%;
      max-height: min(86vh, 820px);
      max-width: min(1120px, calc(100vw - 36px));
      min-height: min(720px, calc(100vh - 36px));
      overflow: hidden;
      position: absolute;
      top: 50%;
      transform: translate(-50%, -50%);
      width: min(1120px, calc(100vw - 36px));
    }
    #modal-users:checked ~ .users-modal,
    #modal-settings:checked ~ .settings-modal,
    #modal-integrations:checked ~ .integrations-modal {
      display: block;
    }
    .modal-header {
      align-items: flex-start;
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 14px;
      justify-content: space-between;
      padding: 18px 20px;
    }
    .modal-header h2 {
      font-size: 1.22rem;
      margin: 0 0 5px;
    }
    .modal-header p {
      color: var(--muted);
      margin: 0;
    }
    .modal-body {
      overflow: auto;
      padding: 18px 20px 22px;
    }
    .close {
      align-items: center;
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--text);
      cursor: pointer;
      display: inline-flex;
      font-size: 1.2rem;
      font-weight: 800;
      height: 34px;
      justify-content: center;
      line-height: 1;
      width: 34px;
    }
    .close:hover {
      background: var(--soft);
      border-color: var(--green);
    }
    form {
      display: grid;
      gap: 14px;
    }
    .form-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
    }
    label,
    .field {
      color: #25311f;
      display: grid;
      font-size: 0.9rem;
      font-weight: 700;
      gap: 6px;
    }
    input,
    select,
    textarea {
      background: #ffffff;
      border: 1px solid #bdc9b7;
      border-radius: 6px;
      color: var(--text);
      font: inherit;
      padding: 9px 10px;
      width: 100%;
    }
    textarea {
      min-height: 88px;
      resize: vertical;
    }
    input[type="checkbox"] {
      accent-color: var(--green);
      height: 18px;
      width: 18px;
    }
    .check-row {
      align-items: center;
      display: flex;
      font-weight: 700;
      gap: 8px;
    }
    .table {
      border: 1px solid var(--line);
      border-radius: 8px;
      display: grid;
      overflow: hidden;
    }
    .row {
      align-items: center;
      background: #ffffff;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      display: grid;
      gap: 10px;
      grid-template-columns: 1fr;
      min-height: 50px;
      padding: 10px 12px;
    }
    .row:last-child { border-bottom: 0; }
    .row.header {
      display: none;
      background: var(--soft);
      color: #25311f;
      font-weight: 800;
    }
    .ui-action,
    button {
      background: var(--green);
      border: 1px solid #91b56f;
      border-radius: 6px;
      color: #102000;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      min-height: 48px;
      font: inherit;
      font-weight: 800;
      padding: 8px 11px;
      width: fit-content;
    }
    .ui-action:hover,
    button:hover {
      background: #88ca33;
      border-color: var(--green-dark);
      box-shadow: 0 6px 16px rgba(52, 89, 27, 0.16);
    }
    .ui-action.secondary,
    button.secondary {
      background: #ffffff;
      color: var(--green-dark);
    }
    .ui-action.secondary:hover,
    button.secondary:hover {
      background: var(--soft);
    }
    .actions {
      display: flex;
      gap: 10px;
      justify-content: flex-end;
      margin-top: 2px;
    }
    .employee-overview .actions {
      margin-bottom: 18px;
    }
    .employee-overview,
    .employee-editor,
    .employee-panel,
    .create-form,
    .edit-form {
      display: none;
    }
    #employee-overview:checked ~ .employee-overview,
    #employee-create:checked ~ .employee-editor,
    #employee-edit-konstantin:checked ~ .employee-editor,
    #employee-create:checked ~ .employee-editor .create-form,
    #employee-edit-konstantin:checked ~ .employee-editor .edit-form {
      display: block;
    }
    .employee-tabs {
      border-bottom: 1px solid var(--line);
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 14px;
      padding-bottom: 8px;
    }
    .employee-tabs label {
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      padding: 8px 10px;
      width: fit-content;
    }
    .employee-tabs label:hover {
      background: var(--soft);
      border-color: var(--green);
    }
    #employee-data:checked ~ .employee-tabs label[for="employee-data"],
    #employee-roles:checked ~ .employee-tabs label[for="employee-roles"],
    #employee-workdays:checked ~ .employee-tabs label[for="employee-workdays"] {
      background: var(--soft);
      border-color: var(--green);
      color: var(--green-dark);
      font-weight: 800;
    }
    #employee-data:checked ~ .employee-panels .employee-data-panel,
    #employee-roles:checked ~ .employee-panels .employee-roles-panel,
    #employee-workdays:checked ~ .employee-panels .employee-workdays-panel {
      display: block;
    }
    .workdays {
      display: grid;
      gap: 8px;
      overflow-x: auto;
    }
    .workday {
      align-items: end;
      background: #fbfcfa;
      border: 1px solid var(--line);
      border-radius: 8px;
      display: grid;
      gap: 8px;
      grid-template-columns: 112px 96px repeat(4, minmax(90px, 1fr));
      min-width: 780px;
      padding: 10px;
    }
    .workday .day {
      align-self: center;
      color: #25311f;
      font-weight: 800;
    }
    .hint {
      color: var(--muted);
      font-size: 0.9rem;
      margin: 0;
    }
    @media (min-width: 768px) {
      body { padding-bottom: 0; }
      .shell { display: grid; grid-template-columns: minmax(240px, 320px) 1fr; }
      aside { border-right: 1px solid var(--line); border-bottom: 0; padding: 28px 24px; }
      aside nav { display: grid; }
      .tenant-logo { width: min(100%, 240px); margin-bottom: 36px; }
      main { padding: 30px 34px 44px; }
      .tile-grid { grid-template-columns: repeat(3, minmax(220px, 1fr)); }
      .form-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .row { grid-template-columns: 1.4fr 1fr 0.8fr; }
      .row.header { display: grid; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      ${renderTenantLogo(DKH_TENANT_UI)}
      ${renderSideNav("admin", true)}
    </aside>
    <main>
      <h1>Admin Bereich</h1>
      <p class="lede">Zentrale Verwaltung fuer Mitarbeiter, Firmenstammdaten und Integrationen.</p>

      <input class="tab-control" id="modal-none" name="modal" type="radio"${modalNone}>
      <input class="tab-control" id="modal-users" name="modal" type="radio"${modalUsers}>
      <input class="tab-control" id="modal-settings" name="modal" type="radio"${modalSettings}>
      <input class="tab-control" id="modal-integrations" name="modal" type="radio"${modalIntegrations}>

      <div class="tile-grid">
        <label class="tile" for="modal-users" role="button" tabindex="0">
          <strong>Benutzer</strong>
          <span>Mitarbeiteruebersicht, Neuanlage und Bearbeitung.</span>
        </label>
        <label class="tile" for="modal-settings" role="button" tabindex="0">
          <strong>Firmenstammdaten</strong>
          <span>Adresse, Kontakt, Handelsregister und zentrale Einstellungen pflegen.</span>
        </label>
        <label class="tile" for="modal-integrations" role="button" tabindex="0">
          <strong>Integrationen</strong>
          <span>Externe Dienste konfigurieren, ohne API-Schluessel im Klartext zu speichern.</span>
        </label>
      </div>

      <div class="modal users-modal">
        <label class="modal-backdrop" for="modal-none"></label>
        <div class="modal-window" role="dialog" aria-modal="true" aria-labelledby="users-title">
          <div class="modal-header">
            <div>
              <h2 id="users-title">Benutzer</h2>
              <p>Mitarbeiter verwalten. Rollen und Arbeitszeiten gehoeren zum jeweils ausgewaehlten Mitarbeiter.</p>
            </div>
            <label class="close" for="modal-none" aria-label="Schliessen">x</label>
          </div>
          <div class="modal-body">
            <input class="tab-control" id="employee-overview" name="employee-mode" type="radio"${employeeOverviewChecked}>
            <input class="tab-control" id="employee-create" name="employee-mode" type="radio">
            <input class="tab-control" id="employee-edit-konstantin" name="employee-mode" type="radio"${employeeEditChecked}>

            <div class="employee-overview">
              <div class="actions">
                <label class="ui-action" for="employee-create">Mitarbeiter anlegen</label>
              </div>
              <div class="table">
                <div class="row header"><span>Name</span><span>Rolle</span><span>Aktion</span></div>
                ${employeeRows}
              </div>
            </div>

            <div class="employee-editor">
              <input class="tab-control" id="employee-data" name="employee-detail" type="radio" checked>
              <input class="tab-control" id="employee-roles" name="employee-detail" type="radio">
              <input class="tab-control" id="employee-workdays" name="employee-detail" type="radio">

              <div class="employee-tabs">
                <label for="employee-data">Stammdaten</label>
                <label for="employee-roles">Rollen &amp; Rechte</label>
                <label for="employee-workdays">Arbeitszeiten</label>
              </div>

              <div class="employee-panels">
                <div class="employee-panel employee-data-panel">
                  <div class="create-form">
                    ${renderEmployeeForm("/admin-api/users?return_to=/admin.php?modal=users", "Mitarbeiter anlegen", state.roles, {
                      firstName: "",
                      lastName: "",
                      email: "",
                      phone: "",
                      jobTitle: "",
                      department: "",
                      active: true,
                      mfa: true,
                      timezone: "Europe/Berlin",
                      roles: ["employee"],
                    })}
                  </div>
                  <div class="edit-form">
                    ${primaryUser ? renderEmployeeForm(`/admin-api/users/${primaryUser.id}?return_to=/admin.php?modal=users`, `${primaryUser.first_name} ${primaryUser.last_name} bearbeiten`, state.roles, userToFormValues(primaryUser)) : ""}
                  </div>
                </div>

                <div class="employee-panel employee-roles-panel">
                  <form method="post" action="${primaryUser ? `/admin-api/users/${primaryUser.id}/roles?return_to=/admin.php?modal=users` : "/admin-api/users?return_to=/admin.php?modal=users"}">
                    <div class="form-grid">
                      ${renderRoleInputs(state.roles, primaryUser?.roles ?? [])}
                      <label class="check-row">
                        <input name="permission_admin_view" type="checkbox" checked>
                        Admin-Bereich ansehen
                      </label>
                      <label class="check-row">
                        <input name="permission_admin_users_manage" type="checkbox" checked>
                        Benutzer verwalten
                      </label>
                      <label class="check-row">
                        <input name="permission_admin_roles_manage" type="checkbox" checked>
                        Rollen verwalten
                      </label>
                      <label class="check-row">
                        <input name="permission_admin_integrations_manage" type="checkbox" checked>
                        Integrationen verwalten
                      </label>
                    </div>
                    <div class="actions">
                      <label class="ui-action secondary" for="employee-overview">Zurueck</label>
                      <button type="submit">Speichern</button>
                    </div>
                  </form>
                </div>

                <div class="employee-panel employee-workdays-panel">
                  <form method="post" action="${primaryUser ? `/admin-api/users/${primaryUser.id}/workdays?return_to=/admin.php?modal=users` : "/admin-api/users?return_to=/admin.php?modal=users"}">
                    <div class="form-grid">
                      <label>Mitarbeiter
                        <select name="user_id">
                          ${state.users.map((user) => `<option value="${user.id}">${escapeHtml(`${user.first_name} ${user.last_name}`)}</option>`).join("")}
                        </select>
                      </label>
                      <label>Zeitzone
                        <select name="preference_timezone">
                          <option${selectedAttribute(primaryUser?.timezone, "Europe/Berlin")}>Europe/Berlin</option>
                          <option${selectedAttribute(primaryUser?.timezone, "Europe/Athens")}>Europe/Athens</option>
                          <option${selectedAttribute(primaryUser?.timezone, "Europe/London")}>Europe/London</option>
                        </select>
                      </label>
                    </div>
                    <div class="workdays">
                      ${[1, 2, 3, 4, 5, 6].map((weekday) => renderWorkday(weekday, primaryUser?.workdays.find((day) => day.weekday === weekday))).join("")}
                    </div>
                    <p class="hint">Sonntag ist nicht als Arbeitstag vorgesehen. Das zweite Zeitfenster bleibt leer, wenn keine Pause oder kein Nachmittagsblock benoetigt wird.</p>
                    <div class="actions">
                      <label class="ui-action secondary" for="employee-overview">Zurueck</label>
                      <button type="submit">Speichern</button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal settings-modal">
        <label class="modal-backdrop" for="modal-none"></label>
        <div class="modal-window" role="dialog" aria-modal="true" aria-labelledby="settings-title">
          <div class="modal-header">
            <div>
              <h2 id="settings-title">Firmenstammdaten</h2>
              <p>Stammdaten fuer zentrale Firmenangaben.</p>
            </div>
            <label class="close" for="modal-none" aria-label="Schliessen">x</label>
          </div>
          <div class="modal-body">
            <form method="post" action="/admin-api/company-settings?return_to=/admin.php?modal=settings">
              <div class="form-grid">
                <label>Firmenname
                  <input name="company_name" value="${escapeHtml(company.company_name ?? "das kuechenhaus")}" required>
                </label>
                <label>Rechtlicher Name
                  <input name="legal_name" value="${escapeHtml(company.legal_name ?? "das kuechenhaus ralph schober GmbH")}" required>
                </label>
                <label>Strasse
                  <input name="street" value="${escapeHtml(company.street ?? "Blumenstrasse 17")}">
                </label>
                <label>PLZ
                  <input name="postal_code" value="${escapeHtml(company.postal_code ?? "73728")}">
                </label>
                <label>Ort
                  <input name="city" value="${escapeHtml(company.city ?? "Esslingen")}">
                </label>
                <label>Land
                  <input name="country" value="${escapeHtml(company.country ?? "DE")}">
                </label>
                <label>Telefon
                  <input name="phone" value="${escapeHtml(company.phone ?? "0711/36550747")}">
                </label>
                <label>Fax
                  <input name="fax" value="${escapeHtml(company.fax ?? "0711/36550746")}">
                </label>
                <label>E-Mail
                  <input name="email" type="email" value="${escapeHtml(company.email ?? "info@schober-daskuechenhaus.de")}">
                </label>
                <label>Webseite
                  <input name="website" value="${escapeHtml(company.website ?? "https://www.schober-daskuechenhaus.de")}">
                </label>
                <label>USt-IdNr.
                  <input name="vat_id" value="${escapeHtml(company.vat_id ?? "DE265715198")}">
                </label>
                <label>Handelsregister
                  <input name="commercial_register" value="${escapeHtml(company.commercial_register ?? "Amtsgericht Stuttgart, HR 730338")}">
                </label>
                <label>Geschaeftsfuehrer
                  <input name="managing_director" value="${escapeHtml(company.managing_director ?? "Ralph Schober")}">
                </label>
              </div>
              <div class="actions">
                <label class="ui-action secondary" for="modal-none">Abbrechen</label>
                <button type="submit">Speichern</button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <div class="modal integrations-modal">
        <label class="modal-backdrop" for="modal-none"></label>
        <div class="modal-window" role="dialog" aria-modal="true" aria-labelledby="integrations-title">
          <div class="modal-header">
            <div>
              <h2 id="integrations-title">Integrationen</h2>
              <p>Anbindungen mit Status, Konfiguration und Secret-Referenz.</p>
            </div>
            <label class="close" for="modal-none" aria-label="Schliessen">x</label>
          </div>
          <div class="modal-body">
            ${integrationRows}
            <form method="post" action="/admin-api/integrations?return_to=/admin.php?modal=integrations">
              <div class="form-grid">
                <label>Code
                  <input name="integration_code" placeholder="fastbill">
                </label>
                <label>Name
                  <input name="integration_name" placeholder="FastBill">
                </label>
                <label>Verbindungsname
                  <input name="display_name" placeholder="FastBill Produktion">
                </label>
                <label>Status
                  <select name="status">
                    <option value="pending">ausstehend</option>
                    <option value="configured">konfiguriert</option>
                    <option value="disabled">deaktiviert</option>
                    <option value="error">Fehler</option>
                  </select>
                </label>
                <label>Secret-Referenz
                  <input name="secret_reference" placeholder="cloudflare:fastbill-api-token">
                </label>
                <label class="check-row">
                  <input name="is_enabled" type="checkbox">
                  Aktiv
                </label>
              </div>
              <label>Konfiguration
                <textarea name="config_json" placeholder='{"account":"produktion"}'></textarea>
              </label>
              <div class="actions">
                <label class="ui-action secondary" for="modal-none">Abbrechen</label>
                <button type="submit">Speichern</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </main>
  </div>
  ${renderFab()}
  ${renderBottomNav("admin")}
</body>
</html>`;
}

type EmployeeFormValues = {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  jobTitle: string;
  department: string;
  active: boolean;
  mfa: boolean;
  timezone: string;
  roles: string[];
};

function checkedAttribute(value: boolean): string {
  return value ? " checked" : "";
}

function userToFormValues(user: User): EmployeeFormValues {
  return {
    firstName: user.first_name,
    lastName: user.last_name,
    email: user.email,
    phone: user.phone ?? "",
    jobTitle: user.job_title ?? "",
    department: user.department ?? "",
    active: user.is_active,
    mfa: user.security.mfa_required,
    timezone: user.timezone,
    roles: user.roles,
  };
}

function renderEmployeeRows(state: AdminState): string {
  if (state.users.length === 0) {
    return `<div class="row"><span>Keine Mitarbeiter angelegt</span><span></span><span></span></div>`;
  }
  return state.users
    .map((user) => {
      const roleNames = user.roles
        .map((code) => state.roles.find((role) => role.code === code)?.name ?? code)
        .join(", ");
      return `<div class="row">
                  <span>${escapeHtml(`${user.first_name} ${user.last_name}`)}</span>
                  <span>${escapeHtml(roleNames || "Keine Rolle")}</span>
                  <a class="ui-action secondary" href="/admin.php?modal=users&edit=${user.id}">Bearbeiten</a>
                </div>`;
    })
    .join("");
}

function renderRoleInputs(roles: Role[], selectedRoles: string[]): string {
  return roles
    .map(
      (role) => `<label class="check-row">
                        <input name="role_${escapeHtml(role.code)}" type="checkbox"${checkedAttribute(selectedRoles.includes(role.code))}>
                        ${escapeHtml(role.name)}
                      </label>`
    )
    .join("");
}

function renderIntegrationRows(state: AdminState): string {
  if (state.integrations.length === 0) {
    return "";
  }
  return `<div class="table">
              <div class="row header"><span>Name</span><span>Status</span><span>Aktiv</span></div>
              ${state.integrations
                .map((integration) => {
                  const status = integration.connections[0]?.status ?? "pending";
                  return `<div class="row">
                    <span>${escapeHtml(integration.name)}</span>
                    <span>${escapeHtml(status)}</span>
                    <span>${integration.is_enabled ? "Ja" : "Nein"}</span>
                  </div>`;
                })
                .join("")}
            </div>`;
}

function renderEmployeeForm(action: string, title: string, roles: Role[], values: EmployeeFormValues): string {
  return `<form method="post" action="${escapeHtml(action)}">
    <h3>${escapeHtml(title)}</h3>
    <div class="form-grid">
      <label>Vorname
        <input name="first_name" autocomplete="given-name" value="${escapeHtml(values.firstName)}" required>
      </label>
      <label>Nachname
        <input name="last_name" autocomplete="family-name" value="${escapeHtml(values.lastName)}" required>
      </label>
      <label>E-Mail
        <input name="email" type="email" autocomplete="email" value="${escapeHtml(values.email)}" required>
      </label>
      <label>Telefon
        <input name="phone" autocomplete="tel" value="${escapeHtml(values.phone)}">
      </label>
      <label>Position
        <input name="job_title" value="${escapeHtml(values.jobTitle)}">
      </label>
      <label>Abteilung
        <input name="department" value="${escapeHtml(values.department)}">
      </label>
      <label>Zeitzone
        <select name="timezone">
          <option${selectedAttribute(values.timezone, "Europe/Berlin")}>Europe/Berlin</option>
          <option${selectedAttribute(values.timezone, "Europe/Athens")}>Europe/Athens</option>
          <option${selectedAttribute(values.timezone, "Europe/London")}>Europe/London</option>
        </select>
      </label>
    </div>
    <div class="form-grid">
      <label class="check-row">
        <input name="is_active" type="checkbox"${checkedAttribute(values.active)}>
        Aktiv
      </label>
      <label class="check-row">
        <input name="mfa_required" type="checkbox"${checkedAttribute(values.mfa)}>
        MFA erforderlich
      </label>
      <label class="check-row">
        <input name="password_login_enabled" type="checkbox" disabled>
        Passwort-Login
      </label>
      ${renderRoleInputs(roles, values.roles)}
    </div>
    <input name="external_identity_provider" type="hidden" value="cloudflare_access">
    <div class="actions">
      <label class="ui-action secondary" for="employee-overview">Zurueck</label>
      <button type="submit">Speichern</button>
    </div>
  </form>`;
}

function renderWorkday(weekday: number, values?: Workday): string {
  const label = {
    1: "Montag",
    2: "Dienstag",
    3: "Mittwoch",
    4: "Donnerstag",
    5: "Freitag",
    6: "Samstag",
  }[weekday];
  const value = String(weekday);
  return `<div class="workday">
    <div class="day">${label}</div>
    <input name="weekday_${value}" type="hidden" value="${value}">
    <label class="check-row">
      <input name="is_working_day_${value}" type="checkbox"${checkedAttribute(values?.is_working_day ?? false)}>
      Aktiv
    </label>
    <label>Von
      <input name="morning_start_time_${value}" type="time" value="${escapeHtml(values?.morning_start_time)}">
    </label>
    <label>Bis
      <input name="morning_end_time_${value}" type="time" value="${escapeHtml(values?.morning_end_time)}">
    </label>
    <label>Von
      <input name="afternoon_start_time_${value}" type="time" value="${escapeHtml(values?.afternoon_start_time)}">
    </label>
    <label>Bis
      <input name="afternoon_end_time_${value}" type="time" value="${escapeHtml(values?.afternoon_end_time)}">
    </label>
  </div>`;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      return new Response("ok", {
        headers: {
          ...SECURITY_HEADERS,
          "content-type": "text/plain; charset=utf-8",
        },
      });
    }
    if (url.pathname.startsWith("/tenant-assets/")) {
      const tenantAsset = serveTenantAsset(url.pathname);
      if (tenantAsset) {
        return tenantAsset;
      }
      return htmlResponse("<!doctype html><title>Nicht gefunden</title><h1>Nicht gefunden</h1>", 404);
    }
    if (url.pathname === "/" || url.pathname === "") {
      return redirectResponse("/index.php");
    }
    if (url.pathname.startsWith("/admin-api/")) {
      return proxyAdminApi(request, env);
    }
    if (url.pathname.startsWith("/overview-api/")) {
      return proxyOverviewApi(request, env);
    }
    if (url.pathname.startsWith("/customers-api/")) {
      return proxyCustomersApi(request, env);
    }
    if (url.pathname === "/index.php") {
      const state = await fetchOverviewState(env, request);
      return htmlResponse(renderHome(state));
    }
    if (url.pathname === "/aufgaben.php") {
      const state = await fetchOverviewState(env, request);
      return htmlResponse(renderTasksPage(state));
    }
    if (url.pathname === "/emails.php") {
      const state = await fetchOverviewState(env, request);
      return htmlResponse(renderEmailsPage(state));
    }
    if (url.pathname === "/kunden.php") {
      const state = await fetchCustomersState(env, request);
      return htmlResponse(
        renderCustomersPage(
          state,
          url.searchParams.get("edit"),
          url.searchParams.has("new"),
          url.searchParams.get("q") ?? "",
        ),
      );
    }
    if (url.pathname === "/admin.php") {
      const state = await fetchAdminState(env, request);
      const activeModal = url.searchParams.get("modal") ?? (url.searchParams.has("edit") ? "users" : "");
      return htmlResponse(renderAdmin(state, activeModal, url.searchParams.get("edit")));
    }
    return htmlResponse("<!doctype html><title>Nicht gefunden</title><h1>Nicht gefunden</h1>", 404);
  },
};
