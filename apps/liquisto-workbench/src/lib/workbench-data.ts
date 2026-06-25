import {
  Activity,
  AlertTriangle,
  Archive,
  BarChart3,
  Bot,
  Boxes,
  CheckSquare,
  CircleDot,
  Clock3,
  DatabaseZap,
  FileSearch,
  Gauge,
  Handshake,
  KeyRound,
  Library,
  ListChecks,
  PackageSearch,
  Recycle,
  ServerCog,
  Search,
  ShieldCheck,
  ShoppingCart,
} from "lucide-react";

export const navItems = [
  { href: "/", label: "Cockpit", icon: Gauge },
  { href: "/inventory-intake", label: "Inventory Intake", icon: PackageSearch },
  { href: "/excess-analysis", label: "Excess Analysis", icon: BarChart3 },
  { href: "/initiative-management", label: "Initiatives", icon: ListChecks },
  { href: "/monetization", label: "Monetization", icon: ShoppingCart },
  { href: "/repurposing", label: "Repurposing", icon: Recycle },
  { href: "/partner-network", label: "Partner Network", icon: Handshake },
  { href: "/scas-workbench", label: "SCAS Workbench", icon: Bot },
];

export const cockpitMetrics = [
  {
    label: "Inventory Listen",
    value: "42",
    detail: "12 in Analyse, 8 bereit zur Entscheidung",
    tone: "info",
    icon: Boxes,
  },
  {
    label: "Excess Risiko",
    value: "18%",
    detail: "marktfaehige Positionen priorisiert",
    tone: "warning",
    icon: AlertTriangle,
  },
  {
    label: "Liquiditaetspotenzial",
    value: "€1.8M",
    detail: "bewertete Wiedervermarktungschancen",
    tone: "success",
    icon: ShoppingCart,
  },
  {
    label: "SCAS Gates",
    value: "3",
    detail: "Freigaben vor riskanten Aktionen",
    tone: "info",
    icon: ShieldCheck,
  },
];

export const workQueue = [
  {
    title: "Excess Inventory Liste normalisieren und klassifizieren",
    scope: "Inventory Intake",
    status: "Review",
    risk: "Medium",
    owner: "Operations",
    due: "Heute 16:00",
    confidence: "88%",
  },
  {
    title: "Shortage-Risiko fuer kritische Ersatzteile bewerten",
    scope: "Excess + Shortage Analysis",
    status: "Decision needed",
    risk: "High",
    owner: "Analytics",
    due: "Heute 17:30",
    confidence: "74%",
  },
  {
    title: "Marktfaehige Positionen fuer Wiederverkauf paketieren",
    scope: "Monetization",
    status: "Ready",
    risk: "Low",
    owner: "Commercial",
    due: "Morgen 09:00",
    confidence: "91%",
  },
  {
    title: "Repurposing-Kandidaten fuer unused material vorbereiten",
    scope: "Circular Economy",
    status: "Validation",
    risk: "Medium",
    owner: "Product",
    due: "Morgen 11:00",
    confidence: "76%",
  },
];

export const agentRuns = [
  {
    id: "run-liquisto-research-2841",
    objective: "Beschaffungsmarkt strukturieren",
    profile: "tenant-research",
    validator: "research-output-contract",
    state: "Validating",
    progress: "72%",
    evidence: "14 spans",
    tone: "info",
  },
  {
    id: "run-liquisto-case-1187",
    objective: "Case next actions vorbereiten",
    profile: "task-execution",
    validator: "task-execution-output-contract",
    state: "Approval required",
    progress: "48%",
    evidence: "write gated",
    tone: "warning",
  },
  {
    id: "run-liquisto-knowledge-0784",
    objective: "Knowledge Record Proposal prüfen",
    profile: "general-task",
    validator: "general-output-contract",
    state: "Complete",
    progress: "100%",
    evidence: "accepted",
    tone: "success",
  },
];

export const governanceRails = [
  "Tenant context: Liquisto.com",
  "Technical authority: liquisto.cloud",
  "Control Plane: Cloudflare",
  "Runtime Plane: Hetzner",
  "Runtime model: single agent, immutable task profile",
  "Cross-tenant access: fail closed",
];

export const commandSuggestions = [
  "Inventory Liste importieren",
  "Excess- und Shortage-Risiko prüfen",
  "Monetarisierungsinitiative öffnen",
  "SCAS Evidence anzeigen",
];

export const systemSignals = [
  {
    label: "Control API",
    value: "Healthy",
    detail: "D1 registry context reachable",
    icon: ServerCog,
    tone: "success",
  },
  {
    label: "Runtime Plane",
    value: "Watch",
    detail: "6 runs need evidence review",
    icon: Activity,
    tone: "warning",
  },
  {
    label: "Approvals",
    value: "Blocked",
    detail: "2 write requests require owner decision",
    icon: AlertTriangle,
    tone: "danger",
  },
  {
    label: "Knowledge",
    value: "Stable",
    detail: "recertification coverage at 94%",
    icon: CircleDot,
    tone: "success",
  },
];

export const evidenceTimeline = [
  {
    time: "09:12",
    title: "Runtime profile sealed",
    detail: "tenant-research profile generated with 8 allowed modules",
    state: "Verified",
  },
  {
    time: "09:18",
    title: "Source pack validated",
    detail: "12 records passed policy and provenance checks",
    state: "Accepted",
  },
  {
    time: "09:31",
    title: "Write action paused",
    detail: "approval required before Knowledge promotion",
    state: "Waiting",
  },
];

export const dataSourceHealth = [
  {
    source: "Liquisto tenant registry",
    scope: "Control metadata",
    status: "Healthy",
    updated: "2 min",
  },
  {
    source: "Knowledge index",
    scope: "Validated records",
    status: "Healthy",
    updated: "8 min",
  },
  {
    source: "Runtime event store",
    scope: "Hetzner artifacts",
    status: "Review",
    updated: "14 min",
  },
  {
    source: "External market sources",
    scope: "Research intake",
    status: "Gated",
    updated: "31 min",
  },
];

export const executionPhases = [
  { label: "Import", value: "complete", icon: PackageSearch },
  { label: "Analyze", value: "complete", icon: Search },
  { label: "Prioritize", value: "complete", icon: ListChecks },
  { label: "Monetize", value: "active", icon: ShoppingCart },
  { label: "Verify", value: "waiting", icon: Clock3 },
];

export const businessProcesses = [
  {
    title: "Inventory Intake",
    detail: "ERP- und Lagerlisten aufnehmen, normalisieren und mit sauberem Kontext versehen.",
    icon: PackageSearch,
  },
  {
    title: "Excess & Shortage Analysis",
    detail: "Ueberbestand, Mangelrisiko, Alterung und Working-Capital-Effekt sichtbar machen.",
    icon: BarChart3,
  },
  {
    title: "Initiative Management",
    detail: "Entscheidungen, Verantwortliche und Fortschritt je Bestandspaket koordinieren.",
    icon: ListChecks,
  },
  {
    title: "Monetization",
    detail: "Marktfaehige Positionen bewerten, bepreisen und fuer Wiederverkauf vorbereiten.",
    icon: ShoppingCart,
  },
  {
    title: "Repurposing",
    detail: "Unused Materials fuer neue Nutzungsideen, Partner und Circular-Economy-Initiativen qualifizieren.",
    icon: Recycle,
  },
  {
    title: "Idle Data Analytics",
    detail: "Daten aus Wertschöpfung und Bestandsbewegung in verwertbare Effizienzsignale uebersetzen.",
    icon: DatabaseZap,
  },
];

export const scasWorkbenchAreas = [
  "Tasks",
  "Research",
  "Cases",
  "Knowledge",
  "Agent Runs",
  "Approvals",
  "Data Sources",
  "Audit",
  "Admin",
];

export const sections = {
  "inventory-intake": {
    title: "Inventory Intake",
    subtitle: "Bestandslisten, ERP-Exporte und Kundenkontext in eine belastbare Liquisto-Arbeitsgrundlage ueberfuehren.",
    icon: PackageSearch,
    items: [
      "Upload- und Importstrecken fuer Excess- und Shortage-relevante Materialdaten",
      "Normalisierung von Artikelnummern, Mengen, Alterung, Standort und Bewertungsfeldern",
      "Datenqualitaet, fehlende Felder und Scope-Freigaben vor weiterer Analyse sichtbar machen",
    ],
  },
  "excess-analysis": {
    title: "Excess & Shortage Analysis",
    subtitle: "Ueberbestand, Mangelrisiko und Working-Capital-Potenzial priorisieren.",
    icon: BarChart3,
    items: [
      "Diagnose des Status quo gegen Bestand, Verbrauch, Alterung und Wiederbeschaffungsrisiko",
      "Priorisierung marktfaehiger Positionen mit minimalem Risiko fuer laufende Operationen",
      "Benchmark- und Vorhersagesignale fuer bessere Bestandsentscheidungen",
    ],
  },
  "initiative-management": {
    title: "Initiative Management",
    subtitle: "Teams, Entscheidungen und Massnahmen rund um Bestandspakete koordinieren.",
    icon: ListChecks,
    items: [
      "Initiativen nach Kunde, Standort, Materialgruppe, Potenzial und Fälligkeit steuern",
      "Entscheidungslogik fuer Hold, Reuse, Resell, Recycle oder weitere Analyse dokumentieren",
      "Aufgaben, Verantwortliche und Fortschritt ohne Medienbruch sichtbar halten",
    ],
  },
  monetization: {
    title: "Monetization",
    subtitle: "Marktfaehige Excess-Positionen bewerten, bepreisen und fuer Wiederverkauf vorbereiten.",
    icon: ShoppingCart,
    items: [
      "Verkaufspakete mit Preisindikation, Marge, Marktinteresse und Risiko vorbereiten",
      "Freigaben fuer externe Vermarktung und E-Commerce-Weitergabe steuern",
      "Liquiditaetspotenzial und vermiedenen Scrap transparent machen",
    ],
  },
  repurposing: {
    title: "Repurposing",
    subtitle: "Unused Materials fuer neue Nutzung, Partnerideen und Circular-Economy-Initiativen qualifizieren.",
    icon: Recycle,
    items: [
      "Materialprofile fuer Repurposing-Ideen und Partner-Screening strukturieren",
      "Use Cases, Machbarkeit und Nachhaltigkeitswirkung nachvollziehbar bewerten",
      "Community- und Partnerentscheidungen als Initiativen weiterfuehren",
    ],
  },
  "partner-network": {
    title: "Partner Network",
    subtitle: "Kunden, Kaeufer, Repurposing-Partner und interne Stakeholder in kontrollierten Workflows verbinden.",
    icon: Handshake,
    items: [
      "Kontakte, Rollen und Interessen entlang einer Initiative sichtbar machen",
      "Anfragen, Kaufinteresse und Partnerfeedback mit Bestandspositionen verbinden",
      "Kommunikations- und Freigabestatus fuer Commercial und Operations buendeln",
    ],
  },
  "scas-workbench": {
    title: "SCAS Workbench",
    subtitle: "Technischer Registerbereich fuer kontrollierte Agent-Arbeit, Governance und Evidence innerhalb der Liquisto-Plattform.",
    icon: CheckSquare,
    items: [
      "Tasks, Research, Cases, Knowledge, Agent Runs, Approvals, Data Sources, Audit und Admin in einem Register",
      "Ein Runtime-Agent arbeitet nur mit validiertem Profil, explizitem Scope und nachvollziehbarer Evidence",
      "SCAS bleibt Betriebsschicht fuer Governance; die Produktoberflaeche bleibt an Liquisto-Geschaeftsprozessen orientiert",
    ],
  },
  tasks: {
    title: "Tasks",
    subtitle: "Operative Arbeit mit kontrollierter Agent-Ausführung, Priorität und Review-Zustand.",
    icon: CheckSquare,
    items: [
      "Queue nach Risiko, Fälligkeit und benötigter Entscheidung",
      "Task Intake mit explizitem Scope, Datenfreigaben und Akzeptanzkriterien",
      "Übergang zu Agent Runs nur nach Profilvalidierung",
    ],
  },
  research: {
    title: "Research",
    subtitle: "Quellenarbeit, Marktanalyse und Synthese mit überprüfbarer Evidence.",
    icon: FileSearch,
    items: [
      "Quellenstatus und Vertrauensniveau sichtbar halten",
      "Research Output Contract statt loser Chat-Antwort",
      "Synthesis Review vor Knowledge Promotion",
    ],
  },
  cases: {
    title: "Cases",
    subtitle: "Fachliche Liquisto-Vorgänge mit Kontext, Entscheidungen und laufenden Tasks.",
    icon: Archive,
    items: [
      "Case Timeline mit Tasks, Runs, Dokumenten und Entscheidungen",
      "Kontextfenster je Case statt globalem Datenzugriff",
      "Nächste Aktionen als überprüfbare Arbeitsprodukte",
    ],
  },
  knowledge: {
    title: "Knowledge",
    subtitle: "Freigegebene Wissensobjekte, Memory Candidates und Qualitätssignale.",
    icon: Library,
    items: [
      "Knowledge Records mit Herkunft, Gültigkeit und Policy-Status",
      "Memory Candidates getrennt von freigegebenem Wissen",
      "Drift- und Recertification-Signale im Arbeitsfluss",
    ],
  },
  "agent-runs": {
    title: "Agent Runs",
    subtitle: "Ausführungen des Single-Agent-Runtimes mit Profil, Steps, Validatoren und Evidence.",
    icon: Bot,
    items: [
      "Immutable Runtime Profile pro Ausführungsversuch",
      "Step-Timeline aus der Hetzner Runtime Plane",
      "Validator- und Policy-Ergebnis vor Abschluss",
    ],
  },
  approvals: {
    title: "Approvals",
    subtitle: "Human-in-the-loop Entscheidungen vor Writes, Promotions und riskanten Aktionen.",
    icon: ListChecks,
    items: [
      "Write Approval Requests mit Diff, Grund und Rollback-Hinweis",
      "Data Scope Escalations getrennt von normalen Tasks",
      "Entscheidungen dauerhaft im Audit sichtbar",
    ],
  },
  "data-sources": {
    title: "Data Sources",
    subtitle: "Erlaubte Liquisto-Datenquellen mit Scope, Sync-Zustand und Zugriffspolitik.",
    icon: DatabaseZap,
    items: [
      "Source Registry als sichtbarer Produktbestandteil",
      "Connector-Zugriffe nur über freigegebene Data Scopes",
      "Sync-Health ohne Offenlegung geheimer Werte",
    ],
  },
  audit: {
    title: "Audit",
    subtitle: "Nachvollziehbare Entscheidungen, Denials, Evidence und Runtime-Ereignisse.",
    icon: ShieldCheck,
    items: [
      "Policy Denial Ledger nach Tenant und Run filterbar",
      "Evidence Links statt roher Tool-Ausgaben",
      "Produktionsreife über Gates und Recertification sichtbar",
    ],
  },
  admin: {
    title: "Admin",
    subtitle: "Tenant-Konfiguration, Rollen, Skill-Freigaben und Kontrollgrenzen.",
    icon: KeyRound,
    items: [
      "Rollen und Principal IDs getrennt von Personenanzeige",
      "Skill Packs und Tool Scopes mit expliziter Freigabe",
      "Cloudflare/Hetzner Boundaries als nicht-verhandelbare Betriebsregel",
    ],
  },
} as const;

export type SectionKey = keyof typeof sections;
