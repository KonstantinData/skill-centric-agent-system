import {
  FileSearch,
  Gauge,
  KeyRound,
} from "lucide-react";

export const navItems = [
  { href: "/", label: "Cockpit", icon: Gauge },
  { href: "/research", label: "Research", icon: FileSearch },
  { href: "/admin", label: "Admin", icon: KeyRound },
];

export const commandSuggestions = [
  "Open research workspace",
  "Open admin",
];

export const workspaceActions = [
  {
    title: "Research",
    detail: "Work with tenant-scoped research tasks and source synthesis.",
    href: "/research",
    cta: "Open research",
    icon: FileSearch,
  },
  {
    title: "Admin",
    detail: "Manage Liquisto tenant users, roles, and settings.",
    href: "/admin",
    cta: "Open admin",
    icon: KeyRound,
  },
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
