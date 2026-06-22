import { PageHero } from "@/components/chrome/page-hero";
import { Button } from "@/components/ui/button";
import { Label, Select } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchOverviewState } from "@/lib/dkh-api";
import { formatDateTime } from "@/lib/utils";

export default async function EmailsPage() {
  const userEmail = await getUserEmail();
  const state = await fetchOverviewState(userEmail);

  return (
    <div className="content-stack">
      <PageHero
        title="E-Mails"
        subtitle="E-Mail-Eingang mit Vorgangszuordnung, Vorschlägen und Lebenszyklus-Aktionen."
      />
      <Panel>
        <h2 className="section-title">Nachrichten</h2>
        <div className="mt-4 grid gap-4">
          {state.emails.map((email) => (
            <article key={email.id} className="rounded-lg border border-[var(--border)] bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-bold">{email.subject}</p>
                  <p className="mt-1 text-sm text-[var(--muted)]">
                    {formatDateTime(email.received_at)} ·{" "}
                    {email.participants.map((item) => item.email_address).join(", ")}
                  </p>
                  {email.snippet ? (
                    <p className="mt-2 text-sm text-[var(--muted)]">{email.snippet}</p>
                  ) : null}
                </div>
                <span className="badge">{email.is_unassigned ? "Unzugeordnet" : "Zugeordnet"}</span>
              </div>
              <form
                className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]"
                action="/api/overview/emails/assign?return_to=/emails"
                method="post"
              >
                <input type="hidden" name="email_message_id" value={email.id} />
                <Label label="Vorgang">
                  <Select name="customer_case_id" required defaultValue={email.cases[0]?.id ?? ""}>
                    <option value="">Vorgang wählen</option>
                    {state.customer_cases.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.case_number || `#${item.id}`} · {item.customer_display_name}
                      </option>
                    ))}
                  </Select>
                </Label>
                <div className="flex items-end gap-2">
                  <Button type="submit">Zuordnen</Button>
                  <Button
                    type="submit"
                    formAction={`/api/overview/emails/${email.id}/archive?return_to=/emails`}
                    variant="secondary"
                  >
                    Archiv
                  </Button>
                  <Button
                    type="submit"
                    formAction={`/api/overview/emails/${email.id}/delete?return_to=/emails`}
                    variant="danger"
                  >
                    Löschen
                  </Button>
                </div>
              </form>
              {email.suggestions.length ? (
                <div className="mt-3 grid gap-2">
                  {email.suggestions.map((suggestion) => (
                    <form
                      key={suggestion.id}
                      action={`/api/overview/emails/suggestions/${suggestion.id}/accept?return_to=/emails`}
                      method="post"
                      className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[var(--surface-soft)] p-3"
                    >
                      <span className="text-sm font-bold">
                        Vorschlag: {suggestion.case?.customer_display_name || "Ohne Fall"} ·{" "}
                        {Math.round(suggestion.confidence * 100)} %
                      </span>
                      <Button type="submit" variant="secondary">Akzeptieren</Button>
                    </form>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
          {state.emails.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">Keine E-Mails sichtbar.</p>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
