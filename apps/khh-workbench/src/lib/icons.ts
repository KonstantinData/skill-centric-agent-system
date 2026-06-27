import {
  CalendarClock,
  ClipboardCheck,
  FileText,
  HeartHandshake,
  Home,
  LayoutDashboard,
  ListChecks,
  ShieldCheck,
  Sparkles,
  UsersRound,
  type LucideProps,
} from "lucide-react";
import type { ComponentType } from "react";
import type { WorkbenchIconId } from "@scas/tenant-workbench-domain";

const iconMap: Record<WorkbenchIconId, ComponentType<LucideProps>> = {
  "calendar-clock": CalendarClock,
  "clipboard-check": ClipboardCheck,
  "file-text": FileText,
  "heart-handshake": HeartHandshake,
  home: Home,
  "layout-dashboard": LayoutDashboard,
  "list-checks": ListChecks,
  "shield-check": ShieldCheck,
  sparkles: Sparkles,
  "users-round": UsersRound,
};

export function resolveIcon(iconId: WorkbenchIconId) {
  return iconMap[iconId];
}
