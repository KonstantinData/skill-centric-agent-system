import { notFound } from "next/navigation";
import Script from "next/script";
import { PageHero } from "@/components/chrome/page-hero";
import { Button } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchCustomersState } from "@/lib/dkh-api";
import { displayName, formatDateTime } from "@/lib/utils";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CustomerFilePage({ params }: PageProps) {
  const { id } = await params;
  const userEmail = await getUserEmail();
  const state = await fetchCustomersState(userEmail);
  const customer = state.customers.find((item) => String(item.id) === id);
  if (!customer) notFound();

  const cases = state.customer_cases.filter(
    (item) => item.customer_id === customer.id,
  );

  return (
    <div className="content-stack">
      <PageHero
        title={customer.display_name}
        subtitle={`${customer.customer_number || "Ohne Kundennummer"} · ${customer.primary_email || "keine E-Mail"}`}
      />
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel>
          <h2 className="section-title">Stammdaten</h2>
          <form
            className="mt-4 grid gap-3"
            action={`/api/kunden/customers/${customer.id}?return_to=/kunden/${customer.id}`}
            method="post"
          >
            <input type="hidden" name="customer_type" value={customer.customer_type} />
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Vorname">
                <Field name="first_name" defaultValue={customer.first_name ?? ""} />
              </Label>
              <Label label="Nachname">
                <Field name="last_name" defaultValue={customer.last_name ?? ""} />
              </Label>
            </div>
            <Label label="Firma">
              <Field name="company_name" defaultValue={customer.company_name ?? ""} />
            </Label>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="E-Mail">
                <Field name="primary_email" defaultValue={customer.primary_email ?? ""} />
              </Label>
              <Label label="Telefon">
                <Field name="primary_phone" defaultValue={customer.primary_phone ?? ""} />
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <Label label="Straße">
                <Field name="street" defaultValue={customer.address?.street ?? ""} />
              </Label>
              <Label label="Hausnummer">
                <Field name="house_number" defaultValue={customer.address?.house_number ?? ""} />
              </Label>
              <Label label="PLZ">
                <Field name="postal_code" defaultValue={customer.address?.postal_code ?? ""} />
              </Label>
            </div>
            <Label label="Ort">
              <Field name="city" defaultValue={customer.address?.city ?? ""} />
            </Label>
            <Label label="Zuständig">
              <Select name="owner_user_id" defaultValue={customer.owner_user_id ?? ""}>
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

        <div className="grid gap-4">
          <Panel>
            <h2 className="section-title">Kundenaktenbereiche</h2>
            <form
              className="mt-4 grid gap-3"
              action={`/api/kunden/customers/${customer.id}/sections/master_data?return_to=/kunden/${customer.id}`}
              method="post"
            >
              <Label label="Zusammenfassung">
                <Textarea
                  name="summary"
                  defaultValue={String(customer.file_sections?.master_data?.summary ?? "")}
                />
              </Label>
              <Button type="submit">Bereich speichern</Button>
            </form>
            <form
              className="mt-4 grid gap-3"
              action={`/api/kunden/customers/${customer.id}/sections/addresses_contacts_privacy?return_to=/kunden/${customer.id}`}
              method="post"
            >
              <Label label="Datenschutz- und Kontaktvermerke">
                <Textarea
                  name="privacy_notes"
                  defaultValue={String(customer.file_sections?.addresses_contacts_privacy?.privacy_notes ?? "")}
                />
              </Label>
              <Button type="submit" variant="secondary">Kontaktbereich speichern</Button>
            </form>
          </Panel>

          <Panel>
            <h2 className="section-title">Vorgänge</h2>
            <div className="mt-4 grid gap-3">
              {cases.map((item) => (
                <article key={item.id} className="rounded-lg border border-[var(--border)] bg-white p-4">
                  <p className="font-bold">{item.case_number || `Vorgang #${item.id}`}</p>
                  <p className="text-sm text-[var(--muted)]">
                    {item.case_title || "Küchenprojekt"} · {item.status_phase_name || item.case_status}
                  </p>
                  {item.carat_order_number ? (
                    <p className="text-sm text-[var(--muted)]">
                      CARAT Vorgangsnummer: {item.carat_order_number}
                    </p>
                  ) : null}
                  <form
                    className="mt-3 grid gap-2"
                    action={`/api/kunden/cases/${item.id}/notes?return_to=/kunden/${customer.id}`}
                    method="post"
                  >
                    <input type="hidden" name="note_type" value="general" />
                    <Textarea name="body" placeholder="Neue Vorgangsnotiz" required />
                    <Button type="submit">Notiz speichern</Button>
                  </form>
                  <div className="mt-3 grid gap-2">
                    {item.notes.slice(0, 3).map((note) => (
                      <p key={note.id} className="rounded-lg bg-[var(--surface-soft)] p-3 text-sm">
                        {note.body} · {note.created_by || "System"} · {formatDateTime(note.created_at)}
                      </p>
                    ))}
                  </div>
                </article>
              ))}
              {cases.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">Keine Vorgänge zu diesem Kunden.</p>
              ) : null}
            </div>
          </Panel>
        </div>
      </div>
      <Script src="/customer-search.v1.js" strategy="afterInteractive" />
    </div>
  );
}
