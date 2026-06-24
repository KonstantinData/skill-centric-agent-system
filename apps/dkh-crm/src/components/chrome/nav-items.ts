import {
  CalendarDays,
  CheckSquare,
  FileText,
  Home,
  Inbox,
  Settings,
  UserRoundSearch,
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/", label: "Übersicht", icon: Home },
  { href: "/termine", label: "Termine", icon: CalendarDays },
  { href: "/aufgaben", label: "Aufgaben", icon: CheckSquare },
  { href: "/emails", label: "E-Mails", icon: Inbox },
  { href: "/kunden", label: "Kunden", icon: UserRoundSearch },
  { href: "/vorlagen", label: "Vorlagen", icon: FileText },
  { href: "/admin", label: "Admin", icon: Settings },
];
