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
  const currentUserId = state.current_user.primary_user_id;
  const assignableUsers =
    state.users.length > 0 || !currentUserId
      ? state.users
      : [
          {
            id: currentUserId,
            first_name: state.current_user.display_name,
            last_name: "",
            email: state.current_user.email,
            roles: [],
          },
        ];
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
          <h2 className="section-title">Neukundenanlage</h2>
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
          <div
            data-customer-create-choice
            hidden
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-4"
          >
            <p className="text-sm font-bold text-[var(--ink)]">Kein Treffer gefunden</p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Legen Sie zuerst fest, ob eine schlanke Leadakte oder direkt eine Kundenakte entstehen soll.
            </p>
            <div className="mt-3 flex flex-wrap gap-3">
              <button type="button" className="btn btn-primary" data-lead-create-open>
                Leadanlage
              </button>
              <button type="button" className="btn btn-secondary" data-customer-create-open>
                Kundenanlage
              </button>
            </div>
          </div>
        </div>
      </Panel>

      <div className="grid items-stretch gap-4 xl:grid-cols-2">
        <Panel className="h-full">
          <div data-customer-direct-search className="grid gap-3">
            <h2 className="section-title">Kunden direkt Suche</h2>
            <div className="grid gap-3 md:grid-cols-[1fr_220px]">
              <input
                data-customer-search-input
                className="field"
                name="direct_q"
                type="search"
                autoComplete="off"
                placeholder="Name, E-Mail, Kundennummer oder Telefon"
              />
              <Select data-customer-status-filter name="customer_status" defaultValue="active">
                <option value="active">Aktive Kunden</option>
                <option value="closed">Abgeschlossene Kunden</option>
                <option value="all">Alle Kunden</option>
              </Select>
            </div>
            <p data-customer-search-hint className="text-sm text-[var(--muted)]">
              Geben Sie mindestens drei Zeichen ein.
            </p>
            <div data-customer-search-results hidden />
          </div>
        </Panel>

        <Panel className="h-full">
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
          <form
            data-customer-create-form
            className="mt-4 grid gap-3"
            action="/api/kunden/customers?return_to=/kunden"
            method="post"
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Kundentyp">
                <Select name="customer_type" defaultValue="private" data-customer-type-select>
                  <option value="private">Privatkunde</option>
                  <option value="company">Objektkunde</option>
                </Select>
              </Label>
              <Label label="Kundennummer">
                <Field value="Wird beim Speichern automatisch vergeben" disabled />
              </Label>
            </div>
            <div data-customer-type-section="private" className="grid gap-3">
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Anrede">
                  <Select name="salutation" defaultValue="">
                    <option value="">Keine Angabe</option>
                    <option value="Herr">Herr</option>
                    <option value="Frau">Frau</option>
                    <option value="Divers">Divers</option>
                    <option value="Familie">Familie</option>
                  </Select>
                </Label>
                <Label label="Titel">
                  <Select name="title" defaultValue="">
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
                  <Field name="first_name" />
                </Label>
                <Label label="Nachname">
                  <Field name="last_name" />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="E-Mail">
                  <Field name="primary_email" type="email" />
                </Label>
                <Label label="Telefon">
                  <Field name="primary_phone" />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-4">
                <Label label="Straße" className="md:col-span-2">
                  <Field name="street" />
                </Label>
                <Label label="Hausnummer">
                  <Field name="house_number" />
                </Label>
                <Label label="PLZ">
                  <Field name="postal_code" />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Ort">
                  <Field name="city" />
                </Label>
                <Label label="Land">
                  <Select name="country" defaultValue="DE" data-customer-country-select>
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
            <div data-customer-type-section="company" className="grid gap-3">
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Firma">
                  <Field name="company_name" />
                </Label>
                <Label label="Objektkunden-Art">
                  <Select name="object_customer_label" defaultValue="">
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
                  <Field name="primary_email" type="email" />
                </Label>
                <Label label="Telefon">
                  <Field name="primary_phone" />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-4">
                <Label label="Straße" className="md:col-span-2">
                  <Field name="street" />
                </Label>
                <Label label="Hausnummer">
                  <Field name="house_number" />
                </Label>
                <Label label="PLZ">
                  <Field name="postal_code" />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Ort">
                  <Field name="city" />
                </Label>
                <Label label="Land">
                  <Select name="country" defaultValue="DE" data-customer-country-select>
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
                  <Field name="legal_form" placeholder="z. B. GmbH, KG, AG" />
                </Label>
                <Label label="USt-IdNr.">
                  <Field name="vat_id" placeholder="z. B. DE123456789" />
                </Label>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Label label="Handelsregisternummer">
                  <Field name="registry_number" placeholder="z. B. HRB 12345" />
                </Label>
                <Label label="Registergericht">
                  <Field name="registry_court" placeholder="z. B. Amtsgericht Stuttgart" />
                </Label>
              </div>
              <Label label="Steuernummer">
                <Field name="tax_number" />
              </Label>
              <div className="grid gap-3 border-t border-[var(--border)] pt-3">
                <h3 className="section-title">Ansprechpartner</h3>
                <div className="grid gap-3 md:grid-cols-2">
                  <Label label="Vorname">
                    <Field name="contact_first_name" />
                  </Label>
                  <Label label="Nachname">
                    <Field name="contact_last_name" />
                  </Label>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Label label="E-Mail Ansprechpartner">
                    <Field name="contact_email" type="email" />
                  </Label>
                  <Label label="Telefon Ansprechpartner">
                    <Field name="contact_phone" />
                  </Label>
                </div>
              </div>
            </div>
            <Label label="Steuerbehandlung">
              <Select name="tax_treatment" defaultValue="standard_de">
                <option value="standard_de">Deutschland Standard</option>
                <option value="eu_business">EU-Unternehmen mit USt-IdNr.</option>
                <option value="third_country_export">Drittland / Ausfuhr prüfen</option>
                <option value="switzerland_export">Schweiz / Ausfuhr prüfen</option>
                <option value="nato_forces">NATO / US-Streitkräfte prüfen</option>
                <option value="custom">Abweichend / manuell prüfen</option>
              </Select>
            </Label>
            <div
              data-customer-custom-vat
              className="grid gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3 md:grid-cols-2"
              hidden
            >
              <input type="hidden" name="has_custom_vat" value="false" data-customer-custom-vat-flag />
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
                  data-customer-custom-vat-rate
                />
              </Label>
              <Label label="Bezeichnung">
                <Select
                  name="custom_vat_rate_label"
                  defaultValue=""
                  disabled
                  data-customer-custom-vat-label
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
                placeholder="z. B. Ausfuhrnachweis erforderlich, NATO-Bescheinigung prüfen"
              />
            </Label>
            <Label label="Zuständig">
              <Select name="owner_user_id" defaultValue={currentUserId ? String(currentUserId) : undefined}>
                {assignableUsers.map((user) => (
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
              <input
                name="create_case"
                value="true"
                type="checkbox"
                data-customer-create-case-toggle
              />
              Direkt einen Vorgang anlegen
            </label>
            <div data-customer-case-details className="grid gap-3">
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
                <Select name="responsible_user_id" defaultValue={currentUserId ? String(currentUserId) : undefined}>
                  {assignableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {displayName(user.first_name, user.last_name) || user.email}
                    </option>
                  ))}
                </Select>
              </Label>
            </div>
            <Button type="submit">Kunde speichern</Button>
          </form>
        </Panel>
      </div>
      <div
        data-lead-create-modal
        hidden
        className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lead-create-title"
      >
        <Panel className="max-h-[92vh] w-full max-w-2xl overflow-y-auto">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="lead-create-title" className="section-title">Lead anlegen</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Erfassen Sie nur die ersten Kontaktdaten. Ein Vorgang entsteht erst bei der Umwandlung zum Kunden.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              data-lead-create-close
              aria-label="Leadanlage schließen"
            >
              Schließen
            </button>
          </div>
          <form
            data-lead-create-form
            className="mt-4 grid gap-3"
            action="/api/kunden/leads?return_to=/kunden"
            method="post"
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Source">
                <Select name="source" defaultValue="website" required>
                  <option value="website">Website</option>
                  <option value="facebook">Facebook</option>
                  <option value="instagram">Instagram</option>
                  <option value="email">E-Mail</option>
                  <option value="phone">Telefon</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="showroom">Ausstellung</option>
                  <option value="referral">Empfehlung</option>
                  <option value="partner">Partner</option>
                  <option value="other">Sonstiges</option>
                </Select>
              </Label>
              <Label label="Eingangskanal">
                <Select name="source_channel" defaultValue="website">
                  <option value="website">Website / Formular</option>
                  <option value="facebook">Facebook</option>
                  <option value="instagram">Instagram</option>
                  <option value="email">E-Mail</option>
                  <option value="phone">Telefon</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="showroom">Ausstellung</option>
                  <option value="referral">Empfehlung</option>
                  <option value="partner">Partner</option>
                  <option value="other">Sonstiges</option>
                  <option value="unknown">Unklar</option>
                </Select>
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
            <Label label="Firma / Objektbezug">
              <Field name="company_name" placeholder="Optional, falls Objektkunde oder Firma erkennbar ist" />
            </Label>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="E-Mail">
                <Field name="primary_email" type="email" />
              </Label>
              <Label label="Telefon">
                <Field name="primary_phone" />
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Mobil / WhatsApp">
                <Field name="primary_mobile" />
              </Label>
              <Label label="Bevorzugter Kontaktweg">
                <Select name="preferred_contact_channel" defaultValue="phone">
                  <option value="phone">Telefon</option>
                  <option value="email">E-Mail</option>
                  <option value="mobile">Mobil</option>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="none">Noch unklar</option>
                </Select>
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <Label label="PLZ">
                <Field name="postal_code" />
              </Label>
              <Label label="Ort" className="md:col-span-2">
                <Field name="city" />
              </Label>
            </div>
            <Label label="Kurzbeschreibung">
              <Field name="project_summary" placeholder="z. B. neue Küche, Renovierung, Neubau, grober Zeitraum" />
            </Label>
            <Label label="Erste Nachricht / Gesprächsnotiz">
              <Textarea
                name="initial_message"
                placeholder="Was hat der Lead angefragt oder gesagt?"
                required
              />
            </Label>
            <Label label="Zuständig">
              <Select name="owner_user_id" defaultValue={currentUserId ? String(currentUserId) : undefined}>
                {assignableUsers.map((user) => (
                  <option key={user.id} value={user.id}>
                    {displayName(user.first_name, user.last_name) || user.email}
                  </option>
                ))}
              </Select>
            </Label>
            <Button type="submit">Lead speichern</Button>
          </form>
        </Panel>
      </div>
      <div
        data-customer-email-duplicate-modal
        hidden
        className="fixed inset-0 z-[60] grid place-items-center bg-black/45 p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="customer-email-duplicate-title"
      >
        <Panel className="w-full max-w-2xl">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="customer-email-duplicate-title" className="section-title">
                E-Mail bereits vorhanden
              </h2>
              <p className="mt-1 text-sm text-[var(--muted)]">
                Prüfen Sie den bestehenden Kunden, bevor Sie diese E-Mail erneut verwenden.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              data-customer-email-duplicate-close
              aria-label="Dublettenprüfung schließen"
            >
              Schließen
            </button>
          </div>
          <div data-customer-email-duplicate-results className="mt-4 grid gap-3" />
          <div className="mt-4 flex flex-wrap justify-end gap-3">
            <button type="button" className="btn btn-secondary" data-customer-email-duplicate-close>
              Prüfung schließen
            </button>
            <button type="button" className="btn btn-primary" data-customer-email-duplicate-confirm>
              Trotzdem speichern
            </button>
          </div>
        </Panel>
      </div>
      <Script src="/customer-search.v1.js" strategy="afterInteractive" />
    </div>
  );
}
