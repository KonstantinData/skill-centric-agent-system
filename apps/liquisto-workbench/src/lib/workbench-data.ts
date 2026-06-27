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

export const workspaceActions = [
  {
    title: "Research",
    detail: "Prepare company, market, and meeting intelligence for Liquisto sales work.",
    href: "/research",
    cta: "Open research",
    icon: FileSearch,
  },
  {
    title: "Admin",
    detail: "Manage approved Liquisto users, roles, and workspace settings.",
    href: "/admin",
    cta: "Open admin",
    icon: KeyRound,
  },
];

export const sections = {
  research: {
    title: "Research",
    subtitle: "Prepare evidence-backed company intelligence before manufacturer meetings.",
    icon: FileSearch,
    items: [
      "Create a pre-meeting intelligence brief from company name and domain",
      "Summarize company profile, markets served, financial signals, and current market context",
      "Highlight excess-inventory hypotheses, buyer segment angles, open questions, and source confidence",
    ],
  },
  admin: {
    title: "Admin",
    subtitle: "Manage approved workspace access and settings.",
    icon: KeyRound,
    items: [
      "Review workspace users and their approved responsibilities",
      "Keep role assignments aligned with Liquisto operating needs",
      "Update workspace settings through controlled administration actions",
    ],
  },
} as const;

export type SectionKey = keyof typeof sections;
