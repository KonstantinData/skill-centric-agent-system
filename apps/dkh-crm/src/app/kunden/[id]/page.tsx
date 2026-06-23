import {
  AlertTriangle,
  CheckSquare,
  ClipboardList,
  FolderOpen,
  Mail,
  MessageSquareText,
  Phone,
  Search,
  Upload,
} from "lucide-react";
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
  searchParams: Promise<{ case?: string }>;
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

function caseLabel(item: CustomerCaseRecord): string {
  return item.case_number || `Vorgang #${item.id}`;
}

export default async function CustomerFilePage({ params, searchParams }: PageProps) {
  const { id } = await params;
  const { case: selectedCaseId } = await searchParams;
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
  const returnTo = selectedCase
    ? encodeURIComponent(`/kunden/${customer.id}?case=${selectedCase.id}`)
    : encodeURIComponent(`/kunden/${customer.id}`);
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

            <details className="mt-4">
              <summary className="cursor-pointer text-sm font-bold">Stammdaten bearbeiten</summary>
              <form
                className="mt-3 grid gap-3"
                action={`/api/kunden/customers/${customer.id}?return_to=/kunden/${customer.id}`}
                method="post"
              >
                <input type="hidden" name="customer_type" value={customer.customer_type} />
                <Label label="Name">
                  <Field name="first_name" defaultValue={customer.first_name ?? ""} />
                </Label>
                <Label label="Nachname / Firma">
                  <Field
                    name={customer.customer_type === "company" ? "company_name" : "last_name"}
                    defaultValue={
                      customer.customer_type === "company"
                        ? customer.company_name ?? ""
                        : customer.last_name ?? ""
                    }
                  />
                </Label>
                <Label label="E-Mail">
                  <Field name="primary_email" defaultValue={customer.primary_email ?? ""} />
                </Label>
                <Label label="Telefon">
                  <Field name="primary_phone" defaultValue={customer.primary_phone ?? ""} />
                </Label>
                <Label label="Notizen">
                  <Textarea name="notes" defaultValue={customer.notes ?? ""} />
                </Label>
                <Button type="submit">Speichern</Button>
              </form>
            </details>
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
  returnTo: string;
}) {
  const projectObjects = selectedCase.sections?.project_objects;
  const projectContacts = selectedCase.sections?.project_contacts;
  const documents = selectedCase.sections?.documents;
  const processControl = selectedCase.sections?.process_control;
  const activeTaskCount = selectedCaseTasks.filter((task) => task.status !== "done").length;

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

      <div className="grid gap-4 2xl:grid-cols-[1fr_360px]">
        <div className="grid gap-4">
          <Panel>
            <div className="flex items-center gap-2">
              <ClipboardList size={18} aria-hidden="true" />
              <h3 className="section-title">Projektobjekte</h3>
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
                <Label label="Liefer-/Montageadresse">
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
              <Button type="submit">Projekt speichern</Button>
            </form>
          </Panel>

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
            <div className="flex items-center gap-2">
              <Upload size={18} aria-hidden="true" />
              <h3 className="section-title">Dokumente</h3>
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
        </div>

        <aside className="grid h-fit gap-4">
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
        </aside>
      </div>
    </div>
  );
}
