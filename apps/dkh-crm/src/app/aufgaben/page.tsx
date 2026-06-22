import { PageHero } from "@/components/chrome/page-hero";
import { Button } from "@/components/ui/button";
import { Field, Label, Select, Textarea } from "@/components/ui/form";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchOverviewState } from "@/lib/dkh-api";
import {
  displayName,
  formatDateTime,
  isOverdue,
  priorityLabel,
} from "@/lib/utils";

export default async function TasksPage() {
  const userEmail = await getUserEmail();
  const state = await fetchOverviewState(userEmail);

  return (
    <div className="content-stack">
      <PageHero
        title="Aufgaben"
        subtitle="Aufgaben anlegen, aktualisieren, archivieren und mit Vorgängen verbinden."
      />
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel>
          <h2 className="section-title">Neue Aufgabe</h2>
          <form
            className="mt-4 grid gap-3"
            action="/api/overview/tasks?return_to=/aufgaben"
            method="post"
          >
            <Label label="Titel">
              <Field name="title" required />
            </Label>
            <Label label="Beschreibung">
              <Textarea name="description" />
            </Label>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Status">
                <Select name="status_code" defaultValue="new">
                  {state.task_statuses.map((status) => (
                    <option key={status.code} value={status.code}>
                      {status.name}
                    </option>
                  ))}
                </Select>
              </Label>
              <Label label="Priorität">
                <Select name="priority" defaultValue="normal">
                  <option value="normal">Normal</option>
                  <option value="high">Hoch</option>
                  <option value="urgent">Dringend</option>
                  <option value="low">Niedrig</option>
                </Select>
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Fällig am">
                <Field name="due_at" type="datetime-local" />
              </Label>
              <Label label="Erinnerung">
                <Field name="reminder_at" type="datetime-local" />
              </Label>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <Label label="Zuständig">
                <Select name="assigned_user_id">
                  {state.users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {displayName(user.first_name, user.last_name) || user.email}
                    </option>
                  ))}
                </Select>
              </Label>
              <Label label="Vorgang">
                <Select name="customer_case_id" defaultValue="">
                  <option value="">Ohne Vorgang</option>
                  {state.customer_cases.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.case_number || `#${item.id}`} · {item.customer_display_name}
                    </option>
                  ))}
                </Select>
              </Label>
            </div>
            <label className="flex items-center gap-2 text-sm font-bold">
              <input name="reminder_overview_enabled" value="true" type="checkbox" defaultChecked />
              In der Übersicht erinnern
            </label>
            <label className="flex items-center gap-2 text-sm font-bold">
              <input name="reminder_email_enabled" value="true" type="checkbox" />
              Per E-Mail erinnern
            </label>
            <Button type="submit">Aufgabe speichern</Button>
          </form>
        </Panel>

        <Panel>
          <h2 className="section-title">Offene Aufgaben</h2>
          <div className="mt-4 grid gap-4">
            {state.tasks.map((task) => (
              <article key={task.id} className="rounded-lg border border-[var(--border)] bg-white p-4">
                <form
                  className="grid gap-3"
                  action={`/api/overview/tasks/${task.id}?return_to=/aufgaben`}
                  method="post"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-bold">{task.title}</p>
                      <p className="text-sm text-[var(--muted)]">
                        {task.case?.customer_display_name || "Ohne Vorgang"} ·{" "}
                        {formatDateTime(task.due_at)}
                      </p>
                    </div>
                    <span className="badge">
                      {isOverdue(task.due_at) ? "Überfällig" : priorityLabel(task.priority)}
                    </span>
                  </div>
                  <input type="hidden" name="title" value={task.title} />
                  <input type="hidden" name="description" value={task.description ?? ""} />
                  <input type="hidden" name="priority" value={task.priority} />
                  <input type="hidden" name="due_at" value={task.due_at ?? ""} />
                  <input type="hidden" name="reminder_at" value={task.reminder_at ?? ""} />
                  <input
                    type="hidden"
                    name="assigned_user_id"
                    value={task.assigned_users[0]?.id ?? state.current_user.primary_user_id ?? ""}
                  />
                  <input type="hidden" name="customer_case_id" value={task.case?.id ?? ""} />
                  <Select name="status_code" defaultValue={task.status}>
                    {state.task_statuses.map((status) => (
                      <option key={status.code} value={status.code}>
                        {status.name}
                      </option>
                    ))}
                  </Select>
                  <div className="flex flex-wrap gap-2">
                    <Button type="submit">Status speichern</Button>
                    <Button
                      type="submit"
                      formAction={`/api/overview/tasks/${task.id}/archive?return_to=/aufgaben`}
                      variant="secondary"
                    >
                      Archivieren
                    </Button>
                    <Button
                      type="submit"
                      formAction={`/api/overview/tasks/${task.id}/delete?return_to=/aufgaben`}
                      variant="danger"
                    >
                      Löschen
                    </Button>
                  </div>
                </form>
              </article>
            ))}
            {state.tasks.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">Keine Aufgaben sichtbar.</p>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}
