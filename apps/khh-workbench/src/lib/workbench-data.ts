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
} from "lucide-react";

export const navItems = [
  { href: "/", label: "Heute", icon: LayoutDashboard },
  { href: "/fristen", label: "Fristen", icon: CalendarClock },
  { href: "/personal", label: "Personal-Ampel", icon: UsersRound },
  { href: "/dienste", label: "Dienste", icon: HeartHandshake },
  { href: "/vorgaenge", label: "Vorgaenge", icon: ShieldCheck },
  { href: "/belegung", label: "Belegung", icon: Home },
  { href: "/entwicklung", label: "Entwicklung", icon: Sparkles },
  { href: "/dokumente", label: "Dokumente", icon: FileText },
  { href: "/aufgaben", label: "Aufgaben", icon: ListChecks },
];

export const dailySignals = [
  {
    title: "Personal",
    status: "pruefen",
    detail: "Nachmittag ohne Reserve geplant.",
    action: "Vertretung pruefen",
    icon: UsersRound,
    tone: "warning",
  },
  {
    title: "Fristen",
    status: "kritisch",
    detail: "2 Nachweise laufen diese Woche ab.",
    action: "Nachweise oeffnen",
    icon: CalendarClock,
    tone: "danger",
  },
  {
    title: "Kochdienst",
    status: "ok",
    detail: "Dienst bestaetigt, Hinweis vorhanden.",
    action: "Originalunterlage pruefen",
    icon: HeartHandshake,
    tone: "success",
  },
  {
    title: "Vorgaenge",
    status: "offen",
    detail: "1 Wiedervorlage braucht Leitungssicht.",
    action: "Vorgang ansehen",
    icon: ShieldCheck,
    tone: "info",
  },
];

export const quickActions = [
  {
    title: "Vorgang erfassen",
    detail: "Minimalen Bezug, Risiko, Frist und Freigabestatus aufnehmen.",
    href: "/vorgaenge",
    cta: "Erfassen",
    icon: ClipboardCheck,
  },
  {
    title: "Nachweis pruefen",
    detail: "Gueltigkeit, Verantwortlichkeit und naechste Aktion klaeren.",
    href: "/fristen",
    cta: "Pruefen",
    icon: CalendarClock,
  },
  {
    title: "Dienst ersetzen",
    detail: "Kochdienst oder Arbeitseinsatz mit Belehrungsstatus absichern.",
    href: "/dienste",
    cta: "Oeffnen",
    icon: HeartHandshake,
  },
];

export const agentNotes = [
  {
    observation: "Ein Nachweis laeuft in 14 Tagen ab.",
    reason: "Der Status wirkt auf die Personal-Ampel.",
    proposal: "Erinnerung vorbereiten und Freigabe einholen.",
    approval: "Freigabe erforderlich",
  },
  {
    observation: "Fuer morgen ist ein Essenshinweis markiert.",
    reason: "Kochdienst braucht nur den Hinweis auf Originalunterlage.",
    proposal: "Kueche informieren, keine Details in der Uebersicht anzeigen.",
    approval: "Leitung prueft",
  },
];

export const sections = {
  fristen: {
    title: "Fristen",
    subtitle: "Nachweise, Belehrungen und Wiedervorlagen nach Risiko steuern.",
    icon: CalendarClock,
    items: [
      "Erweitertes Fuehrungszeugnis, Erste Hilfe, IfSG und Lebensmittelbelehrung",
      "Status: gueltig, laeuft bald ab, fehlt, unklar oder nicht erforderlich",
      "Bezug nur als Vorname, Kuerzel, Rolle oder interne Referenz",
    ],
    focus: ["Nachweis", "Bereich", "Status", "Faellig", "Naechste Aktion"],
  },
  personal: {
    title: "Personal-Ampel",
    subtitle: "Tages- und Wochenrisiken fuer Mindestbesetzung sichtbar machen.",
    icon: UsersRound,
    items: [
      "Vormittag, Nachmittag, morgen und Risikotage getrennt bewerten",
      "PiA, FSJ und Praktikum nicht wie voll anrechenbare Fachkraefte behandeln",
      "Abwesenheiten ohne medizinische Details anzeigen",
    ],
    focus: ["Zeitfenster", "Ampel", "Reserve", "Risiko", "Vertretung"],
  },
  dienste: {
    title: "Dienste",
    subtitle: "Kochdienste, Arbeitseinsaetze und Elternpflichten absichern.",
    icon: HeartHandshake,
    items: [
      "Dienststatus fuer heute und morgen schnell erfassen",
      "Belehrungsstatus und Ersatzbedarf sichtbar machen",
      "Ernaehrungshinweise nur als knapper Status, nie als Detailakte",
    ],
    focus: ["Dienst", "Status", "Hinweis", "Ersatz", "Aktion"],
  },
  vorgaenge: {
    title: "Vorgaenge",
    subtitle: "Sensible Vorgänge getrennt von normalem Aufgaben-Kanban fuehren.",
    icon: ShieldCheck,
    items: [
      "Vorfall, Unfall, Kinderschutz und Beschwerde sauber trennen",
      "Agent darf strukturieren, aber keine finale Bewertung treffen",
      "Meldungen an Jugendamt, KVJS oder Gesundheitsamt nur nach Freigabe",
    ],
    focus: ["Typ", "Risiko", "Freigabe", "Wiedervorlage", "Schutzbereich"],
  },
  belegung: {
    title: "Belegung",
    subtitle: "U3, Kindergarten und Hort mit Uebergaengen planen.",
    icon: Home,
    items: [
      "Kita-Portal-Status nur als Prozessstatus fuehren",
      "Uebergang U3, Kindergarten, Schule und Hort in Monatslogik planen",
      "Geschwister- oder Prioritaetsmerkmale ohne Familienakte erfassen",
    ],
    focus: ["Bereich", "Monat", "Plaetze", "Uebergang", "Risiko"],
  },
  entwicklung: {
    title: "Entwicklung",
    subtitle: "Pädagogik, Team, Räume und Elterninitiative systematisch verbessern.",
    icon: Sparkles,
    items: [
      "Jahresziele und Quartalsmassnahmen sichtbar halten",
      "Qualitaetsreviews als Lernsystem, nicht als Kontrollinstrument nutzen",
      "Ideen aus Team und Elternschaft in kleine Experimente fuehren",
    ],
    focus: ["Ziel", "Massnahme", "Review", "Verantwortung", "Wirkung"],
  },
  dokumente: {
    title: "Dokumente",
    subtitle: "Vorlagen, Konzepte und Nachweise mit Status und Version fuehren.",
    icon: FileText,
    items: [
      "Betriebserlaubnis, Konzeption, Schutzkonzept und Hygieneplan referenzieren",
      "Dokumente mit Version, Gueltigkeit und Verantwortlichkeit versehen",
      "Originalunterlagen bleiben ausserhalb der Standarduebersichten",
    ],
    focus: ["Dokument", "Version", "Status", "Gueltig bis", "Verantwortung"],
  },
  aufgaben: {
    title: "Aufgaben",
    subtitle: "Kanban nur als Arbeitsschicht ueber Fristen, Nachweisen und Vorgängen.",
    icon: ListChecks,
    items: [
      "Status: Neu, Geplant, In Arbeit, Wartet, Zur Pruefung, Erledigt",
      "Jede Aufgabe braucht Bereich, Frist, Risiko und Verantwortung",
      "Freigabe- und Nachweispflichten direkt sichtbar machen",
    ],
    focus: ["Aufgabe", "Bereich", "Frist", "Risiko", "Status"],
  },
} as const;

export type SectionKey = keyof typeof sections;

export const privacyRules = [
  "Keine vollstaendigen Kinder-, Eltern- oder Personalstammdaten",
  "Personenbezug nur mit Vorname, Kuerzel oder interner Referenz",
  "Keine Adressen, privaten Kontaktdaten, Geburtsdaten oder Vertragsdaten",
  "Gesundheits- und Sorgerechtshinweise nur als minimaler Status",
];
