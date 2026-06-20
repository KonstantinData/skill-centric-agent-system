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
  tasks: [],
  emails: [],
  appointments: [],
  news_items: [],
  goal_events: [],
  delegations: [],
};

const LOGO_MARKUP = `
<svg class="logo" viewBox="0 0 260 88" role="img" aria-label="das kuechenhaus">
  <rect width="260" height="88" rx="8" fill="#ffffff"/>
  <path d="M22 20h54v48H22z" fill="#76b726"/>
  <path d="M33 31h32v8H33zm0 15h32v8H33z" fill="#ffffff"/>
  <text x="92" y="38" fill="#111111" font-family="Arial, sans-serif" font-size="18" font-weight="700">das</text>
  <text x="92" y="62" fill="#111111" font-family="Arial, sans-serif" font-size="24" font-weight="700">kuechenhaus</text>
</svg>`;

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

function renderHome(state: OverviewState): string {
  const currentUser = state.current_user.display_name || state.current_user.email || "Angemeldeter Nutzer";
  const openTasks = state.tasks.length;
  const unassignedEmails = state.emails.filter((email) => email.is_unassigned).length;
  const dueTasks = state.tasks.filter((task) => task.due_at).length;
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Uebersicht | das kuechenhaus</title>
  <style>
    :root {
      color-scheme: light;
      --text: #111111;
      --muted: #4f5b4a;
      --line: #d8dfd4;
      --green: #76b726;
      --green-dark: #34591b;
      --surface: #ffffff;
      --band: #f4f7f1;
      --soft: #eef6e8;
      --warning: #9a5b00;
      --danger: #9b1c1c;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--band);
    }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(240px, 320px) 1fr;
    }
    aside {
      background: var(--surface);
      border-right: 1px solid var(--line);
      padding: 28px 24px;
    }
    svg.logo {
      display: block;
      width: min(100%, 240px);
      height: auto;
      margin-bottom: 36px;
    }
    nav {
      display: grid;
      gap: 8px;
    }
    nav a {
      color: var(--text);
      text-decoration: none;
      padding: 10px 12px;
      border-left: 3px solid transparent;
    }
    nav a[aria-current="page"] {
      border-left-color: var(--green);
      background: var(--soft);
      font-weight: 700;
    }
    main {
      padding: 28px 32px 42px;
    }
    .topline {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 24px;
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
      font-size: clamp(2rem, 3vw, 3.2rem);
      line-height: 1;
      letter-spacing: 0;
    }
    .lede {
      max-width: 760px;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.55;
      margin: 14px 0 28px;
    }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(130px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }
    .metric-card,
    section,
    .task-form {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .workgrid {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
      gap: 14px;
      align-items: start;
    }
    .stack { display: grid; gap: 14px; }
    h2 {
      margin: 0 0 10px;
      font-size: 1rem;
      letter-spacing: 0;
    }
    h3 {
      margin: 0;
      font-size: 0.96rem;
      letter-spacing: 0;
    }
    p, li, .muted {
      color: var(--muted);
      line-height: 1.45;
    }
    .metric {
      font-size: 1.8rem;
      font-weight: 800;
      color: var(--green-dark);
      line-height: 1.1;
    }
    .metric-label {
      color: var(--muted);
      font-size: 0.82rem;
      margin-top: 4px;
    }
    .list {
      display: grid;
      gap: 9px;
    }
    .item {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #ffffff;
    }
    .item-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
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
      background: #fff6df;
      color: var(--warning);
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.84rem;
    }
    form {
      display: grid;
      gap: 10px;
    }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
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
      font-weight: 800;
      text-decoration: none;
      cursor: pointer;
      width: fit-content;
      transition: transform 120ms ease, filter 120ms ease, box-shadow 120ms ease;
    }
    .ui-button:hover {
      filter: brightness(0.96);
      box-shadow: 0 2px 0 rgba(52, 89, 27, 0.2);
    }
    .ui-button:active {
      transform: translateY(1px);
      box-shadow: none;
    }
    .empty {
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 14px;
      color: var(--muted);
      background: #fbfcfa;
    }
    @media (max-width: 780px) {
      .shell { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      main { padding: 24px 18px; }
      .metrics,
      .workgrid,
      .form-grid { grid-template-columns: 1fr; }
      .topline { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      ${LOGO_MARKUP}
      <nav aria-label="Bereiche">
        <a href="/index.php" aria-current="page">Uebersicht</a>
        ${state.current_user.is_admin ? '<a href="/admin.php">Admin Bereich</a>' : ""}
        <a href="/aufgaben">Aufgaben</a>
        <a href="/status">Status</a>
      </nav>
    </aside>
    <main>
      <div class="topline">
        <div>
          <h1>Uebersicht</h1>
          <p class="lede">Arbeitszentrale fuer ${escapeHtml(currentUser)}: Aufgaben, E-Mails, Termine, Neuigkeiten, Ziele und aktive Vertretungen.</p>
        </div>
        <span class="badge">${state.current_user.is_admin ? "Admin" : "Mitarbeiter"}</span>
      </div>
      <div class="metrics">
        <div class="metric-card"><div class="metric">${openTasks}</div><div class="metric-label">offene Aufgaben</div></div>
        <div class="metric-card"><div class="metric">${dueTasks}</div><div class="metric-label">mit Faelligkeit</div></div>
        <div class="metric-card"><div class="metric">${unassignedEmails}</div><div class="metric-label">nicht zugeordnete E-Mails</div></div>
        <div class="metric-card"><div class="metric">${state.appointments.length}</div><div class="metric-label">anstehende Termine</div></div>
      </div>
      <div class="workgrid">
        <div class="stack">
          <section>
            <h2>Offene Aufgaben</h2>
            ${renderOverviewTasks(state)}
          </section>
          <section>
            <h2>E-Mail Eingange</h2>
            ${renderOverviewEmails(state)}
          </section>
          <section>
            <h2>Anstehende Termine</h2>
            ${renderOverviewAppointments(state)}
          </section>
        </div>
        <div class="stack">
          <section class="task-form">
            <h2>Aufgabe anlegen</h2>
            ${renderTaskCreateForm(state)}
          </section>
          <section>
            <h2>Neuigkeiten</h2>
            ${renderOverviewNews(state)}
          </section>
          <section>
            <h2>Erreichte Ziele</h2>
            ${renderOverviewGoals(state)}
          </section>
          <section>
            <h2>Aktive Vertretungen</h2>
            ${renderOverviewDelegations(state)}
          </section>
        </div>
      </div>
    </main>
  </div>
</body>
</html>`;
}

function renderOverviewTasks(state: OverviewState): string {
  if (state.tasks.length === 0) {
    return '<div class="empty">Keine offenen Aufgaben in deiner aktuellen Ansicht.</div>';
  }
  return `<div class="list">${state.tasks
    .map((task) => {
      const assigned = task.assigned_users.map((user) => user.name).join(", ") || "nicht zugeordnet";
      const caseLabel = task.case
        ? `${task.case.case_number ? `${task.case.case_number} · ` : ""}${task.case.customer_display_name}`
        : "ohne Vorgang";
      return `<article class="item">
        <div class="item-top">
          <h3>${escapeHtml(task.title)}</h3>
          <span class="pill">${escapeHtml(task.status_name)}</span>
        </div>
        ${task.description ? `<p>${escapeHtml(task.description)}</p>` : ""}
        <div class="meta">
          <span>${escapeHtml(assigned)}</span>
          <span>${escapeHtml(caseLabel)}</span>
          ${task.due_at ? `<span>Faellig: ${escapeHtml(task.due_at)}</span>` : ""}
          ${task.attachment_count > 0 ? `<span>${task.attachment_count} Anlage(n)</span>` : ""}
        </div>
      </article>`;
    })
    .join("")}</div>`;
}

function renderOverviewEmails(state: OverviewState): string {
  if (state.emails.length === 0) {
    return '<div class="empty">Keine E-Mail-Eingaenge in deiner aktuellen Ansicht.</div>';
  }
  return `<div class="list">${state.emails
    .map((email) => {
      const sender =
        email.participants.find((participant) => participant.type === "from") ??
        email.participants[0];
      const caseLabel =
        email.cases.map((entry) => `${entry.case_number ? `${entry.case_number} · ` : ""}${entry.customer_display_name}`).join(", ") ||
        "";
      return `<article class="item">
        <div class="item-top">
          <h3>${escapeHtml(email.subject)}</h3>
          <span class="pill${email.is_unassigned ? " warning" : ""}">${email.is_unassigned ? "zuordnen" : "zugeordnet"}</span>
        </div>
        <div class="meta">
          ${sender ? `<span>${escapeHtml(sender.display_name || sender.email_address)}</span>` : ""}
          ${email.received_at ? `<span>${escapeHtml(email.received_at)}</span>` : ""}
          ${caseLabel ? `<span>${escapeHtml(caseLabel)}</span>` : ""}
        </div>
        ${email.snippet ? `<p>${escapeHtml(email.snippet)}</p>` : ""}
        ${email.is_unassigned ? renderEmailAssignmentForm(email.id) : ""}
      </article>`;
    })
    .join("")}</div>`;
}

function renderEmailAssignmentForm(emailMessageId: number): string {
  return `<form method="post" action="/overview-api/emails/assign?return_to=/index.php">
    <input name="email_message_id" type="hidden" value="${emailMessageId}">
    <div class="form-grid">
      <label>Vorgangs-Nr.
        <input name="case_number" type="text" autocomplete="off">
      </label>
      <label>Kunde / Vorgang
        <input name="customer_display_name" type="text" required autocomplete="off">
      </label>
    </div>
    <button class="ui-button" type="submit">E-Mail zuordnen</button>
  </form>`;
}

function renderOverviewAppointments(state: OverviewState): string {
  if (state.appointments.length === 0) {
    return '<div class="empty">Keine anstehenden Termine in deiner aktuellen Ansicht.</div>';
  }
  return `<div class="list">${state.appointments
    .map(
      (appointment) => `<article class="item">
        <div class="item-top">
          <h3>${escapeHtml(appointment.title)}</h3>
          <span class="pill">${escapeHtml(appointment.starts_at)}</span>
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
      (item) => `<article class="item">
        <div class="item-top">
          <h3>${escapeHtml(item.title)}</h3>
          <span class="pill">${escapeHtml(item.category)}</span>
        </div>
        ${item.body ? `<p>${escapeHtml(item.body)}</p>` : ""}
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
      (event) => `<article class="item">
        <div class="item-top">
          <h3>${escapeHtml(event.goal)}</h3>
          <span class="pill">${escapeHtml(event.achieved_at)}</span>
        </div>
        <div class="meta">${event.achieved_by ? `<span>${escapeHtml(event.achieved_by)}</span>` : ""}</div>
        ${event.note ? `<p>${escapeHtml(event.note)}</p>` : ""}
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
      (delegation) => `<article class="item">
        <div class="item-top">
          <h3>${escapeHtml(delegation.represented_user)}</h3>
          <span class="pill">${escapeHtml(delegation.scope)}</span>
        </div>
        <div class="meta">
          <span>${escapeHtml(delegation.starts_at)}</span>
          <span>${escapeHtml(delegation.ends_at)}</span>
        </div>
      </article>`,
    )
    .join("")}</div>`;
}

function renderTaskCreateForm(state: OverviewState): string {
  const primaryUserId = state.current_user.primary_user_id ?? "";
  return `<form method="post" action="/overview-api/tasks?return_to=/index.php" enctype="multipart/form-data">
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
  <title>Admin Bereich | das kuechenhaus</title>
  <style>
    :root {
      color-scheme: light;
      --text: #111111;
      --muted: #4f5b4a;
      --line: #d8dfd4;
      --green: #76b726;
      --green-dark: #34591b;
      --surface: #ffffff;
      --band: #f4f7f1;
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
    }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(240px, 320px) 1fr;
    }
    aside {
      background: var(--surface);
      border-right: 1px solid var(--line);
      padding: 28px 24px;
    }
    svg.logo {
      display: block;
      width: min(100%, 240px);
      height: auto;
      margin-bottom: 36px;
    }
    nav {
      display: grid;
      gap: 8px;
    }
    nav a {
      color: var(--text);
      text-decoration: none;
      padding: 10px 12px;
      border-left: 3px solid transparent;
    }
    nav a[aria-current="page"] {
      border-left-color: var(--green);
      background: var(--soft);
      font-weight: 700;
    }
    main {
      padding: 30px 34px 44px;
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
      grid-template-columns: repeat(3, minmax(220px, 1fr));
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
      grid-template-columns: repeat(2, minmax(0, 1fr));
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
      grid-template-columns: 1.4fr 1fr 0.8fr;
      min-height: 50px;
      padding: 10px 12px;
    }
    .row:last-child { border-bottom: 0; }
    .row.header {
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
    @media (max-width: 900px) {
      .shell { grid-template-columns: 1fr; }
      aside { border-bottom: 1px solid var(--line); border-right: 0; }
      main { padding: 24px 18px; }
      .tile-grid { grid-template-columns: 1fr; }
      .form-grid { grid-template-columns: 1fr; }
      .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
        ${LOGO_MARKUP}
      <nav aria-label="Bereiche">
        <a href="/index.php">Uebersicht</a>
        <a href="/admin.php" aria-current="page">Admin Bereich</a>
        <a href="/aufgaben">Aufgaben</a>
        <a href="/status">Status</a>
      </nav>
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
                      <label class="ui-action secondary" for="employee-overview">EXIT</label>
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
                      <label class="ui-action secondary" for="employee-overview">EXIT</label>
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
      <label class="ui-action secondary" for="employee-overview">EXIT</label>
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
    if (url.pathname === "/" || url.pathname === "") {
      return redirectResponse("/index.php");
    }
    if (url.pathname.startsWith("/admin-api/")) {
      return proxyAdminApi(request, env);
    }
    if (url.pathname.startsWith("/overview-api/")) {
      return proxyOverviewApi(request, env);
    }
    if (url.pathname === "/index.php") {
      const state = await fetchOverviewState(env, request);
      return htmlResponse(renderHome(state));
    }
    if (url.pathname === "/admin.php") {
      const state = await fetchAdminState(env, request);
      const activeModal = url.searchParams.get("modal") ?? (url.searchParams.has("edit") ? "users" : "");
      return htmlResponse(renderAdmin(state, activeModal, url.searchParams.get("edit")));
    }
    return htmlResponse("<!doctype html><title>Nicht gefunden</title><h1>Nicht gefunden</h1>", 404);
  },
};
