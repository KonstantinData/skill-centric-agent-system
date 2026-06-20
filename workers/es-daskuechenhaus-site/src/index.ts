const LOGO_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAeAAAABvCAMAAAADm+MeAAAABGdBTUEAALGPC/xhBQAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAAY1BMVEUAAAD///////////////////////////////////////////////////////////92uCj///+p03m73JSYyl7d7cmQxVCy14bU6bzD4KGhzmt/vDXl8tf2+/LM5K7u9uSHwUPyC2+eAAAAEHRSTlMAQDAgEL+A75+vUGCPcM/fZqHb/AAAAAFiS0dEAf8CLd4AAAAHdElNRQfqBQkGOyYk0UTJAAANCElEQVR42u2dh4KqOBSGQXrnCNjb+z/lphea4Ow4wM2/dx0NaeYjnRyt8v+VZbQwGcAb118AtnezsujYc/y6vxb3OvUXgMGblUUf5vidR2xO3OuUAbxxGcAblwG8ca0PMB0XDYyODOC21gc4gFC89vg1gHWtDzBAJF57/BrAutYHOPYd8drj1wDWtT7Ab/wawLoM4I3LAN64vgg4Dj3Pw12nACxc/IR8dn3PCzt9K4Ow83306vicIAtjWXaKYglj5te2ksjzUhlLghPJ2BK1g1LD10NbxO1m6HoqlrDdDF2OkH+aUic9J9ViRwESP3F385bAFwN4XyHV+F2N3+1/AHiXAxReAJBywLui5eIWECBfSSskBbwLyAUbfObMYnE8gMDDUdnEb5yjjyjS2FISQV4yejNA7NHrCYsbxUuusw2QBF3KUSaChKbUTg97L4Rv4hD5XlAsdtNinFcDSBV+V+F3zeeAUcFE+L63PfBEUXGXkLqEeG5rB0EfYAQ/sfoLPMKl7dA4fAgCXNYZBDxZMtxG3HwavAjIfRIELo27yKl/erskAD6+kBQoU32APUB3SgwFz5xLoktm9gwbBFyIhYkQaFEVoui4S0CKzW630Riwm7Mq1y7wHDL2eRcRv6yoU/LXLQJW8ugGsUlwUXUT+iegyXmA/+5E3UQJ9gKm0+9Y5DHOyZ/8XwecKAOrnLxPlJWKnBVe3hsW95Ocb7vAMyUWl/jNVX+ZwI/YecS54B99Gje77zLCP5L+nTHASubo5fRfBxyB7LViUlSe4sLwR6g37pEPkm+7wAtwW37ZZQowL+SlCHu1RRI0SZ/31TReUPz3N9GFvAWI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";

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
    .logo {
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
      <img class="logo" src="data:image/png;base64,${LOGO_BASE64}" alt="das kuechenhaus">
      <nav aria-label="Bereiche">
        <a href="/" aria-current="page">Einsatzsteuerung</a>
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
      return htmlResponse(renderHome());
    }
    return htmlResponse("<!doctype html><title>Nicht gefunden</title><h1>Nicht gefunden</h1>", 404);
  },
};
