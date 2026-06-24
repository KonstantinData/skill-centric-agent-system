import { PageHero } from "@/components/chrome/page-hero";
import { Button, LinkButton } from "@/components/ui/button";
import { Label, Select } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchOverviewState } from "@/lib/dkh-api";
import { formatDateTime } from "@/lib/utils";

type EmailsPageProps = {
  searchParams: Promise<{ sender?: string }>;
};

export default async function EmailsPage({ searchParams }: EmailsPageProps) {
  const { sender } = await searchParams;
  const selectedSender = sender?.trim().toLowerCase() ?? "";
  const userEmail = await getUserEmail();
  const state = await fetchOverviewState(userEmail);
  const senderOptions = Array.from(
    state.emails.reduce((options, email) => {
      for (const participant of email.participants) {
        if (participant.type !== "from") continue;
        const address = participant.email_address.trim();
        if (!address) continue;
        const key = address.toLowerCase();
        if (!options.has(key)) {
          options.set(
            key,
            participant.display_name ? `${participant.display_name} <${address}>` : address,
          );
        }
      }
      return options;
    }, new Map<string, string>()),
  ).sort(([, left], [, right]) => left.localeCompare(right, "de"));
  const visibleEmails = selectedSender
    ? state.emails.filter((email) =>
        email.participants.some(
          (participant) =>
            participant.type === "from" &&
            participant.email_address.toLowerCase() === selectedSender,
        ),
      )
    : state.emails;
  const returnTo = selectedSender ? `/emails?sender=${encodeURIComponent(selectedSender)}` : "/emails";
  const encodedReturnTo = encodeURIComponent(returnTo);

  return (
    <div className="content-stack">
      <PageHero
        title="E-Mails"
        subtitle="E-Mail-Eingang mit Vorgangszuordnung, Vorschlägen und Lebenszyklus-Aktionen."
      />
      <Panel>
        <h2 className="section-title">Nachrichten</h2>
        <form
          action="/emails"
          className="mt-4 grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"
          method="get"
        >
          <Label label="Absender filtern">
            <Select name="sender" defaultValue={selectedSender}>
              <option value="">Alle Absender</option>
              {senderOptions.map(([address, label]) => (
                <option key={address} value={address}>
                  {label}
                </option>
              ))}
            </Select>
          </Label>
          <div className="flex items-end gap-2">
            <Button type="submit" variant="secondary">
              Filtern
            </Button>
            {selectedSender ? (
              <LinkButton href="/emails" variant="secondary">
                Zurücksetzen
              </LinkButton>
            ) : null}
          </div>
        </form>
        <div className="mt-4 grid gap-4">
          {visibleEmails.map((email) => (
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
              <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
                <form
                  className="grid gap-3 md:grid-cols-[1fr_auto]"
                  action={`/api/overview/emails/assign?return_to=${encodedReturnTo}`}
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
                  <div className="flex items-end">
                    <Button type="submit">Zuordnen</Button>
                  </div>
                </form>
                <div className="flex items-end gap-2">
                  <form
                    action={`/api/overview/emails/${email.id}/delete?return_to=${encodedReturnTo}`}
                    method="post"
                  >
                    <Button type="submit" variant="danger">
                      Löschen
                    </Button>
                  </form>
                </div>
              </div>
              {email.suggestions.length ? (
                <div className="mt-3 grid gap-2">
                  {email.suggestions.map((suggestion) => (
                    <form
                      key={suggestion.id}
                      action={`/api/overview/emails/suggestions/${suggestion.id}/accept?return_to=${encodedReturnTo}`}
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
          {visibleEmails.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">Keine E-Mails sichtbar.</p>
          ) : null}
        </div>
      </Panel>
    </div>
  );
}
