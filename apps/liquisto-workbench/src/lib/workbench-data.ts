import {
  Activity,
  AlertTriangle,
  Archive,
  Bot,
  CheckSquare,
  CircleDot,
  Clock3,
  DatabaseZap,
  FileSearch,
  Gauge,
  KeyRound,
  Library,
  ListChecks,
  ServerCog,
  Search,
  Settings,
  ShieldCheck,
  Workflow,
} from "lucide-react";

export const navItems = [
  { href: "/", label: "Cockpit", icon: Gauge },
  { href: "/tasks", label: "Tasks", icon: CheckSquare },
  { href: "/research", label: "Research", icon: Search },
  { href: "/cases", label: "Cases", icon: Archive },
  { href: "/knowledge", label: "Knowledge", icon: Library },
  { href: "/agent-runs", label: "Agent Runs", icon: Bot },
  { href: "/approvals", label: "Approvals", icon: ListChecks },
  { href: "/data-sources", label: "Data Sources", icon: DatabaseZap },
  { href: "/audit", label: "Audit", icon: ShieldCheck },
  { href: "/admin", label: "Admin", icon: Settings },
];

export const cockpitMetrics = [
  {
    label: "Aktive Runs",
    value: "18",
    detail: "6 warten auf Evidence",
    tone: "info",
    icon: Activity,
  },
  {
    label: "Freigaben",
    value: "7",
    detail: "2 kritisch vor Ausführung",
    tone: "warning",
    icon: ListChecks,
  },
  {
    label: "Skill Coverage",
    value: "94%",
    detail: "validierte Module im Liquisto Scope",
    tone: "success",
    icon: Workflow,
  },
  {
    label: "Policy Denials",
    value: "3",
    detail: "letzte 24 Stunden",
    tone: "danger",
    icon: ShieldCheck,
  },
];

export const workQueue = [
  {
    title: "Lieferantenanalyse für neue Beschaffungskategorie",
    scope: "Research + Knowledge",
    status: "Human review",
    risk: "Medium",
    owner: "Procurement",
    due: "Heute 16:00",
    confidence: "82%",
  },
  {
    title: "Importierte Marktquelle klassifizieren",
    scope: "Data Source Intake",
    status: "Policy gated",
    risk: "High",
    owner: "Governance",
    due: "Heute 17:30",
    confidence: "61%",
  },
  {
    title: "Case-Briefing aus freigegebenem Kontext erzeugen",
    scope: "Case Execution",
    status: "Ready",
    risk: "Low",
    owner: "Operations",
    due: "Morgen 09:00",
    confidence: "91%",
  },
  {
    title: "Memory Candidate aus Run-Evidence bewerten",
    scope: "Knowledge Governance",
    status: "Validation",
    risk: "Medium",
    owner: "Knowledge",
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
  "Neuen Liquisto Task aufnehmen",
  "Run-ID oder Case suchen",
  "Knowledge Candidate prüfen",
  "Data Source Health öffnen",
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
  { label: "Intake", value: "complete", icon: CheckSquare },
  { label: "Analyze", value: "complete", icon: Search },
  { label: "Compose", value: "complete", icon: Workflow },
  { label: "Execute", value: "active", icon: Bot },
  { label: "Validate", value: "waiting", icon: Clock3 },
];

export const sections = {
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
