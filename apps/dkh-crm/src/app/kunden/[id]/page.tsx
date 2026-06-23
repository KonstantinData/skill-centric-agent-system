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
} from "lucide-react";
import Script from "next/script";
import { PageHero } from "@/components/chrome/page-hero";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchCustomersState, fetchOverviewState } from "@/lib/dkh-api";
import type { CustomerCaseRecord, SectionPayload } from "@/lib/types";
import { displayName, formatDateTime } from "@/lib/utils";

type PageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ case?: string; register?: string }>;
};

const PROJECT_OBJECTS = [
  ["project_object_kitchen", "Einbauküche"],
  ["project_object_utility", "Hauswirtschaftsraum"],
  ["project_object_wardrobe", "Garderobe"],
  ["project_object_bedroom", "Schlafzimmer / Schrank"],
  ["project_object_sideboard", "Sideboard"],
  ["project_object_bath", "Badmöbel"],
  ["project_object_service", "Dienstleistung"],
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
  ["10000_20000", "10.000-20.000 EUR"],
  ["20000_35000", "20.000-35.000 EUR"],
  ["over_35000", "über 35.000 EUR"],
  ["open", "Offen"],
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
                <dd>{customer.display_name}</dd>
                {customer.company_name ? <dd>{customer.company_name}</dd> : null}
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
              <a className="btn btn-secondary" href={`mailto:${customer.primary_email || ""}`}>
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
                  <Select name="country" defaultValue={customer.address?.country || customer.country || "DE"}>
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
                  <Select name="country" defaultValue={customer.address?.country || customer.country || "DE"}>
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
              <Select name="tax_treatment" defaultValue={customer.tax_treatment ?? "standard_de"}>
                <option value="standard_de">Deutschland Standard</option>
                <option value="eu_business">EU-Unternehmen mit USt-IdNr.</option>
                <option value="third_country_export">Drittland / Ausfuhr prüfen</option>
                <option value="switzerland_export">Schweiz / Ausfuhr prüfen</option>
                <option value="nato_forces">NATO / US-Streitkräfte prüfen</option>
                <option value="custom">Abweichend / manuell prüfen</option>
              </Select>
            </Label>
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
  const processControl = selectedCase.sections?.process_control;
  const activeTaskCount = selectedCaseTasks.filter((task) => task.status !== "done").length;
  const currentPhase = selectedCase.status_phase ?? 1;
  const phaseRegister = registerForPhase(currentPhase);
  const registerMeta =
    activeRegister === DOCUMENTS_REGISTER.key
      ? DOCUMENTS_REGISTER
      : CASE_REGISTERS.find((register) => register.key === activeRegister) ?? CASE_REGISTERS[0];

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

      <div className="grid gap-4 2xl:grid-cols-[1fr_360px]">
        <div className="grid gap-4">
          {activeRegister === "anfrage" ? (
          <Panel>
            <div className="flex items-center gap-2">
              <ClipboardList size={18} aria-hidden="true" />
              <h3 className="section-title">Projektgrundlagen</h3>
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
              <div className="grid gap-3 lg:grid-cols-3">
                <Label label="Objekt / Immobilie">
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
                <Label label="Liefer-/Montageort Ort">
                  <Field
                    name="delivery_city"
                    defaultValue={sectionValue(projectObjects, "delivery_city")}
                    placeholder="z. B. Stuttgart"
                  />
                </Label>
                <Label label="Gewünschter Zeitraum">
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
                <Label label="Grund für Terminwunsch">
                  <Field
                    name="timeline_reason"
                    defaultValue={sectionValue(projectObjects, "timeline_reason")}
                    placeholder="z. B. Umzug, Übergabe, Wasserschaden"
                  />
                </Label>
                <Label label="Budgetrahmen">
                  <Select
                    name="budget_range"
                    defaultValue={sectionValue(projectObjects, "budget_range")}
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
              </div>
              <div>
                <p className="text-sm font-bold">Vorhandene Unterlagen</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
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
              </div>
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
              <Button type="submit">Projektgrundlagen speichern</Button>
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
          <Panel>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <FileText size={18} aria-hidden="true" />
                  <h3 className="section-title">Dokumente</h3>
                </div>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  Wählen Sie zuerst die fachliche Dokumentart. Die Hinweise zeigen, welche Unterlagen in welchen Bereich gehören.
                </p>
              </div>
              <span className="badge">Guide</span>
            </div>
            <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
              {DOCUMENT_GUIDE_CATEGORIES.map(([value, label, description]) => (
                <div
                  key={value}
                  className="rounded-lg border border-[var(--border)] bg-white p-3 text-sm"
                >
                  <p className="font-bold">{label}</p>
                  <p className="mt-2 text-xs text-[var(--muted)]">{description}</p>
                </div>
              ))}
            </div>
            <details className="mt-4 rounded-lg border border-[var(--border)] bg-white p-3">
              <summary className="cursor-pointer text-sm font-bold">
                Dokument hinzufügen
              </summary>
              <form
                className="mt-4 grid gap-3 lg:grid-cols-3"
                action={`/api/kunden/cases/${selectedCase.id}/documents?return_to=${returnTo}`}
                method="post"
              >
                <Label label="Dokumentart">
                  <Select name="document_category" defaultValue="from_customer">
                    {DOCUMENT_GUIDE_CATEGORIES.map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </Select>
                  <span className="mt-1 text-xs font-normal text-[var(--muted)]">
                    Die Kacheln oberhalb erklären, welche Dokumente unter welche Dokumentart fallen.
                  </span>
                </Label>
                <Label label="Register">
                  <Select name="register_code" defaultValue={phaseRegister}>
                    {CASE_REGISTERS.filter((register) => register.key !== "kommunikation").map((register) => (
                      <option key={register.key} value={register.key}>{register.label}</option>
                    ))}
                    <option value="kommunikation">Kommunikation</option>
                  </Select>
                </Label>
                <Label label="Status">
                  <Select name="document_status" defaultValue="received">
                    {DOCUMENT_STATUSES.map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </Select>
                </Label>
                <Label label="Titel" className="lg:col-span-2">
                  <Field
                    name="title"
                    required
                    placeholder="z. B. Grundriss Kunde, Angebot V1, Rechnung"
                  />
                </Label>
                <Label label="Version">
                  <Field name="version_label" defaultValue="1" />
                </Label>
                <Label label="Notiz" className="lg:col-span-3">
                  <Textarea
                    name="note"
                    placeholder="Kurzer Hinweis, was abgelegt werden soll."
                  />
                </Label>
                <input type="hidden" name="document_type" value="other" />
                <div className="lg:col-span-3">
                  <Button type="submit">
                    <FileText size={16} aria-hidden="true" />
                    Dokument-Metadaten speichern
                  </Button>
                </div>
              </form>
            </details>
            <div className="mt-4 grid gap-2">
              {caseDocuments.map((document) => (
                <div
                  key={document.id}
                  className="rounded-lg border border-[var(--border)] bg-white p-3 text-sm"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-bold">{document.title}</p>
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        {optionLabel(DOCUMENT_CATEGORY_LABEL_OPTIONS, document.document_category)}
                        {" · "}
                        {optionLabel(CASE_REGISTERS.map((register) => [register.key, register.label] as const), document.register_code)}
                        {" · Version "}
                        {document.version_label}
                      </p>
                      {document.note ? (
                        <p className="mt-2 text-xs text-[var(--muted)]">{document.note}</p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="badge">
                        {optionLabel(DOCUMENT_STATUSES, document.document_status)}
                      </span>
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
              ))}
              {caseDocuments.length === 0 ? (
                <div className="rounded-lg border border-dashed border-[var(--border)] bg-white p-4 text-sm text-[var(--muted)]">
                  Noch keine Dokumente in diesem Vorgang.
                </div>
              ) : null}
            </div>
            <p className="mt-4 text-xs text-[var(--muted)]">
              Aktuell werden Dokument-Metadaten gespeichert. Datei-Upload, Versionierung und Download-Pakete werden im nächsten Schritt angebunden.
            </p>
          </Panel>
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
