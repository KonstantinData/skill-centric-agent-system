import {
  AlertTriangle,
  CheckSquare,
  ClipboardList,
  Download,
  FileText,
  FolderOpen,
  Mail,
  MessageSquareText,
  Phone,
  Search,
  Upload,
  X,
} from "lucide-react";
import Script from "next/script";
import { PageHero } from "@/components/chrome/page-hero";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchCustomersState, fetchOverviewState } from "@/lib/dkh-api";
import type { CaratImportPositionRecord, CustomerCaseRecord, SectionPayload } from "@/lib/types";
import { displayName, formatDateTime } from "@/lib/utils";

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ case?: string; register?: string }>;
};

const PROJECT_OBJECTS = [
  ["project_object_kitchen", "Einbauküche"],
  ["project_object_utility", "Hauswirtschaftsraum"],
  ["project_object_service", "Vorratsraum"],
  ["project_object_bedroom", "Schlafzimmer / Schrank"],
  ["project_object_sideboard", "Sideboard"],
  ["project_object_bath", "Badmöbel"],
  ["project_object_wardrobe", "Garderobe"],
  ["project_object_other", "Sonstiges"],
] as const;

const PROJECT_SITUATIONS = [
  ["", "Bitte wählen"],
  ["new_build", "Neubau"],
  ["existing", "Bestand"],
  ["renovation", "Renovierung"],
  ["rental", "Mietobjekt"],
  ["commercial", "Gewerbe / Objekt"],
] as const;

const PROJECT_URGENCIES = [
  [
    "",
    "Bitte wählen",
    "Noch keine Einschätzung zur zeitlichen Dringlichkeit.",
  ],
  [
    "open",
    "Noch offen",
    "Kunde hat noch keinen festen Zeitdruck. Beispiel: Wir wollen uns erst einmal informieren.",
  ],
  [
    "normal",
    "Normal",
    "Kein akuter Terminzwang. Realistische Planung mit üblichem Vorlauf möglich.",
  ],
  [
    "deadline_relevant",
    "Terminrelevant",
    "Es gibt ein Datum, das beachtet werden muss. Beispiele: Umzug, Wohnungsübergabe, Neubauabschnitt oder Mietbeginn.",
  ],
  [
    "time_critical",
    "Zeitkritisch",
    "Der gewünschte Zeitraum liegt sehr nah oder ist schwer erreichbar. Beispiel: Küche soll in wenigen Wochen stehen.",
  ],
  [
    "emergency_replacement",
    "Notfall / Ersatzbedarf",
    "Bestehende Küche nicht nutzbar oder Schadenfall. Beispiele: Wasserschaden, Brandschaden, defekte Bestandsküche, Übergangslösung nötig.",
  ],
] as const;

const BUDGET_RANGES = [
  ["", "Bitte wählen"],
  ["up_to_10000", "bis 10.000 EUR"],
  ["10000_15000", "10.000-15.000 EUR"],
  ["15000_20000", "15.000-20.000 EUR"],
  ["20000_25000", "20.000-25.000 EUR"],
  ["25000_30000", "25.000-30.000 EUR"],
  ["30000_40000", "30.000-40.000 EUR"],
  ["over_40000", "über 40.000 EUR"],
  ["other", "Sonstiges"],
] as const;

const INQUIRY_SOURCES = [
  ["", "Bitte wählen"],
  ["phone", "Telefon"],
  ["website", "Website"],
  ["email", "E-Mail"],
  ["walk_in", "Laufkundschaft"],
  ["recommendation", "Empfehlung"],
  ["other", "Sonstiges"],
] as const;

const DOCUMENT_GUIDE_CATEGORIES = [
  [
    "from_customer",
    "vom Kunden",
    "Fotos, Skizzen, Wunschlisten, Grundrisse, Maße oder Unterlagen, die der Kunde selbst liefert.",
  ],
  [
    "measurement",
    "Aufmaß",
    "Vor-Ort-Aufmaß, Maßblatt, Raummaße, Anschlussmaße, Kontrollaufmaß oder Aufmaßfotos.",
  ],
  [
    "planning",
    "Planung",
    "Küchenplanung, 3D-Ansichten, CARAT- oder Planungs-PDF, Installationsplan, Elektro-/Wasserplan, Teileliste oder Planungsvarianten.",
  ],
  [
    "offer",
    "Angebot",
    "Angebots-PDF, Angebotsversionen, Kalkulation, Preisfreigaben oder Angebotsanhänge.",
  ],
  [
    "order",
    "Auftrag",
    "Auftrag, Kaufvertrag, Auftragsbestätigung an den Kunden, unterschriebene Freigaben oder Änderungsvereinbarungen.",
  ],
  [
    "order_processing",
    "Bestellabwicklung",
    "Herstellerbestellungen, Lieferanten-Auftragsbestätigungen, Bestellfreigaben, Kommissionsunterlagen oder Lieferterminbestätigungen vom Lieferanten.",
  ],
  [
    "delivery_installation",
    "Lieferung / Montage",
    "Lieferbelege, Montageunterlagen, Monteurpläne, Baustellenfotos, Abnahmeprotokoll oder Montagebericht.",
  ],
  [
    "complaint_service",
    "Reklamation / Kundendienst",
    "Mängelbilder, Reklamationsnotizen, Kundendienstauftrag, Ersatzteilunterlagen oder Nachbesserungsprotokolle.",
  ],
  [
    "invoice",
    "Rechnung",
    "Rechnung, E-Rechnung, Anzahlungsrechnung, Schlussrechnung, Zahlungsbeleg oder Gutschrift.",
  ],
] as const;

const LEGACY_DOCUMENT_CATEGORIES = [
  ["customer_document", "Kundenunterlage"],
  ["drawing_plan", "Plan / Aufmaß"],
  ["offer_order", "Angebot / Auftrag"],
  ["invoice_closure", "Rechnung / Abschluss"],
] as const;

const DOCUMENT_CATEGORY_LABEL_OPTIONS = [
  ...DOCUMENT_GUIDE_CATEGORIES,
  ...LEGACY_DOCUMENT_CATEGORIES,
] as const;

const DOCUMENT_STATUSES = [
  ["received", "Eingegangen"],
  ["in_review", "In Prüfung"],
  ["approved", "Freigegeben"],
  ["sent_to_customer", "An Kunde gesendet"],
  ["confirmed_by_customer", "Vom Kunden bestätigt"],
] as const;

const CONTACT_ROLES = [
  ["architect", "Architekt"],
  ["developer", "Bauträger"],
  ["company", "Firma"],
  ["partner", "Partner"],
  ["joinery", "Schreinerei"],
  ["drywall", "Trockenbau"],
  ["electrical", "Elektriker"],
  ["plumbing", "Flaschner / Sanitär"],
  ["installer", "Monteur"],
  ["supplier", "Lieferant"],
  ["other", "Sonstige"],
] as const;

const CASE_REGISTERS = [
  {
    key: "anfrage",
    label: "Anfrage",
    phaseRange: [1, 1],
    description: "Projektgrundlagen und erster Anlass.",
  },
  {
    key: "beratung",
    label: "Beratung",
    phaseRange: [2, 2],
    description: "Ansprechpartner und Abstimmung.",
  },
  {
    key: "planung",
    label: "Planung",
    phaseRange: [3, 3],
    description: "Objekte, Räume und Planungsnotizen.",
  },
  {
    key: "angebot_auftrag",
    label: "Angebot / Auftrag",
    phaseRange: [4, 5],
    description: "Angebote, Auftragsunterlagen und Dokumente.",
  },
  {
    key: "abwicklung",
    label: "Abwicklung",
    phaseRange: [6, 8],
    description: "Aufgaben, Termine und kritische Schritte.",
  },
  {
    key: "rechnung_abschluss",
    label: "Rechnung / Abschluss",
    phaseRange: [9, 11],
    description: "Rechnung, Abschluss und Vorgangshistorie.",
  },
  {
    key: "kommunikation",
    label: "Kommunikation",
    phaseRange: [1, 11],
    description: "Telefonnotizen, E-Mail-Entwürfe und Historie.",
  },
] as const;

type CaseRegisterKey = (typeof CASE_REGISTERS)[number]["key"];
type CaseDesktopRegisterKey = CaseRegisterKey | "dokumente";

const DOCUMENTS_REGISTER = {
  key: "dokumente",
  label: "Dokumente",
  description: "Dokumente hochladen, herunterladen und für den Versand vorbereiten.",
} as const;

const INITIAL_CUSTOMER_EXPORT_AT = "2026-06-23T17:42:00+02:00";

function registerForPhase(phase: number | null | undefined): CaseRegisterKey {
  const normalizedPhase = phase ?? 1;
  return (
    CASE_REGISTERS.find(
      (register) =>
        normalizedPhase >= register.phaseRange[0] &&
        normalizedPhase <= register.phaseRange[1] &&
        register.key !== "kommunikation",
    )?.key ?? "anfrage"
  );
}

function normalizeRegister(value: string | undefined, phase: number | null | undefined): CaseDesktopRegisterKey {
  if (value === DOCUMENTS_REGISTER.key) {
    return DOCUMENTS_REGISTER.key;
  }
  return CASE_REGISTERS.some((register) => register.key === value)
    ? (value as CaseRegisterKey)
    : registerForPhase(phase);
}

function sectionValue(
  section: SectionPayload | undefined,
  key: string,
): string {
  const value = section?.[key];
  return value === null || value === undefined ? "" : String(value);
}

function sectionChecked(section: SectionPayload | undefined, key: string): boolean {
  const value = section?.[key];
  return value === true || value === "true" || value === "on" || value === "1";
}

function optionLabel(
  options: readonly (readonly string[])[],
  value: string | null | undefined,
): string {
  return options.find(([key]) => key === value)?.[1] ?? value ?? "";
}

function displayImportQuantity(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "Menge offen";
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return `Menge ${value}`;
  return `Menge ${numeric.toLocaleString("de-DE", { maximumFractionDigits: 3 })}`;
}

function displayDimensions(dimensions: Record<string, number | string | null | undefined>) {
  const values = [dimensions.width, dimensions.depth, dimensions.height]
    .filter((value) => value !== null && value !== undefined && value !== "")
    .map((value) => String(value));
  return values.length > 0 ? values.join(" x ") : "";
}

function normalizeCaratText(value: string | null | undefined): string {
  return (value ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/\s+/g, " ");
}

function isExportableCaratPosition(position: CaratImportPositionRecord): boolean {
  const supplierName = normalizeCaratText(position.supplier_name);
  const title = normalizeCaratText(position.title);
  return !(
    supplierName === "bilddaten" ||
    (position.article_code === "46000000000" &&
      (title === "decke" || /^wand [0-9]+$/.test(title)))
  );
}

function severityLabel(value: string): string {
  if (value === "red") return "Rot";
  if (value === "yellow") return "Gelb";
  return "Grün";
}

function severityClass(value: string): string {
  if (value === "red") return "border-red-300 bg-red-50 text-red-900";
  if (value === "yellow") return "border-yellow-300 bg-yellow-50 text-yellow-900";
  return "border-emerald-300 bg-emerald-50 text-emerald-900";
}

function confirmationStatusLabel(value: string): string {
  const labels: Record<string, string> = {
    draft: "Entwurf",
    matching_in_progress: "Abgleich läuft",
    matched: "Passt",
    exceptions_open: "Abweichungen offen",
    context_revision_required: "Kontext prüfen",
    suspended: "Wartet auf Lieferant",
    invalidated: "Ungültig",
    replaced: "Ersetzt",
    approved: "Freigegeben",
    archived: "Archiviert",
  };
  return labels[value] ?? value;
}

function differenceTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    article_number: "Artikelnummer",
    quantity: "Menge",
    unit: "Einheit",
    net_price: "Netto-Preis",
    discount: "Rabatt",
    delivery_date: "Liefertermin",
    text: "Text",
    extra_position: "Zusatzposition",
    missing_position: "Fehlende Position",
    unreadable_field: "Nicht lesbar",
    replacement_article: "Ersatzartikel",
    context: "Kontext",
  };
  return labels[value] ?? value;
}

function UrgencyInfoTooltip() {
  return (
    <div className="group relative inline-flex">
      <span
        tabIndex={0}
        aria-label="Informationen zu den Dringlichkeitsleveln"
        className="grid h-5 w-5 cursor-help place-items-center rounded-full border border-[var(--accent)] bg-white text-xs font-bold text-[var(--accent-strong)] outline-none focus:ring-2 focus:ring-[var(--accent)]"
      >
        i
      </span>
      <div className="pointer-events-none absolute left-0 top-7 z-20 hidden w-80 rounded-lg border border-[var(--border)] bg-white p-3 text-xs font-normal leading-relaxed text-[var(--foreground)] shadow-lg group-hover:block group-focus-within:block">
        <p className="font-bold">Dringlichkeitslevel</p>
        <dl className="mt-2 grid gap-2">
          {PROJECT_URGENCIES.filter(([value]) => value).map(([value, label, description]) => (
            <div key={value}>
              <dt className="font-bold">{label}</dt>
              <dd className="text-[var(--muted)]">{description}</dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}

function caseLabel(item: CustomerCaseRecord): string {
  return item.case_number || `Vorgang #${item.id}`;
}

export default async function CustomerFilePage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const { case: selectedCaseId, register } = await searchParams;
  const userEmail = await getUserEmail();
  const [state, overview] = await Promise.all([
    fetchCustomersState(userEmail),
    fetchOverviewState(userEmail),
  ]);
  const customer = state.customers.find((item) => String(item.id) === id);
  if (!customer) {
    return (
      <div className="content-stack">
        <PageHero
          title="Kundenakte nicht gefunden"
          subtitle={`Für die ID ${id} ist keine sichtbare Kundenakte vorhanden.`}
        />
        <Panel>
          <div className="grid min-h-[360px] place-items-center rounded-lg border border-dashed border-[var(--border)] bg-white p-8 text-center">
            <div className="max-w-lg">
              <Search size={36} className="mx-auto text-[var(--accent-strong)]" aria-hidden="true" />
              <h2 className="mt-3 text-xl font-bold">Kunde über Suche öffnen</h2>
              <p className="mt-2 text-sm text-[var(--muted)]">
                Die angeforderte Kundenakte ist nicht in den aktuell geladenen Kundendaten enthalten.
                Öffnen Sie die Kundensuche, um den richtigen Datensatz auszuwählen.
              </p>
              <div className="mt-4 flex justify-center">
                <LinkButton href="/kunden" variant="primary">
                  Zur Kundensuche
                </LinkButton>
              </div>
            </div>
          </div>
        </Panel>
      </div>
    );
  }

  const cases = state.customer_cases.filter(
    (item) => item.customer_id === customer.id,
  );
  const selectedCase = selectedCaseId
    ? cases.find((item) => String(item.id) === selectedCaseId)
    : undefined;
  const selectedCaseTasks = selectedCase
    ? overview.tasks.filter((task) => task.case?.id === selectedCase.id)
    : [];
  const selectedCaseEvents = selectedCase
    ? (overview.communication_events ?? []).filter(
        (event) => event.customer_case?.id === selectedCase.id,
      )
    : [];
  const activeRegister = selectedCase ? normalizeRegister(register, selectedCase.status_phase) : null;
  const selectedCaseReturnPath = selectedCase
    ? `/kunden/${customer.id}?case=${selectedCase.id}${activeRegister ? `&register=${activeRegister}` : ""}`
    : `/kunden/${customer.id}`;
  const returnTo = encodeURIComponent(selectedCaseReturnPath);
  const formalContactName = [
    customer.salutation,
    customer.title,
    customer.display_name,
  ]
    .filter(Boolean)
    .join(" ");
  const address = [
    customer.address?.street,
    customer.address?.house_number,
    customer.address?.postal_code,
    customer.address?.city,
    customer.address?.country || customer.country,
  ]
    .filter(Boolean)
    .join(" ");
  const owner = state.users.find((user) => user.id === customer.owner_user_id);
  const lastExportedAt =
    sectionValue(customer.file_sections?.customer_export, "last_exported_at") ||
    INITIAL_CUSTOMER_EXPORT_AT;

  return (
    <div className="content-stack">
      <PageHero
        title={customer.display_name}
        subtitle={`${customer.customer_number || "Ohne Kundennummer"} · Kundenakte als Desktop mit vorgangsbezogener Arbeit`}
      />

      <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
        <aside className="grid h-fit gap-4">
          <Panel>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="section-title">Stammdaten-Snapshot</h2>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  {customer.customer_type === "company" ? "Objektkunde" : "Privatkunde"}
                </p>
              </div>
              <span className="badge">{customer.customer_number || "ohne Nummer"}</span>
            </div>

            <dl className="mt-4 grid gap-3 text-sm">
              <div>
                <dt className="font-bold">Kontakt</dt>
                <dd>{formalContactName || customer.display_name}</dd>
                {customer.company_name ? <dd>{customer.company_name}</dd> : null}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <dt className="font-bold">Anrede</dt>
                  <dd>{customer.salutation || "Nicht hinterlegt"}</dd>
                </div>
                <div>
                  <dt className="font-bold">Titel</dt>
                  <dd>{customer.title || "Nicht hinterlegt"}</dd>
                </div>
              </div>
              <div>
                <dt className="font-bold">Telefon</dt>
                <dd>{customer.primary_phone || customer.primary_mobile || "Nicht hinterlegt"}</dd>
              </div>
              <div>
                <dt className="font-bold">E-Mail</dt>
                <dd className="break-words">{customer.primary_email || "Nicht hinterlegt"}</dd>
              </div>
              <div>
                <dt className="font-bold">Adresse</dt>
                <dd>{address || "Nicht hinterlegt"}</dd>
              </div>
              <div>
                <dt className="font-bold">Zuständig</dt>
                <dd>
                  {owner
                    ? displayName(owner.first_name, owner.last_name) || owner.email
                    : "Nicht zugeordnet"}
                </dd>
              </div>
            </dl>

            <div className="mt-4 flex flex-wrap gap-2">
              <a className="btn btn-secondary" href={`tel:${customer.primary_phone || customer.primary_mobile || ""}`}>
                <Phone size={16} aria-hidden="true" />
                Telefon
              </a>
              <a
                className={`btn btn-secondary ${customer.primary_email ? "" : "pointer-events-none opacity-50"}`}
                href={customer.primary_email ? `mailto:${customer.primary_email}` : undefined}
                aria-disabled={!customer.primary_email}
              >
                <Mail size={16} aria-hidden="true" />
                E-Mail
              </a>
            </div>

            <div className="mt-4">
              <button type="button" className="btn btn-secondary" data-customer-master-open>
                Stammdaten bearbeiten
              </button>
            </div>

            <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3">
              <p className="text-xs font-bold uppercase text-[var(--muted)]">Lokale Sicherung</p>
              <p className="mt-1 text-sm">
                Letzter Export: {formatDateTime(lastExportedAt)}
              </p>
              <a
                className="btn btn-primary mt-3 w-full justify-center"
                href={`/api/kunden/customers/${customer.id}/export`}
              >
                <Download size={16} aria-hidden="true" />
                Kundenakte herunterladen
              </a>
            </div>
          </Panel>

          <Panel>
            <div className="flex items-center justify-between gap-3">
              <h2 className="section-title">Vorgangsregal</h2>
              <span className="badge">{cases.length} Vorgänge</span>
            </div>
            <div className="mt-4 grid gap-2">
              {cases.map((item) => {
                const isSelected = selectedCase?.id === item.id;
                return (
                  <a
                    key={item.id}
                    href={`/kunden/${customer.id}?case=${item.id}`}
                    className={`rounded-lg border p-3 transition ${
                      isSelected
                        ? "border-[var(--accent)] bg-[var(--surface-soft)]"
                        : "border-[var(--border)] bg-white hover:border-[var(--accent)]"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <FolderOpen size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
                      <div className="min-w-0">
                        <p className="font-bold">{caseLabel(item)}</p>
                        <p className="text-sm text-[var(--muted)]">
                          {item.case_title || "Küchenprojekt"}
                        </p>
                        <p className="text-xs text-[var(--muted)]">
                          {item.status_phase_name || item.case_status}
                        </p>
                      </div>
                    </div>
                  </a>
                );
              })}
              {cases.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Keine Vorgänge zu diesem Kunden.</p>
              ) : null}
            </div>
            <details className="mt-4 rounded-lg border border-[var(--border)] bg-white p-3" open={cases.length === 0}>
              <summary className="cursor-pointer text-sm font-bold">Neuen Vorgang anlegen</summary>
              <form
                className="mt-3 grid gap-3"
                action={`/api/kunden/cases?return_to=/kunden/${customer.id}`}
                method="post"
              >
                <input type="hidden" name="customer_id" value={customer.id} />
                <input type="hidden" name="case_status" value="active" />
                <Label label="Vorgangstitel">
                  <Field name="case_title" placeholder="z. B. Küchenplanung" />
                </Label>
                <Label label="CARAT Vorgangsnummer">
                  <Field
                    name="carat_order_number"
                    pattern="[A-Za-z0-9]{1,5}-[A-Za-z0-9]{1,3}"
                    maxLength={9}
                    placeholder="z. B. 12345-123"
                    title="Maximal 5 Zeichen, Bindestrich, maximal 3 Zeichen"
                  />
                </Label>
                <Label label="Statusphase">
                  <Select name="status_phase_id" defaultValue="1">
                    {state.status_phases.map((phase) => (
                      <option key={phase.phase} value={phase.phase}>
                        {phase.phase}. {phase.name}
                      </option>
                    ))}
                  </Select>
                </Label>
                <Label label="Vorgang verantwortlich">
                  <Select
                    name="responsible_user_id"
                    defaultValue={state.current_user.primary_user_id ? String(state.current_user.primary_user_id) : undefined}
                  >
                    {state.users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {displayName(user.first_name, user.last_name) || user.email}
                      </option>
                    ))}
                  </Select>
                </Label>
                <Button type="submit">Vorgang anlegen</Button>
              </form>
            </details>
          </Panel>
        </aside>

        <main className="min-w-0">
          {selectedCase ? (
            <CaseDesktop
              customerId={customer.id}
              currentUserId={state.current_user.primary_user_id}
              selectedCase={selectedCase}
              selectedCaseTasks={selectedCaseTasks}
              selectedCaseEvents={selectedCaseEvents}
              users={state.users}
              statusPhases={state.status_phases}
              activeRegister={activeRegister ?? registerForPhase(selectedCase.status_phase)}
              returnTo={returnTo}
            />
          ) : (
            <Panel>
              <div className="grid min-h-[520px] place-items-center rounded-lg border border-dashed border-[var(--border)] bg-white p-8 text-center">
                <div className="max-w-lg">
                  <FolderOpen size={36} className="mx-auto text-[var(--accent-strong)]" aria-hidden="true" />
                  <h2 className="mt-3 text-xl font-bold">Desktop</h2>
                  <p className="mt-2 text-sm text-[var(--muted)]">
                    Wählen Sie links einen Vorgang aus dem Regal, um die Projektmappe auf dem Desktop zu öffnen.
                  </p>
                </div>
              </div>
            </Panel>
          )}
        </main>
      </div>
      <div
        data-customer-master-modal
        hidden
        className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="customer-master-title"
      >
        <Panel className="max-h-[92vh] w-full max-w-3xl overflow-y-auto">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="customer-master-title" className="section-title">Kundenstammdaten bearbeiten</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Vollständiges Stammdatenblatt zur geöffneten Kundenakte.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              data-customer-master-close
              aria-label="Stammdatenblatt schließen"
            >
              Schließen
            </button>
          </div>
          <form
            className="mt-4 grid gap-3"
            action={`/api/kunden/customers/${customer.id}?return_to=${encodeURIComponent(selectedCaseReturnPath)}`}
            method="post"
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Kundentyp">
                <Select name="customer_type" defaultValue={customer.customer_type} data-customer-master-type-select>
                  <option value="private">Privatkunde</option>
                  <option value="company">Objektkunde</option>
                </Select>
              </Label>
              <Label label="Kundennummer">
                <Field value={customer.customer_number || "Wird beim Speichern automatisch vergeben"} disabled />
              </Label>
            </div>
            <div data-customer-master-type-section="private" className="grid gap-3">
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Anrede">
                  <Select name="salutation" defaultValue={customer.salutation ?? ""}>
                    <option value="">Keine Angabe</option>
                    <option value="Herr">Herr</option>
                    <option value="Frau">Frau</option>
                    <option value="Divers">Divers</option>
                    <option value="Familie">Familie</option>
                  </Select>
                </Label>
                <Label label="Titel">
                  <Select name="title" defaultValue={customer.title ?? ""}>
                    <option value="">Kein Titel</option>
                    <option value="Dr.">Dr.</option>
                    <option value="Prof.">Prof.</option>
                    <option value="Prof. Dr.">Prof. Dr.</option>
                    <option value="Dipl.-Ing.">Dipl.-Ing.</option>
                    <option value="Mag.">Mag.</option>
                  </Select>
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Vorname">
                  <Field name="first_name" defaultValue={customer.first_name ?? ""} />
                </Label>
                <Label label="Nachname">
                  <Field name="last_name" defaultValue={customer.last_name ?? ""} />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="E-Mail">
                  <Field name="primary_email" type="email" defaultValue={customer.primary_email ?? ""} />
                </Label>
                <Label label="Telefon">
                  <Field name="primary_phone" defaultValue={customer.primary_phone ?? ""} />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-4">
                <Label label="Straße" className="md:col-span-2">
                  <Field name="street" defaultValue={customer.address?.street ?? ""} />
                </Label>
                <Label label="Hausnummer">
                  <Field name="house_number" defaultValue={customer.address?.house_number ?? ""} />
                </Label>
                <Label label="PLZ">
                  <Field name="postal_code" defaultValue={customer.address?.postal_code ?? ""} />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Ort">
                  <Field name="city" defaultValue={customer.address?.city ?? ""} />
                </Label>
                <Label label="Land">
                  <Select
                    name="country"
                    defaultValue={customer.address?.country || customer.country || "DE"}
                    data-customer-master-country-select
                  >
                    <option value="DE">Deutschland</option>
                    <option value="CH">Schweiz</option>
                    <option value="US">USA</option>
                    <option value="AT">Österreich</option>
                    <option value="FR">Frankreich</option>
                    <option value="ZZ">Anderes Land</option>
                  </Select>
                </Label>
              </div>
            </div>
            <div data-customer-master-type-section="company" className="grid gap-3">
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Firma">
                  <Field name="company_name" defaultValue={customer.company_name ?? ""} />
                </Label>
                <Label label="Objektkunden-Art">
                  <Select name="object_customer_label" defaultValue={sectionValue(customer.file_sections?.customer_profile, "object_customer_label")}>
                    <option value="">Bitte wählen</option>
                    <option value="architect">Architekt</option>
                    <option value="developer">Bauträger</option>
                    <option value="company">Firma</option>
                    <option value="partner">Partner</option>
                    <option value="joinery">Schreinerei</option>
                    <option value="contractor">Handwerker</option>
                    <option value="other">Sonstiges</option>
                  </Select>
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="E-Mail">
                  <Field name="primary_email" type="email" defaultValue={customer.primary_email ?? ""} />
                </Label>
                <Label label="Telefon">
                  <Field name="primary_phone" defaultValue={customer.primary_phone ?? ""} />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-4">
                <Label label="Straße" className="md:col-span-2">
                  <Field name="street" defaultValue={customer.address?.street ?? ""} />
                </Label>
                <Label label="Hausnummer">
                  <Field name="house_number" defaultValue={customer.address?.house_number ?? ""} />
                </Label>
                <Label label="PLZ">
                  <Field name="postal_code" defaultValue={customer.address?.postal_code ?? ""} />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Ort">
                  <Field name="city" defaultValue={customer.address?.city ?? ""} />
                </Label>
                <Label label="Land">
                  <Select
                    name="country"
                    defaultValue={customer.address?.country || customer.country || "DE"}
                    data-customer-master-country-select
                  >
                    <option value="DE">Deutschland</option>
                    <option value="CH">Schweiz</option>
                    <option value="US">USA</option>
                    <option value="AT">Österreich</option>
                    <option value="FR">Frankreich</option>
                    <option value="ZZ">Anderes Land</option>
                  </Select>
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Rechtsform">
                  <Field name="legal_form" defaultValue={sectionValue(customer.file_sections?.legal_tax, "legal_form")} />
                </Label>
                <Label label="USt-IdNr.">
                  <Field name="vat_id" defaultValue={sectionValue(customer.file_sections?.legal_tax, "vat_id")} />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Handelsregisternummer">
                  <Field name="registry_number" defaultValue={sectionValue(customer.file_sections?.legal_tax, "registry_number")} />
                </Label>
                <Label label="Registergericht">
                  <Field name="registry_court" defaultValue={sectionValue(customer.file_sections?.legal_tax, "registry_court")} />
                </Label>
              </div>
              <Label label="Steuernummer">
                <Field name="tax_number" defaultValue={sectionValue(customer.file_sections?.legal_tax, "tax_number")} />
              </Label>
              <div className="grid gap-3 border-t border-[var(--border)] pt-3">
                <h3 className="section-title">Ansprechpartner</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <Label label="Vorname">
                    <Field name="contact_first_name" defaultValue={sectionValue(customer.file_sections?.customer_profile, "contact_first_name")} />
                  </Label>
                  <Label label="Nachname">
                    <Field name="contact_last_name" defaultValue={sectionValue(customer.file_sections?.customer_profile, "contact_last_name")} />
                  </Label>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Label label="E-Mail Ansprechpartner">
                    <Field name="contact_email" type="email" defaultValue={sectionValue(customer.file_sections?.customer_profile, "contact_email")} />
                  </Label>
                  <Label label="Telefon Ansprechpartner">
                    <Field name="contact_phone" defaultValue={sectionValue(customer.file_sections?.customer_profile, "contact_phone")} />
                  </Label>
                </div>
              </div>
            </div>
            <Label label="Steuerbehandlung">
              <Select
                name="tax_treatment"
                defaultValue={customer.tax_treatment ?? "standard_de"}
                data-customer-master-tax-treatment
              >
                <option value="standard_de">Deutschland Standard</option>
                <option value="eu_business">EU-Unternehmen mit USt-IdNr.</option>
                <option value="third_country_export">Drittland / Ausfuhr prüfen</option>
                <option value="switzerland_export">Schweiz / Ausfuhr prüfen</option>
                <option value="nato_forces">NATO / US-Streitkräfte prüfen</option>
                <option value="custom">Abweichend / manuell prüfen</option>
              </Select>
            </Label>
            <div
              data-customer-master-custom-vat
              className="grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3 md:grid-cols-2"
              hidden
            >
              <input
                type="hidden"
                name="has_custom_vat"
                value={customer.has_custom_vat ? "true" : "false"}
                data-customer-master-custom-vat-flag
              />
              <Label label="Abweichender Mehrwertsteuersatz">
                <Field
                  name="custom_vat_rate"
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  placeholder="z. B. 8,10"
                  required
                  disabled
                  defaultValue={customer.custom_vat_rate ?? ""}
                  data-customer-master-custom-vat-rate
                />
              </Label>
              <Label label="Bezeichnung">
                <Select
                  name="custom_vat_rate_label"
                  defaultValue={customer.custom_vat_rate_label ?? ""}
                  disabled
                  data-customer-master-custom-vat-label
                >
                  <option value="">Bitte wählen</option>
                  <option value="Schweiz Normalsatz">Schweiz Normalsatz</option>
                  <option value="Schweiz reduzierter Satz">Schweiz reduzierter Satz</option>
                  <option value="Schweiz Sondersatz">Schweiz Sondersatz</option>
                  <option value="Individuell">Individuell</option>
                </Select>
              </Label>
            </div>
            <Label label="Hinweis zur Steuerbehandlung">
              <Textarea
                name="tax_treatment_note"
                defaultValue={customer.tax_treatment_note ?? ""}
                placeholder="z. B. Ausfuhrnachweis erforderlich, NATO-Bescheinigung prüfen"
              />
            </Label>
            <Label label="Zuständig">
              <Select name="owner_user_id" defaultValue={customer.owner_user_id ? String(customer.owner_user_id) : undefined}>
                {state.users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {displayName(user.first_name, user.last_name) || user.email}
                  </option>
                ))}
              </Select>
            </Label>
            <Label label="Notizen">
              <Textarea name="notes" defaultValue={customer.notes ?? ""} />
            </Label>
            <Button type="submit">Stammdaten speichern</Button>
          </form>
        </Panel>
      </div>
      <Script src="/customer-search.v1.js" strategy="afterInteractive" />
      <Script id="carat-supplier-select-all" strategy="afterInteractive">
        {`
          function syncCaratSupplierToggle(group) {
            const toggle = group.querySelector("[data-carat-supplier-toggle]");
            const boxes = Array.from(group.querySelectorAll("[data-carat-position-checkbox]"));
            if (!toggle || boxes.length === 0) return;
            const checkedCount = boxes.filter((box) => box.checked).length;
            toggle.checked = checkedCount === boxes.length;
            toggle.indeterminate = checkedCount > 0 && checkedCount < boxes.length;
          }

          document.addEventListener("change", (event) => {
            const target = event.target;
            if (!(target instanceof HTMLInputElement)) return;

            const supplierToggle = target.closest("[data-carat-supplier-toggle]");
            if (supplierToggle) {
              const group = supplierToggle.closest("[data-carat-supplier-group]");
              if (!group) return;
              group.querySelectorAll("[data-carat-position-checkbox]").forEach((box) => {
                box.checked = supplierToggle.checked;
              });
              supplierToggle.indeterminate = false;
              return;
            }

            const positionCheckbox = target.closest("[data-carat-position-checkbox]");
            if (positionCheckbox) {
              const group = positionCheckbox.closest("[data-carat-supplier-group]");
              if (group) syncCaratSupplierToggle(group);
            }
          });
        `}
      </Script>
    </div>
  );
}

function CaseDesktop({
  customerId,
  currentUserId,
  selectedCase,
  selectedCaseTasks,
  selectedCaseEvents,
  users,
  statusPhases,
  activeRegister,
  returnTo,
}: {
  customerId: number;
  currentUserId: number | null;
  selectedCase: CustomerCaseRecord;
  selectedCaseTasks: Awaited<ReturnType<typeof fetchOverviewState>>["tasks"];
  selectedCaseEvents: NonNullable<
    Awaited<ReturnType<typeof fetchOverviewState>>["communication_events"]
  >;
  users: Awaited<ReturnType<typeof fetchCustomersState>>["users"];
  statusPhases: Awaited<ReturnType<typeof fetchCustomersState>>["status_phases"];
  activeRegister: CaseDesktopRegisterKey;
  returnTo: string;
}) {
  const projectObjects = selectedCase.sections?.project_objects;
  const projectContacts = selectedCase.sections?.project_contacts;
  const documents = selectedCase.sections?.documents;
  const caseDocuments = selectedCase.documents ?? [];
  const caratImports = selectedCase.carat_imports ?? [];
  const latestCurrentCaratDocument = caseDocuments.find(
    (document) =>
      document.document_type === "carat_project" &&
      document.document_status !== "archived" &&
      document.is_current_version,
  );
  const supplierOrders = selectedCase.supplier_orders ?? [];
  const supplierConfirmations = selectedCase.supplier_order_confirmations ?? [];
  const openSupplierConfirmations = supplierConfirmations.filter((confirmation) =>
    ["exceptions_open", "context_revision_required", "suspended"].includes(confirmation.status),
  );
  const openConfirmationExceptionCount = supplierConfirmations.reduce(
    (count, confirmation) =>
      count + confirmation.exceptions.filter((exception) => exception.status === "open").length,
    0,
  );
  const processControl = selectedCase.sections?.process_control;
  const activeTaskCount = selectedCaseTasks.filter((task) => task.status !== "done").length;
  const currentPhase = selectedCase.status_phase ?? 1;
  const phaseRegister = registerForPhase(currentPhase);
  const registerMeta =
    activeRegister === DOCUMENTS_REGISTER.key
      ? DOCUMENTS_REGISTER
      : CASE_REGISTERS.find((register) => register.key === activeRegister) ?? CASE_REGISTERS[0];
  const hasRegisterAside = ["abwicklung", "kommunikation", "rechnung_abschluss"].includes(activeRegister);

  return (
    <div className="grid gap-4">
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="badge">Geöffnete Vorgangsmappe</p>
            <h2 className="mt-2 text-2xl font-bold">{selectedCase.case_title || "Küchenprojekt"}</h2>
            <p className="text-sm text-[var(--muted)]">
              {caseLabel(selectedCase)} · {selectedCase.status_phase_name || selectedCase.case_status}
              {selectedCase.carat_order_number ? ` · CARAT ${selectedCase.carat_order_number}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <LinkButton href={`/kunden/${customerId}`}>Vorgang schließen</LinkButton>
            <a className="btn btn-secondary" href="#telefonnotiz">
              <Phone size={16} aria-hidden="true" />
              Telefonnotiz
            </a>
            <a className="btn btn-secondary" href="#emailentwurf">
              <Mail size={16} aria-hidden="true" />
              E-Mail
            </a>
          </div>
        </div>

        <form
          className="mt-5 grid gap-3 lg:grid-cols-4"
          action={`/api/kunden/cases/${selectedCase.id}?return_to=${returnTo}`}
          method="post"
        >
          <input type="hidden" name="case_status" value={selectedCase.case_status} />
          <Label label="Vorgangstitel">
            <Field name="case_title" defaultValue={selectedCase.case_title ?? ""} />
          </Label>
          <Label label="CARAT Vorgangsnummer">
            <Field
              name="carat_order_number"
              pattern="[A-Za-z0-9]{1,5}-[A-Za-z0-9]{1,3}"
              placeholder="12345-123"
              defaultValue={selectedCase.carat_order_number ?? ""}
            />
          </Label>
          <Label label="Ablaufphase">
            <Select name="status_phase_id" defaultValue={selectedCase.status_phase ?? 1}>
              {statusPhases.map((phase) => (
                <option key={phase.phase} value={phase.phase}>
                  {phase.name}
                </option>
              ))}
            </Select>
          </Label>
          <Label label="Vorgang verantwortlich">
            <Select name="responsible_user_id" defaultValue={currentUserId ?? ""}>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {displayName(user.first_name, user.last_name) || user.email}
                </option>
              ))}
            </Select>
          </Label>
          <div className="lg:col-span-4">
            <Button type="submit">Vorgang speichern</Button>
          </div>
        </form>
      </Panel>

      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="section-title">Register</h3>
            <p className="mt-1 text-sm text-[var(--muted)]">{registerMeta.description}</p>
          </div>
          <span className="badge">
            Aktuell: {selectedCase.status_phase_name || `Phase ${currentPhase}`}
          </span>
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {CASE_REGISTERS.map((register) => {
            const isActive = register.key === activeRegister;
            const isPhaseRegister = register.key === phaseRegister;
            const isPast = register.phaseRange[1] < currentPhase;
            const isFuture = register.phaseRange[0] > currentPhase;
            return (
              <a
                key={register.key}
                href={`/kunden/${customerId}?case=${selectedCase.id}&register=${register.key}`}
                className={`rounded-lg border p-3 text-sm transition ${
                  isActive
                    ? "border-[var(--accent)] bg-[var(--surface-soft)]"
                    : "border-[var(--border)] bg-white hover:border-[var(--accent)]"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold">{register.label}</span>
                  {isPhaseRegister ? <span className="badge">Status</span> : null}
                </div>
                <p className="mt-2 text-xs text-[var(--muted)]">
                  {isPast ? "Vergangenheit" : isFuture ? "Zukunft" : "Aktueller Bereich"}
                </p>
              </a>
            );
          })}
          <a
            href={`/kunden/${customerId}?case=${selectedCase.id}&register=${DOCUMENTS_REGISTER.key}`}
            className={`rounded-lg border p-3 text-sm transition ${
              activeRegister === DOCUMENTS_REGISTER.key
                ? "border-[var(--accent)] bg-[var(--surface-soft)]"
                : "border-[var(--border)] bg-white hover:border-[var(--accent)]"
            }`}
            aria-label="Dokumentenbereich öffnen"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-2 font-bold text-[var(--foreground)]">
                <FileText size={16} aria-hidden="true" />
                {DOCUMENTS_REGISTER.label}
              </span>
            </div>
            <p className="mt-2 text-xs">
              Hochladen, herunterladen und per E-Mail versenden.
            </p>
          </a>
        </div>
      </Panel>

      <div className={`grid gap-4 ${hasRegisterAside ? "2xl:grid-cols-[1fr_360px]" : ""}`}>
        <div className="grid gap-4">
          {activeRegister === "anfrage" ? (
          <Panel>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <ClipboardList size={18} aria-hidden="true" />
                  <h3 className="section-title">Projektgrundlagen</h3>
                </div>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Erste Einordnung der Anfrage, Terminlage und vorhandenen Unterlagen.
                </p>
              </div>
            </div>
            <form
              className="mt-5 grid gap-6"
              action={`/api/kunden/cases/${selectedCase.id}/sections/project_objects?return_to=${returnTo}`}
              method="post"
            >
              <fieldset className="grid gap-3">
                <legend className="text-sm font-bold">Projektart</legend>
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  {PROJECT_OBJECTS.map(([key, label]) => (
                    <label key={key} className="flex min-h-10 items-center gap-2 rounded-lg border border-[var(--border)] bg-white px-3 text-sm font-bold">
                      <input
                        type="checkbox"
                        name={key}
                        defaultChecked={sectionChecked(projectObjects, key)}
                        data-project-object-other={key === "project_object_other" ? "true" : undefined}
                      />
                      {label}
                    </label>
                  ))}
                </div>
                <div
                  className="mt-3"
                  data-project-object-other-note
                  hidden={!sectionChecked(projectObjects, "project_object_other")}
                >
                  <Label label="Sonstiges genauer beschreiben">
                    <Textarea
                      name="project_object_other_note"
                      defaultValue={sectionValue(projectObjects, "project_object_other_note")}
                      placeholder="z. B. Dienstleistung, Sondermöbel oder weitere Projektart"
                    />
                  </Label>
                </div>
              </fieldset>

              <fieldset className="grid gap-3 border-t border-[var(--border)] pt-4">
                <legend className="text-sm font-bold">Objekt und Montageort</legend>
                <div className="grid gap-3 lg:grid-cols-4">
                  <Label label="Objekt / Immobilie" className="lg:col-span-2">
                    <Field
                      name="property_label"
                      defaultValue={sectionValue(projectObjects, "property_label")}
                      placeholder="z. B. Wohnung Stuttgart"
                    />
                  </Label>
                  <Label label="Situation">
                    <Select
                      name="project_situation"
                      defaultValue={sectionValue(projectObjects, "project_situation")}
                    >
                      {PROJECT_SITUATIONS.map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </Select>
                  </Label>
                  <Label label="Liefer-/Montageort PLZ">
                    <Field
                      name="delivery_postal_code"
                      defaultValue={sectionValue(projectObjects, "delivery_postal_code")}
                      inputMode="numeric"
                      placeholder="z. B. 70173"
                    />
                  </Label>
                  <Label label="Liefer-/Montageort Ort" className="lg:col-span-2">
                    <Field
                      name="delivery_city"
                      defaultValue={sectionValue(projectObjects, "delivery_city")}
                      placeholder="z. B. Stuttgart"
                    />
                  </Label>
                </div>
              </fieldset>

              <fieldset className="grid gap-3 border-t border-[var(--border)] pt-4">
                <legend className="text-sm font-bold">Zeit und Dringlichkeit</legend>
                <div className="grid gap-3 lg:grid-cols-4">
                  <Label label="Gewünschter Zeitraum" className="lg:col-span-2">
                    <Field
                      name="desired_timeline"
                      defaultValue={sectionValue(projectObjects, "desired_timeline")}
                      placeholder="z. B. Herbst, KW 42, noch offen"
                    />
                  </Label>
                  <Label label="Dringlichkeit">
                    <span className="flex items-center gap-2">
                      <span className="min-w-0 flex-1">
                        <Select
                          name="urgency"
                          defaultValue={sectionValue(projectObjects, "urgency")}
                        >
                          {PROJECT_URGENCIES.map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </Select>
                      </span>
                      <UrgencyInfoTooltip />
                    </span>
                  </Label>
                  <Label label="Erster Termin gewünscht">
                    <Select
                      name="first_appointment_wanted"
                      defaultValue={sectionValue(projectObjects, "first_appointment_wanted")}
                    >
                      <option value="">Bitte wählen</option>
                      <option value="yes">Ja</option>
                      <option value="no">Nein</option>
                      <option value="open">Noch offen</option>
                    </Select>
                  </Label>
                  <Label label="Grund für Terminwunsch" className="lg:col-span-4">
                    <Field
                      name="timeline_reason"
                      defaultValue={sectionValue(projectObjects, "timeline_reason")}
                      placeholder="z. B. Umzug, Übergabe, Wasserschaden"
                    />
                  </Label>
                </div>
              </fieldset>

              <fieldset className="grid gap-3 border-t border-[var(--border)] pt-4">
                <legend className="text-sm font-bold">Budget und Herkunft</legend>
                <div className="grid gap-3 lg:grid-cols-4">
                  <Label label="Budgetrahmen">
                    <Select
                      name="budget_range"
                      defaultValue={sectionValue(projectObjects, "budget_range")}
                      data-budget-range-select
                    >
                      {BUDGET_RANGES.map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </Select>
                  </Label>
                  <Label label="Budget besprochen">
                    <Select
                      name="budget_discussed"
                      defaultValue={sectionValue(projectObjects, "budget_discussed")}
                    >
                      <option value="">Bitte wählen</option>
                      <option value="yes">Ja</option>
                      <option value="no">Nein</option>
                    </Select>
                  </Label>
                  <Label label="Kontaktweg">
                    <Select
                      name="inquiry_source"
                      defaultValue={sectionValue(projectObjects, "inquiry_source")}
                    >
                      {INQUIRY_SOURCES.map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </Select>
                  </Label>
                  <Label label="Empfehlung / Quelle">
                    <Field
                      name="referral_source"
                      defaultValue={sectionValue(projectObjects, "referral_source")}
                      placeholder="z. B. Name, Anzeige, Google"
                    />
                  </Label>
                </div>
                <div
                  className="mt-3"
                  data-budget-range-other-note
                  hidden={sectionValue(projectObjects, "budget_range") !== "other"}
                >
                  <Label label="Sonstiges Budget genauer beschreiben">
                    <Textarea
                      name="budget_range_other_note"
                      defaultValue={sectionValue(projectObjects, "budget_range_other_note")}
                      placeholder="z. B. aufgeteilt nach Küche, Vorratsraum, Montage oder weiteren Bereichen"
                    />
                  </Label>
                </div>
              </fieldset>

              <fieldset className="grid gap-3 border-t border-[var(--border)] pt-4">
                <legend className="text-sm font-bold">Vorhandene Unterlagen</legend>
                <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                  {[
                    ["has_floor_plan", "Grundriss"],
                    ["has_measurements", "Maße"],
                    ["has_photos", "Fotos"],
                    ["has_architect_plan", "Architektenplan"],
                  ].map(([key, label]) => (
                    <label key={key} className="flex min-h-10 items-center gap-2 rounded-lg border border-[var(--border)] bg-white px-3 text-sm font-bold">
                      <input
                        type="checkbox"
                        name={key}
                        defaultChecked={sectionChecked(projectObjects, key)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </fieldset>

              <fieldset className="grid gap-3 border-t border-[var(--border)] pt-4 lg:grid-cols-2">
                <legend className="text-sm font-bold">Notizen</legend>
                <Label label="Wunsch / Anlass">
                  <Textarea
                    name="planning_notes"
                    defaultValue={sectionValue(projectObjects, "planning_notes")}
                    placeholder="Kurze Zusammenfassung aus dem ersten Kontakt"
                  />
                </Label>
                <Label label="Interne Notiz für den ersten Termin">
                  <Textarea
                    name="intake_notes"
                    defaultValue={sectionValue(projectObjects, "intake_notes")}
                  />
                </Label>
              </fieldset>
              <div className="flex justify-end">
                <Button type="submit">Projektgrundlagen speichern</Button>
              </div>
            </form>
          </Panel>
          ) : null}

          {activeRegister === "planung" ? (
          <Panel>
            <div className="flex items-center gap-2">
              <ClipboardList size={18} aria-hidden="true" />
              <h3 className="section-title">Projektobjekte / Planung</h3>
            </div>
            <form
              className="mt-4 grid gap-4"
              action={`/api/kunden/cases/${selectedCase.id}/sections/project_objects?return_to=${returnTo}`}
              method="post"
            >
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                {PROJECT_OBJECTS.map(([key, label]) => (
                  <label key={key} className="flex min-h-10 items-center gap-2 rounded-lg border border-[var(--border)] bg-white px-3 text-sm font-bold">
                    <input
                      type="checkbox"
                      name={key}
                      defaultChecked={sectionChecked(projectObjects, key)}
                    />
                    {label}
                  </label>
                ))}
              </div>
              <div className="grid gap-3 lg:grid-cols-2">
                <Label label="Objekt / Immobilie">
                  <Field
                    name="property_label"
                    defaultValue={sectionValue(projectObjects, "property_label")}
                    placeholder="z. B. Wohnung Stuttgart"
                  />
                </Label>
                <Label label="Liefer-/Montageort">
                  <Field
                    name="delivery_address"
                    defaultValue={sectionValue(projectObjects, "delivery_address")}
                  />
                </Label>
              </div>
              <Label label="Projektbeschreibung">
                <Textarea
                  name="planning_notes"
                  defaultValue={sectionValue(projectObjects, "planning_notes")}
                />
              </Label>
              <Button type="submit">Planung speichern</Button>
            </form>
          </Panel>
          ) : null}

          {activeRegister === "beratung" ? (
          <Panel>
            <div className="flex items-center gap-2">
              <MessageSquareText size={18} aria-hidden="true" />
              <h3 className="section-title">Kontakte im Vorgang</h3>
            </div>
            <form
              className="mt-4 grid gap-3"
              action={`/api/kunden/cases/${selectedCase.id}/sections/project_contacts?return_to=${returnTo}`}
              method="post"
            >
              <label className="flex items-center gap-2 text-sm font-bold">
                <input
                  type="checkbox"
                  name="primary_contact_same_as_master"
                  defaultChecked={sectionChecked(projectContacts, "primary_contact_same_as_master")}
                />
                Ansprechpartner entspricht Stammdaten
              </label>
              <div className="grid gap-3 lg:grid-cols-4">
                <Label label="Kontaktart">
                  <Select
                    name="contact_role"
                    defaultValue={sectionValue(projectContacts, "contact_role")}
                  >
                    <option value="">Bitte wählen</option>
                    {CONTACT_ROLES.map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Label>
                <Label label="Name">
                  <Field
                    name="contact_name"
                    defaultValue={sectionValue(projectContacts, "contact_name")}
                  />
                </Label>
                <Label label="E-Mail">
                  <Field
                    name="contact_email"
                    defaultValue={sectionValue(projectContacts, "contact_email")}
                  />
                </Label>
                <Label label="Telefon">
                  <Field
                    name="contact_phone"
                    defaultValue={sectionValue(projectContacts, "contact_phone")}
                  />
                </Label>
              </div>
              <Label label="Kontaktvermerk">
                <Textarea
                  name="contact_notes"
                  defaultValue={sectionValue(projectContacts, "contact_notes")}
                />
              </Label>
              <Button type="submit">Kontaktbereich speichern</Button>
            </form>
          </Panel>
          ) : null}

          {activeRegister === "abwicklung" ? (
          <>
          <Panel>
            <div className="flex items-center gap-2">
              <CheckSquare size={18} aria-hidden="true" />
              <h3 className="section-title">Aufgaben</h3>
            </div>
            <form
              className="mt-4 grid gap-3 lg:grid-cols-[1fr_180px_180px_auto]"
              action={`/api/overview/tasks?return_to=${returnTo}`}
              method="post"
            >
              <input type="hidden" name="related_case_id" value={selectedCase.id} />
              <Label label="Aufgabe">
                <Field name="title" required />
              </Label>
              <Label label="Fällig">
                <Field name="due_at" type="datetime-local" />
              </Label>
              <Label label="Priorität">
                <Select name="priority" defaultValue="normal">
                  <option value="low">Niedrig</option>
                  <option value="normal">Normal</option>
                  <option value="high">Hoch</option>
                  <option value="urgent">Dringend</option>
                </Select>
              </Label>
              <div className="flex items-end">
                <Button type="submit">Anlegen</Button>
              </div>
            </form>
            <div className="mt-4 grid gap-2">
              {selectedCaseTasks.slice(0, 6).map((task) => (
                <div key={task.id} className="rounded-lg border border-[var(--border)] bg-white p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-bold">{task.title}</p>
                    <span className="badge">{task.status_name}</span>
                  </div>
                  <p className="text-sm text-[var(--muted)]">
                    {task.due_at ? `Fällig ${formatDateTime(task.due_at)}` : "Ohne Fälligkeit"}
                  </p>
                </div>
              ))}
              {selectedCaseTasks.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Keine Aufgaben in diesem Vorgang.</p>
              ) : null}
            </div>
          </Panel>
          <Panel>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <ClipboardList size={18} aria-hidden="true" />
                  <h3 className="section-title">CARAT-Importe</h3>
                </div>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  PRJZ-Projektdateien werden hier importiert und automatisch analysiert. Positionen werden erst nach Auswahl übernommen.
                </p>
              </div>
              <form
                className="grid min-w-[min(100%,420px)] gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3"
                action={`/api/kunden/cases/${selectedCase.id}/documents?return_to=${returnTo}`}
                encType="multipart/form-data"
                method="post"
              >
                <input type="hidden" name="document_category" value="order_processing" />
                <input type="hidden" name="document_type" value="carat_project" />
                <input type="hidden" name="document_status" value="received" />
                <input type="hidden" name="version_label" value="1" />
                <input type="hidden" name="title" value="CARAT-Projektdatei" />
                <div className="grid gap-2 text-sm">
                  <label className="flex items-start gap-2 rounded-lg border border-[var(--border)] bg-white px-3 py-2">
                    <input
                      className="mt-1"
                      type="radio"
                      name="carat_upload_mode"
                      value="new_version"
                      defaultChecked
                    />
                    <span>
                      <span className="block font-bold text-[var(--text)]">Als neue Version hochladen</span>
                      <span className="block text-xs text-[var(--muted)]">
                        Der bestehende CARAT-Import bleibt sichtbar.
                      </span>
                    </span>
                  </label>
                  {latestCurrentCaratDocument ? (
                    <label className="flex items-start gap-2 rounded-lg border border-[var(--border)] bg-white px-3 py-2">
                      <input
                        className="mt-1"
                        type="radio"
                        name="carat_upload_mode"
                        value="replace_latest"
                      />
                      <span>
                        <span className="block font-bold text-[var(--text)]">
                          Vorherigen CARAT-Import ersetzen
                        </span>
                        <span className="block text-xs text-[var(--muted)]">
                          Der bisher aktuelle Import wird ersetzt und nicht mehr im Cockpit angezeigt.
                        </span>
                      </span>
                    </label>
                  ) : null}
                </div>
                <Label label="CARAT-Projektdatei">
                  <Field
                    className="bg-white"
                    name="file"
                    type="file"
                    accept=".prjz,application/zip,application/x-zip-compressed,application/octet-stream"
                    required
                  />
                </Label>
                <div className="flex justify-end">
                  <Button type="submit">
                    <Upload size={16} aria-hidden="true" />
                    CARAT importieren
                  </Button>
                </div>
              </form>
            </div>
            <div className="mt-4 grid gap-3">
              {caratImports.map((caratImport) => {
                const exportablePositions = caratImport.positions.filter(isExportableCaratPosition);
                const skippedPositionCount = caratImport.positions.length - exportablePositions.length;
                const selectedCount = exportablePositions.filter(
                  (position) => position.selection_status === "selected",
                ).length;
                const transferredCount = exportablePositions.filter(
                  (position) => position.selection_status === "transferred",
                ).length;
                const supplierNames = Array.from(
                  new Set(
                    exportablePositions.map(
                      (position) => position.supplier_name || "Ohne Lieferant",
                    ),
                  ),
                );
                return (
                  <form
                    key={caratImport.id}
                    className="rounded-lg border border-[var(--border)] bg-white p-3"
                    action={`/api/kunden/cases/${selectedCase.id}/carat-imports/${caratImport.id}/positions?return_to=${returnTo}`}
                    method="post"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-bold">
                          {caratImport.source_filename || `CARAT-Import ${caratImport.id}`}
                        </p>
                        <p className="mt-1 text-xs text-[var(--muted)]">
                          {caratImport.project_number ? `Projekt ${caratImport.project_number}` : "Projekt ohne Nummer"}
                          {caratImport.carat_version ? ` · ${caratImport.carat_version}` : ""}
                          {caratImport.customer_name ? ` · ${caratImport.customer_name}` : ""}
                          {caratImport.created_at ? ` · ${caratImport.created_at}` : ""}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className="badge">{caratImport.supplier_count} Lieferanten</span>
                        <span className="badge">{exportablePositions.length} exportierbare Positionen</span>
                        <span className="badge">{transferredCount} übernommen</span>
                        {selectedCount > 0 ? <span className="badge">{selectedCount} markiert</span> : null}
                        {skippedPositionCount > 0 ? (
                          <span className="badge">{skippedPositionCount} Bilddaten nicht exportiert</span>
                        ) : null}
                      </div>
                    </div>
                    {skippedPositionCount > 0 ? (
                      <p className="mt-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-900">
                        Bilddaten wie Wand- oder Deckenpositionen werden nicht in Bestellungen übernommen.
                      </p>
                    ) : null}
                    <div className="mt-3 grid gap-3">
                      {supplierNames.map((supplierName) => {
                        const positions = exportablePositions.filter(
                          (position) => (position.supplier_name || "Ohne Lieferant") === supplierName,
                        );
                        return (
                          <div
                            key={`${caratImport.id}-${supplierName}`}
                            data-carat-supplier-group
                            className="rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-sm font-bold">{supplierName}</p>
                              <div className="flex flex-wrap items-center gap-2">
                                <label className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-white px-3 py-1 text-xs font-bold text-[var(--muted)]">
                                  <input type="checkbox" data-carat-supplier-toggle />
                                  Alles markieren
                                </label>
                                <span className="badge">{positions.length} Positionen</span>
                              </div>
                            </div>
                            <div className="mt-2 grid gap-2">
                              {positions.map((position) => {
                                const dimensions = displayDimensions(position.dimensions);
                                return (
                                  <label
                                    key={position.id}
                                    className="grid gap-3 rounded-lg border border-[var(--border)] bg-white p-3 text-sm lg:grid-cols-[auto_minmax(0,1fr)_auto]"
                                  >
                                    <input
                                      className="mt-1"
                                      type="checkbox"
                                      name={`position_${position.id}`}
                                      data-carat-position-checkbox
                                    />
                                    <span className="min-w-0">
                                      <span className="block text-sm font-bold leading-snug text-[var(--text)]">
                                        {position.position_number ? `Pos. ${position.position_number} · ` : ""}
                                        {position.title}
                                      </span>
                                      <span className="mt-2 flex flex-wrap gap-2 text-xs text-[var(--muted)]">
                                        {position.article_code ? (
                                          <span className="badge font-mono">{position.article_code}</span>
                                        ) : null}
                                        <span className="badge">{displayImportQuantity(position.quantity)}</span>
                                        {dimensions ? <span className="badge">{dimensions} mm</span> : null}
                                      </span>
                                      {position.description ? (
                                        <span className="mt-2 line-clamp-3 block text-xs leading-relaxed text-[var(--muted)]">
                                          {position.description}
                                        </span>
                                      ) : null}
                                    </span>
                                    <span className="badge h-fit">
                                      {position.selection_status === "transferred"
                                        ? "Übernommen"
                                        : position.selection_status === "selected"
                                          ? "Markiert"
                                          : "Kandidat"}
                                    </span>
                                  </label>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 flex flex-wrap justify-end gap-2 border-t border-[var(--border)] pt-3">
                      <Button type="submit" name="carat_action" value="reset" variant="secondary">
                        Ausgewählte Positionen zurücksetzen
                      </Button>
                      <Button type="submit" name="carat_action" value="transfer">
                        Ausgewählte Positionen übernehmen
                      </Button>
                    </div>
                  </form>
                );
              })}
              {caratImports.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[var(--border)] bg-white p-4 text-sm text-[var(--muted)]">
                  Noch kein CARAT-Import in diesem Vorgang. Laden Sie eine PRJZ-Datei direkt hier hoch.
                </div>
              ) : null}
            </div>
          </Panel>
          <Panel>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <AlertTriangle size={18} aria-hidden="true" />
                  <h3 className="section-title">AB-Cockpit</h3>
                </div>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Lieferanten-ABs werden gegen die übernommenen CARAT-Bestellpositionen geprüft. Nur 1:1-Übereinstimmungen werden grün.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="badge">{supplierOrders.length} Bestellungen</span>
                <span className="badge">{openSupplierConfirmations.length} offene ABs</span>
                <span className="badge">{openConfirmationExceptionCount} offene Abweichungen</span>
              </div>
            </div>

            <form
              className="mt-4 grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3"
              action={`/api/kunden/cases/${selectedCase.id}/confirmations?return_to=${returnTo}`}
              method="post"
            >
              <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_180px]">
                <Label label="Bestellung">
                  <Select name="supplier_order_id" required>
                    <option value="">Bitte wählen</option>
                    {supplierOrders.map((order) => (
                      <option key={order.id} value={order.id}>
                        {order.supplier_name} · {order.order_number || order.title} · {order.ordered_position_count} Pos.
                      </option>
                    ))}
                  </Select>
                </Label>
                <Label label="AB-Nummer">
                  <Field name="confirmation_number" placeholder="optional" />
                </Label>
                <Label label="AB-Dokument">
                  <Select name="document_id" defaultValue="">
                    <option value="">Ohne Dokument</option>
                    {caseDocuments
                      .filter((document) => document.document_category === "order_processing")
                      .map((document) => (
                        <option key={document.id} value={document.id}>
                          {document.title}
                        </option>
                      ))}
                  </Select>
                </Label>
              </div>
              <Label label="AB-Positionen">
                <Textarea
                  name="confirmation_positions"
                  className="min-h-32 font-mono text-xs"
                  placeholder={"Artikelnummer | Titel | Menge | Netto-Preis | Liefer-KW | Lieferdatum YYYY-MM-DD | Beschreibung\nB123 | Unterschrank | 1 | 850,00 | KW 30 | 2026-07-22 | optional"}
                  required
                />
              </Label>
              <div className="flex justify-end">
                <Button type="submit">AB prüfen</Button>
              </div>
            </form>

            <div className="mt-4 grid gap-3">
              {supplierConfirmations.map((confirmation) => {
                const redCount = confirmation.exceptions.filter(
                  (exception) => exception.status === "open" && exception.severity === "red",
                ).length;
                const yellowCount = confirmation.exceptions.filter(
                  (exception) => exception.status === "open" && exception.severity === "yellow",
                ).length;
                const matchRate = Math.round(Number(confirmation.match_rate || 0) * 100);
                return (
                  <div key={confirmation.id} className="rounded-lg border border-[var(--border)] bg-white p-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`rounded-md border px-2 py-1 text-xs font-bold ${severityClass(redCount > 0 ? "red" : yellowCount > 0 ? "yellow" : "green")}`}>
                            {redCount > 0 ? `${redCount} rot` : yellowCount > 0 ? `${yellowCount} gelb` : "grün"}
                          </span>
                          <span className="badge">{confirmationStatusLabel(confirmation.status)}</span>
                          <span className="badge">{matchRate}% Match</span>
                        </div>
                        <p className="mt-2 font-bold">
                          {confirmation.supplier_name} · {confirmation.confirmation_number || `AB #${confirmation.id}`}
                        </p>
                        <p className="mt-1 text-xs text-[var(--muted)]">
                          {confirmation.matched_position_count}/{confirmation.ordered_position_count} Bestellpositionen gematcht · {confirmation.created_at}
                        </p>
                      </div>
                    </div>

                    <div className="mt-3 grid gap-2">
                      {confirmation.positions.map((position) => (
                        <div key={position.id} className="rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3 text-sm">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="font-bold">
                                {position.position_number ? `Pos. ${position.position_number} · ` : ""}
                                {position.title}
                              </p>
                              <p className="mt-1 text-xs text-[var(--muted)]">
                                {[position.article_code, displayImportQuantity(position.quantity), position.confirmed_net_price ? `Netto ${position.confirmed_net_price}` : "", position.confirmed_delivery_week || position.confirmed_delivery_date || ""].filter(Boolean).join(" · ")}
                              </p>
                            </div>
                            <span className={`rounded-md border px-2 py-1 text-xs font-bold ${severityClass(position.severity)}`}>
                              {severityLabel(position.severity)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>

                    {confirmation.exceptions.length > 0 ? (
                      <div className="mt-3 grid gap-2">
                        {confirmation.exceptions.map((exception) => (
                          <div key={exception.id} className={`rounded-lg border p-3 text-sm ${severityClass(exception.severity)}`}>
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="font-bold">
                                  {differenceTypeLabel(exception.difference_type)} · {exception.message}
                                </p>
                                <p className="mt-1 text-xs">
                                  Soll: {exception.ordered_value || "-"} · AB: {exception.confirmed_value || "-"} · Status: {exception.status}
                                </p>
                                {exception.resolution_note ? (
                                  <p className="mt-1 text-xs">Notiz: {exception.resolution_note}</p>
                                ) : null}
                              </div>
                              {exception.status === "open" ? (
                                <div className="flex flex-wrap gap-2">
                                  <form
                                    action={`/api/kunden/confirmations/${confirmation.id}/exceptions/${exception.id}/decide?return_to=${returnTo}`}
                                    method="post"
                                  >
                                    <input type="hidden" name="action" value="accept" />
                                    <Button type="submit" variant="secondary">Akzeptieren</Button>
                                  </form>
                                  <form
                                    action={`/api/kunden/confirmations/${confirmation.id}/exceptions/${exception.id}/decide?return_to=${returnTo}`}
                                    method="post"
                                  >
                                    <input type="hidden" name="action" value="request_corrected_ab" />
                                    <Button type="submit" variant="secondary">Änderungs-AB</Button>
                                  </form>
                                </div>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    {confirmation.communications.length > 0 ? (
                      <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3 text-sm">
                        <p className="font-bold">Lieferantenkommunikation</p>
                        <div className="mt-2 grid gap-2">
                          {confirmation.communications.map((communication) => (
                            <details key={communication.id} className="rounded-lg bg-white p-3">
                              <summary className="cursor-pointer font-bold">
                                {communication.subject} · {communication.status}
                              </summary>
                              <pre className="mt-2 whitespace-pre-wrap text-xs text-[var(--muted)]">{communication.body}</pre>
                            </details>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                );
              })}
              {supplierConfirmations.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[var(--border)] bg-white p-4 text-sm text-[var(--muted)]">
                  Noch keine Lieferanten-AB erfasst. Übernehmen Sie zuerst CARAT-Positionen und erfassen Sie dann die AB-Positionen.
                </div>
              ) : null}
            </div>
          </Panel>
          </>
          ) : null}

          {["angebot_auftrag", "rechnung_abschluss"].includes(activeRegister) ? (
          <Panel>
            <div className="flex items-center gap-2">
              <Upload size={18} aria-hidden="true" />
              <h3 className="section-title">
                {activeRegister === "angebot_auftrag" ? "Angebot / Auftrag" : "Rechnung / Abschluss"}
              </h3>
            </div>
            <form
              className="mt-4 grid gap-3 lg:grid-cols-[180px_1fr]"
              action={`/api/kunden/cases/${selectedCase.id}/sections/documents?return_to=${returnTo}`}
              method="post"
            >
              <Label label="Dokumenttyp">
                <Select name="document_type" defaultValue={sectionValue(documents, "document_type")}>
                  <option value="offer">Angebot</option>
                  <option value="measurement">Aufmaß</option>
                  <option value="order_confirmation">AB</option>
                  <option value="plan">Plan</option>
                  <option value="photo">Foto</option>
                  <option value="invoice">Rechnung</option>
                  <option value="other">Sonstiges</option>
                </Select>
              </Label>
              <Label label="Dokumentenvermerk">
                <Field
                  name="document_note"
                  defaultValue={sectionValue(documents, "document_note")}
                />
              </Label>
              <div className="lg:col-span-2">
                <Button type="submit">Dokumentenregister speichern</Button>
              </div>
            </form>
          </Panel>
          ) : null}

          {activeRegister === "kommunikation" ? (
          <Panel>
            <h3 className="section-title">Kommunikation</h3>
            <form
              id="telefonnotiz"
              className="mt-4 grid gap-3"
              action={`/api/kunden/cases/${selectedCase.id}/notes?return_to=${returnTo}`}
              method="post"
            >
              <input type="hidden" name="note_type" value="call" />
              <Label label="Telefonnotiz">
                <Textarea name="body" placeholder="Gesprächsnotiz" required />
              </Label>
              <Button type="submit">
                <Phone size={16} aria-hidden="true" />
                Telefonnotiz speichern
              </Button>
            </form>
            <form
              id="emailentwurf"
              className="mt-4 grid gap-3"
              action={`/api/kunden/cases/${selectedCase.id}/notes?return_to=${returnTo}`}
              method="post"
            >
              <input type="hidden" name="note_type" value="customer_request" />
              <Label label="E-Mail-Entwurf">
                <Textarea name="body" placeholder="Entwurf oder Gesprächsanlass" required />
              </Label>
              <Button type="submit" variant="secondary">
                <Mail size={16} aria-hidden="true" />
                Entwurf vormerken
              </Button>
            </form>
          </Panel>
          ) : null}

          {activeRegister === DOCUMENTS_REGISTER.key ? (
          <>
            <Panel>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <FileText size={18} aria-hidden="true" />
                    <h3 className="section-title">Vorgangsdokumente</h3>
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    Alle hochgeladenen Dokumente zu diesem Vorgang. Die Dokumentart ist pro Eintrag direkt sichtbar.
                  </p>
                </div>
                <Button type="button" data-document-upload-open>
                  <Upload size={16} aria-hidden="true" />
                  Dokument hinzufügen
                </Button>
              </div>
              <div className="mt-4 grid gap-2">
                {caseDocuments.map((document) => {
                  const documentCategoryLabel = optionLabel(
                    DOCUMENT_CATEGORY_LABEL_OPTIONS,
                    document.document_category,
                  );
                  return (
                  <div
                    key={document.id}
                    className="rounded-lg border border-[var(--border)] bg-white p-3 text-sm"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-md border border-[var(--accent)] bg-[var(--surface-soft)] px-2 py-1 text-xs font-bold text-[var(--foreground)]">
                            {documentCategoryLabel}
                          </span>
                          <span className="badge">
                            {optionLabel(DOCUMENT_STATUSES, document.document_status)}
                          </span>
                        </div>
                        <p className="mt-2 font-bold">{document.title}</p>
                        <p className="mt-1 text-xs text-[var(--muted)]">
                          {optionLabel(CASE_REGISTERS.map((register) => [register.key, register.label] as const), document.register_code)}
                          {" · Version "}
                          {document.version_label}
                        </p>
                        {document.note ? (
                          <p className="mt-2 text-xs text-[var(--muted)]">{document.note}</p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {document.has_file ? (
                          <LinkButton
                            href={`/api/kunden/cases/${selectedCase.id}/documents/${document.id}/download`}
                            variant="secondary"
                          >
                            <Download size={16} aria-hidden="true" />
                            Herunterladen
                          </LinkButton>
                        ) : null}
                        <form
                          action={`/api/kunden/cases/${selectedCase.id}/documents/${document.id}/archive?return_to=${returnTo}`}
                          method="post"
                        >
                          <Button type="submit" variant="secondary">
                            Archivieren
                          </Button>
                        </form>
                      </div>
                    </div>
                    <p className="mt-2 text-xs text-[var(--muted)]">
                      {document.has_file ? "Datei vorhanden" : "Noch ohne Datei"}
                      {document.created_by ? ` · angelegt von ${document.created_by}` : ""}
                      {document.created_at ? ` · ${document.created_at}` : ""}
                    </p>
                  </div>
                  );
                })}
                {caseDocuments.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-[var(--border)] bg-white p-4 text-sm text-[var(--muted)]">
                    Noch keine Dokumente in diesem Vorgang.
                  </div>
                ) : null}
              </div>
            </Panel>
            <div
              className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
              data-document-upload-modal
              hidden
              role="dialog"
              aria-modal="true"
              aria-labelledby="document-upload-title"
            >
              <button
                type="button"
                className="absolute inset-0 cursor-default"
                data-document-upload-backdrop
                aria-label="Dokument hinzufügen schließen"
              />
              <div className="relative max-h-[90vh] w-full max-w-6xl overflow-auto rounded-lg border border-[var(--border)] bg-white shadow-xl">
                <div className="sticky top-0 z-10 flex items-start justify-between gap-3 border-b border-[var(--border)] bg-white px-4 py-3">
                  <div>
                    <h3 id="document-upload-title" className="section-title">Dokument hinzufügen</h3>
                    <p className="mt-1 text-sm text-[var(--muted)]">
                      Die Dokumentart ordnet den Upload automatisch dem passenden Register zu.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    className="aspect-square p-2"
                    data-document-upload-close
                    aria-label="Dokument hinzufügen schließen"
                  >
                    <X size={16} aria-hidden="true" />
                  </Button>
                </div>
                <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_360px]">
                  <form
                    className="grid h-fit gap-4 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-4"
                    action={`/api/kunden/cases/${selectedCase.id}/documents?return_to=${returnTo}`}
                    encType="multipart/form-data"
                    method="post"
                  >
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_minmax(170px,0.65fr)]">
                      <Label label="Datei">
                        <Field
                          className="bg-white"
                          name="file"
                          type="file"
                          accept=".pdf,.jpg,.jpeg,.png,.webp,.docx,.xlsx,application/pdf,image/jpeg,image/png,image/webp,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        />
                      </Label>
                      <Label label="Version">
                        <Field className="bg-white" name="version_label" defaultValue="1" />
                      </Label>
                    </div>
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
                      <Label label="Dokumentart">
                        <Select name="document_category" defaultValue="from_customer">
                          {DOCUMENT_GUIDE_CATEGORIES.map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </Select>
                        <span className="mt-1 text-xs font-normal leading-relaxed text-[var(--muted)]">
                          Legt automatisch fest, in welchem Register das Dokument geführt wird.
                        </span>
                      </Label>
                      <Label label="Status">
                        <Select name="document_status" defaultValue="received">
                          {DOCUMENT_STATUSES.map(([value, label]) => (
                            <option key={value} value={value}>{label}</option>
                          ))}
                        </Select>
                      </Label>
                    </div>
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.75fr)]">
                      <Label label="Titel">
                        <Field
                          name="title"
                          required
                          placeholder="z. B. Grundriss Kunde, Angebot V1, Rechnung"
                        />
                      </Label>
                      <Label label="Notiz">
                        <Textarea
                          className="min-h-10"
                          name="note"
                          placeholder="Kurzer interner Hinweis"
                        />
                      </Label>
                    </div>
                    <input type="hidden" name="document_type" value="other" />
                    <div className="flex justify-end border-t border-[var(--border)] pt-3">
                      <Button type="submit">
                        <Upload size={16} aria-hidden="true" />
                        Dokument hochladen
                      </Button>
                    </div>
                  </form>
                  <aside className="grid h-fit gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-bold">Dokumentenarten</p>
                      <span className="badge">Guide</span>
                    </div>
                    <div className="grid gap-2">
                      {DOCUMENT_GUIDE_CATEGORIES.map(([value, label, description]) => (
                        <div
                          key={value}
                          className="rounded-lg border border-[var(--border)] bg-white p-3 text-sm"
                        >
                          <p className="font-bold">{label}</p>
                          <p className="mt-2 text-xs leading-relaxed text-[var(--muted)]">{description}</p>
                        </div>
                      ))}
                    </div>
                  </aside>
                </div>
              </div>
            </div>
          </>
          ) : null}
        </div>

        {["abwicklung", "kommunikation", "rechnung_abschluss"].includes(activeRegister) ? (
        <aside className="grid h-fit gap-4">
          {activeRegister === "abwicklung" ? (
          <Panel>
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} aria-hidden="true" />
              <h3 className="section-title">Cockpit</h3>
            </div>
            <div className="mt-4 grid gap-2 text-sm">
              <div className="rounded-lg bg-[var(--surface-soft)] p-3">
                <p className="font-bold">{activeTaskCount} offene Aufgaben</p>
                <p className="text-[var(--muted)]">Aus dem Aufgabenbereich zum geöffneten Vorgang.</p>
              </div>
              <form
                className="grid gap-2 rounded-lg bg-white p-3"
                action={`/api/kunden/cases/${selectedCase.id}/sections/process_control?return_to=${returnTo}`}
                method="post"
              >
                <Label label="Nächster kritischer Schritt">
                  <Field
                    name="next_control_step"
                    defaultValue={sectionValue(processControl, "next_control_step")}
                    placeholder="z. B. AB prüfen"
                  />
                </Label>
                <Label label="Fällig am">
                  <Field
                    name="next_control_due"
                    type="date"
                    defaultValue={sectionValue(processControl, "next_control_due")}
                  />
                </Label>
                <Button type="submit" variant="secondary">Speichern</Button>
              </form>
            </div>
          </Panel>
          ) : null}

          {["kommunikation", "rechnung_abschluss"].includes(activeRegister) ? (
          <Panel>
            <h3 className="section-title">Historie</h3>
            <div className="mt-4 grid gap-2">
              {selectedCase.notes.slice(0, 5).map((note) => (
                <p key={note.id} className="rounded-lg bg-[var(--surface-soft)] p-3 text-sm">
                  {note.body} · {note.created_by || "System"} · {formatDateTime(note.created_at)}
                </p>
              ))}
              {selectedCaseEvents.slice(0, 4).map((event) => (
                <p key={`event-${event.id}`} className="rounded-lg bg-white p-3 text-sm">
                  {event.title} · {event.actor || "System"} · {formatDateTime(event.occurred_at)}
                </p>
              ))}
              {selectedCase.notes.length === 0 && selectedCaseEvents.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Noch keine Vorgangshistorie.</p>
              ) : null}
            </div>
          </Panel>
          ) : null}
        </aside>
        ) : null}
      </div>
    </div>
  );
}
