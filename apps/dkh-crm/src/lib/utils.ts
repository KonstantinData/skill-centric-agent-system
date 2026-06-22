import { format, isToday as dateFnsIsToday, parseISO } from "date-fns";
import { de } from "date-fns/locale";

export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Nicht gesetzt";
  try {
    return format(parseISO(value), "dd.MM.yyyy HH:mm", { locale: de });
  } catch {
    return value;
  }
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Nicht gesetzt";
  try {
    return format(parseISO(value), "dd.MM.yyyy", { locale: de });
  } catch {
    return value;
  }
}

export function isOverdue(value: string | null | undefined): boolean {
  if (!value) return false;
  const date = new Date(value);
  return Number.isFinite(date.getTime()) && date < new Date();
}

export function isToday(value: string | null | undefined): boolean {
  if (!value) return false;
  try {
    return dateFnsIsToday(parseISO(value));
  } catch {
    return false;
  }
}

export function priorityLabel(priority: string | null | undefined): string {
  switch (priority) {
    case "urgent":
      return "Dringend";
    case "high":
      return "Hoch";
    case "low":
      return "Niedrig";
    default:
      return "Normal";
  }
}

export function displayName(firstName: string, lastName: string): string {
  return [firstName, lastName].filter(Boolean).join(" ").trim();
}

export function safeReturnTo(value: string | null | undefined, fallback = "/") {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return fallback;
  return value;
}

export function safeDecodeSegment(segment: string): string | null {
  try {
    const decoded = decodeURIComponent(segment);
    if (decoded.includes("/") || decoded.includes("\\") || decoded.includes("\0")) {
      return null;
    }
    return decoded;
  } catch {
    return null;
  }
}
