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
    label: "Inventory Lists",
    value: "42",
    detail: "12 in analysis, 8 ready for decision",
    tone: "info",
    icon: Boxes,
  },
  {
    label: "Excess Risk",
    value: "18%",
    detail: "marketable positions prioritized",
    tone: "warning",
    icon: AlertTriangle,
  },
  {
    label: "Liquidity Potential",
    value: "€1.8M",
    detail: "assessed remarketing opportunities",
    tone: "success",
    icon: ShoppingCart,
  },
  {
    label: "SCAS Gates",
    value: "3",
    detail: "approvals before risky actions",
    tone: "info",
    icon: ShieldCheck,
  },
];

export const workQueue = [
  {
    title: "Normalize and classify excess inventory list",
    scope: "Inventory Intake",
    status: "Review",
    risk: "Medium",
    owner: "Operations",
    due: "Today 16:00",
    confidence: "88%",
  },
  {
    title: "Assess shortage risk for critical spare parts",
    scope: "Excess + Shortage Analysis",
    status: "Decision needed",
    risk: "High",
    owner: "Analytics",
    due: "Today 17:30",
    confidence: "74%",
  },
  {
    title: "Package marketable positions for resale",
    scope: "Monetization",
    status: "Ready",
    risk: "Low",
    owner: "Commercial",
    due: "Tomorrow 09:00",
    confidence: "91%",
  },
  {
    title: "Prepare repurposing candidates for unused material",
    scope: "Circular Economy",
    status: "Validation",
    risk: "Medium",
    owner: "Product",
    due: "Tomorrow 11:00",
    confidence: "76%",
  },
];

export const agentRuns = [
  {
    id: "run-liquisto-research-2841",
    objective: "Structure procurement market",
    profile: "tenant-research",
    validator: "research-output-contract",
    state: "Validating",
    progress: "72%",
    evidence: "14 spans",
    tone: "info",
  },
  {
    id: "run-liquisto-case-1187",
    objective: "Prepare case next actions",
    profile: "task-execution",
    validator: "task-execution-output-contract",
    state: "Approval required",
    progress: "48%",
    evidence: "write gated",
    tone: "warning",
  },
  {
    id: "run-liquisto-knowledge-0784",
    objective: "Review knowledge record proposal",
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
  "Import inventory list",
  "Review excess and shortage risk",
  "Open monetization initiative",
  "Show SCAS evidence",
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
    detail: "Receive ERP and warehouse lists, normalize them, and attach clean context.",
    icon: PackageSearch,
  },
  {
    title: "Excess & Shortage Analysis",
    detail: "Expose excess stock, shortage risk, aging, and working-capital impact.",
    icon: BarChart3,
  },
  {
    title: "Initiative Management",
    detail: "Coordinate decisions, owners, and progress for each inventory package.",
    icon: ListChecks,
  },
  {
    title: "Monetization",
    detail: "Assess marketable positions, price them, and prepare them for resale.",
    icon: ShoppingCart,
  },
  {
    title: "Repurposing",
    detail: "Qualify unused materials for new use cases, partners, and circular-economy initiatives.",
    icon: Recycle,
  },
  {
    title: "Idle Data Analytics",
    detail: "Translate value-chain and inventory movement data into actionable efficiency signals.",
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
    subtitle: "Turn inventory lists, ERP exports, and customer context into a reliable Liquisto work base.",
    icon: PackageSearch,
    items: [
      "Upload and import paths for excess- and shortage-relevant material data",
      "Normalize part numbers, quantities, aging, locations, and valuation fields",
      "Expose data quality, missing fields, and scope approvals before further analysis",
    ],
  },
  "excess-analysis": {
    title: "Excess & Shortage Analysis",
    subtitle: "Prioritize excess stock, shortage risk, and working-capital potential.",
    icon: BarChart3,
    items: [
      "Diagnose current state against stock, consumption, aging, and replenishment risk",
      "Prioritize marketable positions with minimal risk to ongoing operations",
      "Use benchmark and forecast signals for better inventory decisions",
    ],
  },
  "initiative-management": {
    title: "Initiative Management",
    subtitle: "Coordinate teams, decisions, and actions around inventory packages.",
    icon: ListChecks,
    items: [
      "Manage initiatives by customer, site, material group, potential, and due date",
      "Document decision logic for hold, reuse, resell, recycle, or further analysis",
      "Keep tasks, owners, and progress visible without media breaks",
    ],
  },
  monetization: {
    title: "Monetization",
    subtitle: "Assess marketable excess positions, price them, and prepare them for resale.",
    icon: ShoppingCart,
    items: [
      "Prepare sales packages with price indication, margin, market interest, and risk",
      "Control approvals for external marketing and e-commerce handoff",
      "Make liquidity potential and avoided scrap transparent",
    ],
  },
  repurposing: {
    title: "Repurposing",
    subtitle: "Qualify unused materials for new use cases, partner ideas, and circular-economy initiatives.",
    icon: Recycle,
    items: [
      "Structure material profiles for repurposing ideas and partner screening",
      "Assess use cases, feasibility, and sustainability impact in a traceable way",
      "Carry community and partner decisions forward as initiatives",
    ],
  },
  "partner-network": {
    title: "Partner Network",
    subtitle: "Connect customers, buyers, repurposing partners, and internal stakeholders in controlled workflows.",
    icon: Handshake,
    items: [
      "Make contacts, roles, and interests visible along each initiative",
      "Connect requests, buying interest, and partner feedback with inventory positions",
      "Bundle communication and approval status for Commercial and Operations",
    ],
  },
  "scas-workbench": {
    title: "SCAS Workbench",
    subtitle: "Technical register area for controlled agent work, governance, and evidence inside the Liquisto Platform.",
    icon: CheckSquare,
    items: [
      "Tasks, Research, Cases, Knowledge, Agent Runs, Approvals, Data Sources, Audit, and Admin in one register",
      "One runtime agent works only with a validated profile, explicit scope, and traceable evidence",
      "SCAS remains the governance operating layer; the product surface stays oriented around Liquisto business processes",
    ],
  },
  tasks: {
    title: "Tasks",
    subtitle: "Operational work with controlled agent execution, priority, and review state.",
    icon: CheckSquare,
    items: [
      "Queue by risk, due date, and required decision",
      "Task intake with explicit scope, data approvals, and acceptance criteria",
      "Transition to Agent Runs only after profile validation",
    ],
  },
  research: {
    title: "Research",
    subtitle: "Source work, market analysis, and synthesis with verifiable evidence.",
    icon: FileSearch,
    items: [
      "Keep source status and confidence level visible",
      "Research output contract instead of loose chat response",
      "Synthesis review before knowledge promotion",
    ],
  },
  cases: {
    title: "Cases",
    subtitle: "Liquisto business cases with context, decisions, and active tasks.",
    icon: Archive,
    items: [
      "Case timeline with tasks, runs, documents, and decisions",
      "Case-specific context window instead of global data access",
      "Next actions as verifiable work products",
    ],
  },
  knowledge: {
    title: "Knowledge",
    subtitle: "Approved knowledge objects, memory candidates, and quality signals.",
    icon: Library,
    items: [
      "Knowledge records with provenance, validity, and policy status",
      "Memory candidates separated from approved knowledge",
      "Drift and recertification signals in the workflow",
    ],
  },
  "agent-runs": {
    title: "Agent Runs",
    subtitle: "Single-agent runtime executions with profile, steps, validators, and evidence.",
    icon: Bot,
    items: [
      "Immutable runtime profile for each execution attempt",
      "Step timeline from the Hetzner Runtime Plane",
      "Validator and policy result before completion",
    ],
  },
  approvals: {
    title: "Approvals",
    subtitle: "Human-in-the-loop decisions before writes, promotions, and risky actions.",
    icon: ListChecks,
    items: [
      "Write approval requests with diff, reason, and rollback note",
      "Data scope escalations separated from normal tasks",
      "Decisions permanently visible in audit",
    ],
  },
  "data-sources": {
    title: "Data Sources",
    subtitle: "Allowed Liquisto data sources with scope, sync state, and access policy.",
    icon: DatabaseZap,
    items: [
      "Source Registry as a visible product surface",
      "Connector access only through approved data scopes",
      "Sync health without exposing secret values",
    ],
  },
  audit: {
    title: "Audit",
    subtitle: "Traceable decisions, denials, evidence, and runtime events.",
    icon: ShieldCheck,
    items: [
      "Policy denial ledger filterable by tenant and run",
      "Evidence links instead of raw tool output",
      "Production readiness visible through gates and recertification",
    ],
  },
  admin: {
    title: "Admin",
    subtitle: "Tenant configuration, roles, skill approvals, and control boundaries.",
    icon: KeyRound,
    items: [
      "Roles and principal IDs separated from person display",
      "Skill packs and tool scopes with explicit approval",
      "Cloudflare/Hetzner boundaries as non-negotiable operating rule",
    ],
  },
} as const;

export type SectionKey = keyof typeof sections;
