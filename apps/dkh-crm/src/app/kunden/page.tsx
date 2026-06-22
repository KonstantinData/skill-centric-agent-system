import Script from "next/script";
import { PageHero } from "@/components/chrome/page-hero";
import { Button, LinkButton } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchCustomersState } from "@/lib/dkh-api";
import { displayName } from "@/lib/utils";

export default async function CustomersPage() {
  const userEmail = await getUserEmail();
  const state = await fetchCustomersState(userEmail);

  return (
    <div className="content-stack">
      <PageHero
        title="Kunden"
        subtitle="Suche, Dubletten-sensible Neuanlage und direkter Einstieg in Kundenakten."
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
          <p data-customer-search-empty hidden className="text-sm text-[var(--muted)]">
            Kein Treffer. Legen Sie den Kunden unten neu an.
          </p>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel>
          <h2 className="section-title">Kunde anlegen</h2>
          <form className="mt-4 grid gap-3" action="/api/kunden/customers?return_to=/kunden" method="post">
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Typ">
                <Select name="customer_type" defaultValue="private">
                  <option value="private">Privat</option>
                  <option value="company">Firma</option>
                </Select>
              </Label>
              <Label label="Kundennummer">
                <Field name="customer_number" />
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
              <input name="create_direct_case" value="true" type="checkbox" defaultChecked />
              Direkt einen Vorgang anlegen
            </label>
            <Button type="submit">Kunde speichern</Button>
          </form>
        </Panel>

        <Panel>
          <h2 className="section-title">Aktuelle Kunden</h2>
          <div className="mt-4 grid gap-3">
            {state.customers.map((customer) => (
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
            {state.customers.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">Keine Kunden im Sichtbereich.</p>
            ) : null}
          </div>
        </Panel>
      </div>
      <Script src="/customer-search.v1.js" strategy="afterInteractive" />
    </div>
  );
}
