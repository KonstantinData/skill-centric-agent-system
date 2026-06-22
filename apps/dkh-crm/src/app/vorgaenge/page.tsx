import { PageHero } from "@/components/chrome/page-hero";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchCustomersState } from "@/lib/dkh-api";
import { formatDateTime } from "@/lib/utils";

const CASE_SECTION_CODES = [
  "case_control",
  "consultation_needs",
  "measurement_room",
  "planning_carat",
  "offer_order",
  "suppliers_procurement",
  "appointments_tasks",
  "installation_acceptance",
  "documents",
  "invoice_closing",
];

export default async function CasesPage() {
  const userEmail = await getUserEmail();
  const state = await fetchCustomersState(userEmail);

  return (
    <div className="content-stack">
      <PageHero
        title="Vorgänge"
        subtitle="Küchenprojekte mit Statusphase, Kundenbezug, Notizen und Aktenbereichen."
      />
      <Panel>
        <h2 className="section-title">Vorgangsübersicht</h2>
        <div className="mt-4 grid gap-4">
          {state.customer_cases.map((item) => (
            <article key={item.id} className="rounded-lg border border-[var(--border)] bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-bold">{item.case_number || `Vorgang #${item.id}`}</p>
                  <p className="text-sm text-[var(--muted)]">
                    {item.customer_display_name} · {item.case_title || "Küchenprojekt"} ·{" "}
                    {item.status_phase_name || item.case_status}
                  </p>
                </div>
                {item.customer_id ? (
                  <LinkButton href={`/kunden/${item.customer_id}`}>Kundenakte</LinkButton>
                ) : null}
              </div>
              <div className="mt-4 grid gap-3 xl:grid-cols-[0.8fr_1.2fr]">
                <form
                  className="grid gap-3"
                  action={`/api/kunden/cases/${item.id}/notes?return_to=/vorgaenge`}
                  method="post"
                >
                  <Label label="Notiztyp">
                    <Select name="note_type" defaultValue="general">
                      <option value="general">Allgemein</option>
                      <option value="call">Telefonat</option>
                      <option value="meeting">Termin</option>
                      <option value="internal">Intern</option>
                      <option value="supplier">Lieferant</option>
                      <option value="installation">Montage</option>
                    </Select>
                  </Label>
                  <Label label="Notiz">
                    <Textarea name="body" required />
                  </Label>
                  <Button type="submit">Notiz speichern</Button>
                </form>
                <div className="grid gap-2">
                  {item.notes.slice(0, 4).map((note) => (
                    <p key={note.id} className="rounded-lg bg-[var(--surface-soft)] p-3 text-sm">
                      {note.body} · {note.created_by || "System"} · {formatDateTime(note.created_at)}
                    </p>
                  ))}
                </div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {CASE_SECTION_CODES.map((code) => (
                  <form
                    key={code}
                    className="grid gap-2 rounded-lg bg-[var(--surface-soft)] p-3"
                    action={`/api/kunden/cases/${item.id}/sections/${code}?return_to=/vorgaenge`}
                    method="post"
                  >
                    <Label label={code.replaceAll("_", " ")}>
                      <Field
                        name="note"
                        defaultValue={String(item.sections?.[code]?.note ?? "")}
                      />
                    </Label>
                    <Button type="submit" variant="secondary">
                      Speichern
                    </Button>
                  </form>
                ))}
              </div>
            </article>
          ))}
          {state.customer_cases.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">Keine Vorgänge sichtbar.</p>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
