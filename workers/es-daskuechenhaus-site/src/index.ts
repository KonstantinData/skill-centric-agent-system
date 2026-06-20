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
    "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
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
    status: 302,
    headers: {
      ...SECURITY_HEADERS,
      location,
    },
  });
}

function renderHome(): string {
  return `<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Einsatzsteuerung | das kuechenhaus</title>
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
      background: #eef6e8;
      font-weight: 700;
    }
    main {
      padding: 32px;
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
      font-size: clamp(2rem, 4vw, 4rem);
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
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      max-width: 980px;
    }
    section {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      min-height: 150px;
    }
    h2 {
      margin: 0 0 10px;
      font-size: 1rem;
      letter-spacing: 0;
    }
    p, li {
      color: var(--muted);
      line-height: 1.45;
    }
    ul {
      margin: 0;
      padding-left: 18px;
    }
    .metric {
      font-size: 2.2rem;
      font-weight: 800;
      color: var(--green-dark);
    }
    @media (max-width: 780px) {
      .shell { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      main { padding: 24px 18px; }
      .grid { grid-template-columns: 1fr; }
      .topline { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      ${LOGO_MARKUP}
      <nav aria-label="Bereiche">
        <a href="/index.php" aria-current="page">Einsatzsteuerung</a>
        <a href="/planung">Planung</a>
        <a href="/aufgaben">Aufgaben</a>
        <a href="/status">Status</a>
      </nav>
    </aside>
    <main>
      <div class="topline">
        <div>
          <h1>Einsatzsteuerung</h1>
          <p class="lede">Interner Arbeitsbereich fuer das kuechenhaus. Der Zugriff wird vor dieser Anwendung durch Cloudflare Access geschuetzt.</p>
        </div>
        <span class="badge">Access geschuetzt</span>
      </div>
      <div class="grid">
        <section>
          <h2>Heute</h2>
          <div class="metric">0</div>
          <p>Live-Daten werden nach der Backend-Anbindung hier angezeigt.</p>
        </section>
        <section>
          <h2>Naechste Schritte</h2>
          <ul>
            <li>Arbeitsbereiche freischalten</li>
            <li>CRM-Statusdaten anbinden</li>
            <li>Aufgaben und Termine synchronisieren</li>
          </ul>
        </section>
        <section>
          <h2>Sicherheit</h2>
          <p>Diese Seite darf nicht oeffentlich erreichbar sein. Ein HTTP-200 ohne Cloudflare-Access-Session ist ein Deploy-Fehler.</p>
        </section>
        <section>
          <h2>Betrieb</h2>
          <p>Deployment und Access-Konfiguration laufen ueber den SCAS GitHub Actions Workflow.</p>
        </section>
      </div>
    </main>
  </div>
</body>
</html>`;
}

export default {
  fetch(request: Request): Response {
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
    if (url.pathname === "/index.php") {
      return htmlResponse(renderHome());
    }
    return htmlResponse("<!doctype html><title>Nicht gefunden</title><h1>Nicht gefunden</h1>", 404);
  },
};
