import Script from "next/script";
import { PageHero } from "@/components/chrome/page-hero";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchCustomersState } from "@/lib/dkh-api";
import type { CustomerRecord } from "@/lib/types";
import { displayName } from "@/lib/utils";

function customerUpdatedTime(customer: CustomerRecord): number {
  if (!customer.updated_at) return 0;
  const time = new Date(customer.updated_at).getTime();
  return Number.isFinite(time) ? time : 0;
}

export default async function CustomersPage() {
  const userEmail = await getUserEmail();
  const state = await fetchCustomersState(userEmail);
  const recentlyUsedCustomers = [...state.customers]
    .sort((left, right) => customerUpdatedTime(right) - customerUpdatedTime(left))
    .slice(0, 5);

  return (
    <div className="content-stack">
      <PageHero
        eyebrow={null}
        title="Kunden"
        subtitle="Suche, Neuanlage und direkter Einstieg in Kundenakten."
      />
      <Panel>
        <div data-customer-search-first className="grid gap-3">
          <h2 className="section-title">Kunde suchen</h2>
          <input
            data-customer-search-input
            className="field"
            name="q"
            type="search"
            autoComplete="off"
            placeholder="Name, E-Mail, Kundennummer oder Telefon"
          />
          <p data-customer-search-hint className="text-sm text-[var(--muted)]">
            Geben Sie mindestens drei Zeichen ein.
          </p>
          <div data-customer-search-results hidden />
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <div aria-hidden="true" />

        <Panel>
          <h2 className="section-title">Zuletzt verwendet</h2>
          <div className="mt-4 grid gap-3">
            {recentlyUsedCustomers.map((customer) => (
              <article key={customer.id} className="rounded-lg border border-[var(--border)] bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-bold">{customer.display_name}</p>
                    <p className="text-sm text-[var(--muted)]">
                      {customer.customer_number || "Ohne Kundennummer"} ·{" "}
                      {customer.primary_email || customer.primary_phone || "Keine Kontaktdaten"}
                    </p>
                  </div>
                  <LinkButton
                    href={`/kunden/${customer.id}`}
                    data-customer-file-link=""
                    data-customer-id={customer.id}
                  >
                    Akte öffnen
                  </LinkButton>
                </div>
              </article>
            ))}
            {recentlyUsedCustomers.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">Noch keine zuletzt bearbeiteten Kunden.</p>
            ) : null}
          </div>
        </Panel>
      </div>
      <div
        data-customer-create-modal
        hidden
        className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="customer-create-title"
      >
        <Panel className="max-h-[92vh] w-full max-w-3xl overflow-y-auto">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="customer-create-title" className="section-title">Kunde anlegen</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Kein Treffer in der Suche. Erfassen Sie den Kunden jetzt neu.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              data-customer-create-close
              aria-label="Neuanlage schließen"
            >
              Schließen
            </button>
          </div>
          <form className="mt-4 grid gap-3" action="/api/kunden/customers?return_to=/kunden" method="post">
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Kundentyp">
                <Select name="customer_type" defaultValue="private">
                  <option value="private">Privatkunde</option>
                  <option value="company">Objektkunde</option>
                </Select>
              </Label>
              <Label label="Kundennummer">
                <Field value="Wird beim Speichern automatisch vergeben" disabled />
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Vorname">
                <Field name="first_name" />
              </Label>
              <Label label="Nachname">
                <Field name="last_name" />
              </Label>
            </div>
            <Label label="Firma">
              <Field name="company_name" />
            </Label>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="E-Mail">
                <Field name="primary_email" type="email" />
              </Label>
              <Label label="Telefon">
                <Field name="primary_phone" />
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <Label label="Straße">
                <Field name="street" />
              </Label>
              <Label label="Hausnummer">
                <Field name="house_number" />
              </Label>
              <Label label="PLZ">
                <Field name="postal_code" />
              </Label>
            </div>
            <Label label="Ort">
              <Field name="city" />
            </Label>
            <Label label="Zuständig">
              <Select name="owner_user_id">
                {state.users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {displayName(user.first_name, user.last_name) || user.email}
                  </option>
                ))}
              </Select>
            </Label>
            <Label label="Notizen">
              <Textarea name="notes" />
            </Label>
            <label className="flex items-center gap-2 text-sm font-bold">
              <input name="create_case" value="true" type="checkbox" defaultChecked />
              Direkt einen Vorgang anlegen
            </label>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Vorgangsnummer">
                <Field value="Wird beim Speichern automatisch vergeben" disabled />
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
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Vorgangstitel">
                <Field name="case_title" placeholder="z. B. Küchenplanung" />
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
            </div>
            <Label label="Vorgang verantwortlich">
              <Select name="responsible_user_id">
                {state.users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {displayName(user.first_name, user.last_name) || user.email}
                  </option>
                ))}
              </Select>
            </Label>
            <Button type="submit">Kunde speichern</Button>
          </form>
        </Panel>
      </div>
      <Script src="/customer-search.v1.js" strategy="afterInteractive" />
    </div>
  );
}
