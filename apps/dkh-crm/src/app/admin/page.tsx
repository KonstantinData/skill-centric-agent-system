import { PageHero } from "@/components/chrome/page-hero";
import { Button } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchAdminState } from "@/lib/dkh-api";

type AdminPageProps = {
  searchParams: Promise<{ bereich?: string }>;
};

const ADMIN_SECTIONS = [
  {
    key: "benutzer",
    title: "Benutzer",
    description: "Mitarbeiterübersicht, Neuanlage und Bearbeitung.",
  },
  {
    key: "firmenstammdaten",
    title: "Firmenstammdaten",
    description: "Adresse, Kontakt, Handelsregister und zentrale Einstellungen pflegen.",
  },
  {
    key: "integrationen",
    title: "Integrationen",
    description: "Externe Dienste konfigurieren, ohne API-Schlüssel im Klartext zu speichern.",
  },
  {
    key: "system",
    title: "System",
    description: "Systemfunktionen und technische Verwaltung.",
  },
] as const;

type AdminSectionKey = (typeof ADMIN_SECTIONS)[number]["key"];

function normalizeSection(value: string | undefined): AdminSectionKey | null {
  return ADMIN_SECTIONS.some((section) => section.key === value)
    ? (value as AdminSectionKey)
    : null;
}

export default async function AdminPage({ searchParams }: AdminPageProps) {
  const { bereich } = await searchParams;
  const activeSection = normalizeSection(bereich);
  const userEmail = await getUserEmail();
  const state = await fetchAdminState(userEmail);
  const settings = state.company_settings;
  const usersReturnTo = encodeURIComponent("/admin?bereich=benutzer");
  const companyReturnTo = encodeURIComponent("/admin?bereich=firmenstammdaten");
  const integrationsReturnTo = encodeURIComponent("/admin?bereich=integrationen");

  return (
    <div className="content-stack">
      <PageHero
        title="Admin Bereich"
        subtitle="Zentrale Verwaltung für Mitarbeiter, Firmenstammdaten, Integrationen und System."
      />
      {!activeSection ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {ADMIN_SECTIONS.map((section) => (
            <a
              key={section.key}
              href={`/admin?bereich=${section.key}`}
              className="rounded-lg border border-[var(--border)] bg-white p-4 shadow-sm transition hover:border-[var(--accent)] hover:bg-[var(--surface-soft)]"
            >
              <h2 className="text-base font-bold">{section.title}</h2>
              <p className="mt-5 text-sm font-bold leading-relaxed text-[var(--ink)]">
                {section.description}
              </p>
            </a>
          ))}
        </div>
      ) : null}

      {activeSection ? (
        <div>
          <a className="btn btn-secondary" href="/admin">
            Zur Admin-Übersicht
          </a>
        </div>
      ) : null}

      {activeSection === "benutzer" ? (
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel>
          <h2 className="section-title">Mitarbeiter anlegen</h2>
          <form className="mt-4 grid gap-3" action={`/api/admin/users?return_to=${usersReturnTo}`} method="post">
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Vorname">
                <Field name="first_name" required />
              </Label>
              <Label label="Nachname">
                <Field name="last_name" required />
              </Label>
            </div>
            <Label label="E-Mail">
              <Field name="email" type="email" required />
            </Label>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Telefon">
                <Field name="phone" />
              </Label>
              <Label label="Position">
                <Field name="job_title" />
              </Label>
            </div>
            <Label label="Zeitzone">
              <Field name="timezone" defaultValue="Europe/Berlin" />
            </Label>
            <div className="flex flex-wrap gap-3 text-sm font-bold">
              {state.roles.map((role) => (
                <label key={role.code} className="flex items-center gap-2">
                  <input name={`role_${role.code}`} value="true" type="checkbox" />
                  {role.name}
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm font-bold">
              <input name="is_active" value="true" type="checkbox" defaultChecked />
              Aktiv
            </label>
            <label className="flex items-center gap-2 text-sm font-bold">
              <input name="mfa_required" value="true" type="checkbox" defaultChecked />
              MFA erforderlich
            </label>
            <Button type="submit">Mitarbeiter speichern</Button>
          </form>
        </Panel>

        <Panel>
          <h2 className="section-title">Mitarbeiter</h2>
          <div className="mt-4 grid gap-4">
            {state.users.map((user) => (
              <article key={user.id} className="rounded-lg border border-[var(--border)] bg-white p-4">
                <form
                  className="grid gap-3"
                  action={`/api/admin/users/${user.id}?return_to=${usersReturnTo}`}
                  method="post"
                >
                  <div className="grid gap-3 md:grid-cols-2">
                    <Label label="Vorname">
                      <Field name="first_name" defaultValue={user.first_name} required />
                    </Label>
                    <Label label="Nachname">
                      <Field name="last_name" defaultValue={user.last_name} required />
                    </Label>
                  </div>
                  <Label label="E-Mail">
                    <Field name="email" type="email" defaultValue={user.email} required />
                  </Label>
                  <div className="grid gap-3 md:grid-cols-3">
                    <Label label="Telefon">
                      <Field name="phone" defaultValue={user.phone ?? ""} />
                    </Label>
                    <Label label="Position">
                      <Field name="job_title" defaultValue={user.job_title ?? ""} />
                    </Label>
                    <Label label="Abteilung">
                      <Field name="department" defaultValue={user.department ?? ""} />
                    </Label>
                  </div>
                  <Label label="Zeitzone">
                    <Field name="timezone" defaultValue={user.timezone} />
                  </Label>
                  <div className="flex flex-wrap gap-3 text-sm font-bold">
                    {state.roles.map((role) => {
                      const isLockedAdminRole = user.roles.includes("admin") && role.code === "admin";
                      return (
                        <label key={role.code} className="flex items-center gap-2">
                          {isLockedAdminRole ? <input name="role_admin" value="true" type="hidden" /> : null}
                          <input
                            name={`role_${role.code}`}
                            value="true"
                            type="checkbox"
                            defaultChecked={isLockedAdminRole || user.roles.includes(role.code)}
                            disabled={isLockedAdminRole}
                          />
                          {role.name}
                        </label>
                      );
                    })}
                  </div>
                  <label className="flex items-center gap-2 text-sm font-bold">
                    <input name="is_active" value="true" type="checkbox" defaultChecked={user.is_active} />
                    Aktiv
                  </label>
                  <label className="flex items-center gap-2 text-sm font-bold">
                    <input
                      name="mfa_required"
                      value="true"
                      type="checkbox"
                      defaultChecked={user.security.mfa_required}
                    />
                    MFA erforderlich
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <Button type="submit">Speichern</Button>
                    <Button
                      type="submit"
                      formAction={`/api/admin/users/${user.id}/delete?return_to=${usersReturnTo}`}
                      variant="danger"
                    >
                      Deaktivieren
                    </Button>
                    <input type="hidden" name="confirm_delete" value="true" />
                  </div>
                </form>
              </article>
            ))}
            {state.users.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">Keine Mitarbeiter sichtbar.</p>
            ) : null}
          </div>
        </Panel>
      </div>
      ) : null}

      {activeSection === "firmenstammdaten" ? (
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <h2 className="section-title">Firmendaten</h2>
          <form
            className="mt-4 grid gap-3"
            action={`/api/admin/company-settings?return_to=${companyReturnTo}`}
            method="post"
          >
            <Label label="Unternehmen">
              <Field name="company_name" defaultValue={settings.company_name ?? ""} />
            </Label>
            <Label label="Rechtlicher Name">
              <Field name="legal_name" defaultValue={settings.legal_name ?? ""} />
            </Label>
            <div className="grid gap-3 md:grid-cols-3">
              <Label label="Straße">
                <Field name="street" defaultValue={settings.street ?? ""} />
              </Label>
              <Label label="PLZ">
                <Field name="postal_code" defaultValue={settings.postal_code ?? ""} />
              </Label>
              <Label label="Ort">
                <Field name="city" defaultValue={settings.city ?? ""} />
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="E-Mail">
                <Field name="email" defaultValue={settings.email ?? ""} />
              </Label>
              <Label label="Webseite">
                <Field name="website" defaultValue={settings.website ?? ""} />
              </Label>
            </div>
            <Button type="submit">Firmendaten speichern</Button>
          </form>
        </Panel>
      </div>
      ) : null}

      {activeSection === "integrationen" ? (
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel>
          <h2 className="section-title">Integration anlegen</h2>
          <form
            className="mt-4 grid gap-3"
            action={`/api/admin/integrations?return_to=${integrationsReturnTo}`}
            method="post"
          >
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Code">
                <Field name="integration_code" placeholder="google_calendar" required />
              </Label>
              <Label label="Name">
                <Field name="integration_name" placeholder="Google Calendar" required />
              </Label>
            </div>
            <Label label="Verbindung">
              <Field name="display_name" placeholder="DKH Kalender-Sync" />
            </Label>
            <Label label="Secret-Referenz">
              <Field name="secret_reference" placeholder="hetzner/vault/path" />
            </Label>
            <Label label="Konfiguration JSON">
              <Textarea name="config_json" defaultValue="{}" />
            </Label>
            <Label label="Status">
              <Select name="status" defaultValue="pending">
                <option value="pending">Ausstehend</option>
                <option value="connected">Verbunden</option>
                <option value="error">Fehler</option>
              </Select>
            </Label>
            <label className="flex items-center gap-2 text-sm font-bold">
              <input name="is_enabled" value="true" type="checkbox" defaultChecked />
              Aktiv
            </label>
            <Button type="submit">Integration speichern</Button>
          </form>
          <div className="mt-5 grid gap-2">
            {state.integrations.map((integration) => (
              <p key={integration.id} className="rounded-lg bg-[var(--surface-soft)] p-3 text-sm">
                <strong>{integration.name}</strong> · {integration.is_enabled ? "aktiv" : "inaktiv"} ·{" "}
                {integration.connections.length} Verbindungen
              </p>
            ))}
          </div>
        </Panel>
      </div>
      ) : null}

      {activeSection === "system" ? (
        <Panel>
          <h2 className="section-title">System</h2>
          <p className="mt-3 text-sm text-[var(--muted)]">
            Die Funktionen für diesen Bereich werden separat festgelegt.
          </p>
        </Panel>
      ) : null}
    </div>
  );
}
