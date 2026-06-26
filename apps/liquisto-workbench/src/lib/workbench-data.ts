import {
  Bot,
  CheckSquare,
  CircleDot,
  Clock3,
  FileSearch,
  Gauge,
  KeyRound,
  ServerCog,
  Search,
  ShieldCheck,
} from "lucide-react";

export const navItems = [
  { href: "/", label: "Cockpit", icon: Gauge },
  { href: "/research", label: "Research", icon: FileSearch },
  { href: "/admin", label: "Admin", icon: KeyRound },
];

export const cockpitMetrics = [
  {
    label: "Tenant Status",
    value: "Setup",
    detail: "liquisto.cloud resolves to the Liquisto tenant authority",
    tone: "info",
    icon: ShieldCheck,
  },
  {
    label: "Visible Workflows",
    value: "2",
    detail: "Research and Admin are the only exposed work areas",
    tone: "success",
    icon: CheckSquare,
  },
  {
    label: "Granted Workflows",
    value: "2",
    detail: "research-intake and tenant-admin are granted by role bundles",
    tone: "success",
    icon: Bot,
  },
  {
    label: "Foreign Context",
    value: "Blocked",
    detail: "Foreign tenant markers are rejected for the Liquisto UI",
    tone: "info",
    icon: ShieldCheck,
  },
];

export const workflowQueue = [
  {
    title: "Research intake",
    scope: "research-intake",
    status: "Configured",
    role: "liquisto-owner, liquisto-researcher",
    validator: "research-output-contract",
  },
  {
    title: "Tenant administration",
    scope: "tenant-admin",
    status: "Configured",
    role: "liquisto-owner",
    validator: "admin-action-validator",
  },
  {
    title: "Tenant isolation",
    scope: "strict-tenant-isolation",
    status: "Enforced",
    role: "all Liquisto role bundles",
    validator: "no-cross-tenant-scope-validator",
  },
];

export const runtimeWorkflowCards = [
  {
    id: "research-intake",
    title: "Tenant-scoped research",
    capability: "research",
    validator: "research-output-contract",
    evidence: "configured in Liquisto owner and researcher role bundles",
    tone: "info",
  },
  {
    id: "tenant-admin",
    title: "Tenant administration",
    capability: "tenant-admin",
    validator: "admin-action-validator",
    evidence: "configured for Liquisto owner role bundle",
    tone: "warning",
  },
  {
    id: "strict-tenant-isolation",
    title: "Cross-tenant rejection",
    capability: "policy gate",
    validator: "no-cross-tenant-scope-validator",
    evidence: "covered by tenant isolation tests and deploy content checks",
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
  "Open research workspace",
  "Review tenant authority",
  "Check role grants",
  "Show isolation evidence",
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
    label: "Research",
    value: "Configured",
    detail: "research-intake is role-granted",
    icon: FileSearch,
    tone: "success",
  },
  {
    label: "Admin",
    value: "Configured",
    detail: "tenant-admin is owner-only",
    icon: KeyRound,
    tone: "info",
  },
  {
    label: "Isolation",
    value: "Fail closed",
    detail: "foreign tenant context is rejected",
    icon: CircleDot,
    tone: "success",
  },
];

export const evidenceTimeline = [
  {
    time: "Config",
    title: "Liquisto tenant authority registered",
    detail: "liquisto.cloud maps to tenant_id liquisto and area_id liquisto",
    state: "Verified",
  },
  {
    time: "Roles",
    title: "Research workflow granted",
    detail: "liquisto-owner and liquisto-researcher include research-intake",
    state: "Accepted",
  },
  {
    time: "Deploy",
    title: "Foreign tenant marker blocked",
    detail: "liquisto-workbench deployment checks reject foreign tenant content",
    state: "Guarded",
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
    source: "Research workflow grants",
    scope: "research-intake",
    status: "Configured",
    updated: "fixture",
  },
  {
    source: "Admin workflow grants",
    scope: "tenant-admin",
    status: "Configured",
    updated: "fixture",
  },
  {
    source: "Tenant isolation tests",
    scope: "Liquisto tenant separation",
    status: "Enforced",
    updated: "repo gate",
  },
];

export const executionPhases = [
  { label: "Resolve tenant", value: "complete", icon: ShieldCheck },
  { label: "Filter scopes", value: "complete", icon: Search },
  { label: "Seal profile", value: "complete", icon: Bot },
  { label: "Run workflow", value: "active", icon: FileSearch },
  { label: "Verify evidence", value: "waiting", icon: Clock3 },
];

export const runtimeSurfaces = [
  {
    title: "Research",
    detail: "Tenant-scoped research using the research-context-synthesis module and research-output-contract validator.",
    icon: FileSearch,
  },
  {
    title: "Admin",
    detail: "Tenant administration is limited to the Liquisto owner role and admin-action-validator.",
    icon: KeyRound,
  },
  {
    title: "Isolation Gate",
    detail: "Strict tenant isolation and no-cross-tenant validators fail closed for mixed scope.",
    icon: ShieldCheck,
  },
];

export const scasWorkbenchAreas = [
  "Research",
  "Admin",
];

export const sections = {
  research: {
    title: "Research",
    subtitle: "Tenant-scoped research workflow backed by Liquisto role grants and validators.",
    icon: FileSearch,
    items: [
      "Role bundles grant research-intake to Liquisto owner and researcher",
      "Runtime composition uses research-context-synthesis",
      "Outputs must pass research-output-contract and tenant scope validators",
    ],
  },
  admin: {
    title: "Admin",
    subtitle: "Owner-only tenant administration workflow.",
    icon: KeyRound,
    items: [
      "liquisto-owner has tenant-admin capability",
      "User permissions are checked through user-permission-validator",
      "Admin actions require admin-action-validator",
    ],
  },
} as const;

export type SectionKey = keyof typeof sections;
