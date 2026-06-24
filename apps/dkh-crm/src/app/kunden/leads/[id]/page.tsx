import { notFound } from "next/navigation";
import { PageHero } from "@/components/chrome/page-hero";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Label, Select } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchCustomersState } from "@/lib/dkh-api";

type LeadPageProps = {
  params: Promise<{ id: string }>;
};

const leadStatusLabels: Record<string, string> = {
  new: "Neu",
  contacted: "Kontakt aufgenommen",
  waiting_for_customer: "Wartet auf Rückmeldung",
  appointment_scheduled: "Termin vereinbart",
  converted: "In Kunde umgewandelt",
  not_reached: "Nicht erreicht",
  not_interested: "Kein Interesse",
  not_qualified: "Nicht passend",
  closed: "Geschlossen",
};

const sourceLabels: Record<string, string> = {
  website: "Website",
  facebook: "Facebook",
  instagram: "Instagram",
  email: "E-Mail",
  phone: "Telefon",
  whatsapp: "WhatsApp",
  showroom: "Ausstellung",
  referral: "Empfehlung",
  partner: "Partner",
  other: "Sonstiges",
  unknown: "Unklar",
};

export default async function LeadPage({ params }: LeadPageProps) {
  const { id } = await params;
  const userEmail = await getUserEmail();
  const state = await fetchCustomersState(userEmail);
  const lead = state.leads.find((item) => String(item.id) === id);

  if (!lead) notFound();

  return (
    <div className="content-stack">
      <PageHero
        eyebrow={lead.lead_number || "Lead"}
        title={lead.display_name}
        subtitle="Leadakte für Erstinformationen, Kommunikation und nächste Schritte vor der Kundenumwandlung."
      />

      <div className="flex flex-wrap gap-3">
        <LinkButton href="/kunden" variant="secondary">
          Zur Kundensuche
        </LinkButton>
        <Button type="button" disabled>
          In Kunde umwandeln
        </Button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Panel className="h-fit">
          <h2 className="section-title">Leadstammdaten</h2>
          <dl className="mt-4 grid gap-3 text-sm">
            <div>
              <dt className="font-bold text-[var(--ink)]">Status</dt>
              <dd className="text-[var(--muted)]">
                {leadStatusLabels[lead.status] || lead.status}
              </dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--ink)]">Source</dt>
              <dd className="text-[var(--muted)]">
                {sourceLabels[lead.source] || lead.source} ·{" "}
                {sourceLabels[lead.source_channel] || lead.source_channel}
              </dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--ink)]">Kontakt</dt>
              <dd className="text-[var(--muted)]">
                {[lead.primary_email, lead.primary_phone, lead.primary_mobile]
                  .filter(Boolean)
                  .join(" · ") || "Noch keine Kontaktdaten"}
              </dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--ink)]">Ort</dt>
              <dd className="text-[var(--muted)]">
                {[lead.postal_code, lead.city].filter(Boolean).join(" ") || "Noch kein Ort"}
              </dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--ink)]">Kurzbeschreibung</dt>
              <dd className="text-[var(--muted)]">
                {lead.project_summary || "Noch keine Kurzbeschreibung"}
              </dd>
            </div>
            <div>
              <dt className="font-bold text-[var(--ink)]">Letzte Änderung</dt>
              <dd className="text-[var(--muted)]">{lead.updated_at || "-"}</dd>
            </div>
          </dl>
        </Panel>

        <div className="grid gap-4">
          <Panel>
            <h2 className="section-title">Erste Informationen</h2>
            <div className="mt-4 grid gap-3">
              <article className="rounded-lg border border-[var(--border)] bg-white p-4">
                <p className="text-sm font-bold">Erste Nachricht</p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--muted)]">
                  {lead.initial_message || "Noch keine erste Nachricht erfasst."}
                </p>
              </article>
              {lead.notes ? (
                <article className="rounded-lg border border-[var(--border)] bg-white p-4">
                  <p className="text-sm font-bold">Interne Notiz</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--muted)]">
                    {lead.notes}
                  </p>
                </article>
              ) : null}
            </div>
          </Panel>

          <Panel>
            <h2 className="section-title">Kommunikation dokumentieren</h2>
            <form
              className="mt-4 grid gap-3"
              action={`/api/kunden/leads/${lead.id}/notes?return_to=/kunden/leads/${lead.id}`}
              method="post"
            >
              <div className="grid gap-3 md:grid-cols-[220px_1fr]">
                <Label label="Art">
                  <Select name="note_type" defaultValue="call">
                    <option value="call">Telefon</option>
                    <option value="email">E-Mail</option>
                    <option value="whatsapp">WhatsApp</option>
                    <option value="social">Social Media</option>
                    <option value="customer_request">Kundenanfrage</option>
                    <option value="internal">Interne Notiz</option>
                    <option value="general">Allgemein</option>
                  </Select>
                </Label>
                <Label label="Kurznotiz">
                  <Field name="body" required placeholder="z. B. Rückruf geführt, Terminwunsch, Unterlagen angefordert" />
                </Label>
              </div>
              <Button type="submit">Kommunikation speichern</Button>
            </form>
          </Panel>

          <Panel>
            <h2 className="section-title">Kommunikationsverlauf</h2>
            <div className="mt-4 grid gap-3">
              {lead.notes_history.map((note) => (
                <article key={note.id} className="rounded-lg border border-[var(--border)] bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="badge">{note.note_type}</span>
                    <p className="text-xs text-[var(--muted)]">
                      {note.created_at} · {note.created_by || "Unbekannt"}
                    </p>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm text-[var(--muted)]">
                    {note.body}
                  </p>
                </article>
              ))}
              {lead.notes_history.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">
                  Noch keine Kommunikation dokumentiert.
                </p>
              ) : null}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
