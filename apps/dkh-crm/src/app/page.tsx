import {
  CalendarDays,
  CheckSquare,
  Inbox,
  ShieldAlert,
  UsersRound,
} from "lucide-react";
import { PageHero } from "@/components/chrome/page-hero";
import { AppointmentCard } from "@/components/dashboard/appointment-card";
import { StatusCard } from "@/components/dashboard/status-card";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchOverviewState } from "@/lib/dkh-api";
import { formatDateTime, isOverdue, isToday, priorityLabel } from "@/lib/utils";

export default async function Home() {
  const userEmail = await getUserEmail();
  const state = await fetchOverviewState(userEmail);
  const todaysAppointments = state.appointments.filter((item) =>
    isToday(item.starts_at),
  );
  const overdueTasks = state.tasks.filter((task) => isOverdue(task.due_at));
  const unassignedEmails = state.emails.filter((email) => email.is_unassigned);
  const conflicts = state.appointments.filter(
    (item) => item.conflict_status && item.conflict_status !== "clear",
  );

  return (
    <div className="content-stack">
      <PageHero
        title="CRM Arbeitsbereich"
        subtitle="Termine, Aufgaben, E-Mails, Kundenakten und Vorgänge in einer gemeinsamen Arbeitsoberfläche."
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <StatusCard
          label="Heutige Termine"
          value={todaysAppointments.length}
          detail={`${state.appointments.length} Termine insgesamt`}
          icon={CalendarDays}
        />
        <StatusCard
          label="Offene Aufgaben"
          value={state.tasks.length}
          detail={`${overdueTasks.length} überfällig`}
          icon={CheckSquare}
        />
        <StatusCard
          label="Unzugeordnete E-Mails"
          value={unassignedEmails.length}
          detail={`${state.emails.length} Nachrichten sichtbar`}
          icon={Inbox}
        />
        <StatusCard
          label="Aktive Vorgänge"
          value={state.customer_cases.length}
          detail="im aktuellen Sichtbereich"
          icon={UsersRound}
        />
        <StatusCard
          label="Konflikte"
          value={conflicts.length}
          detail="aus Kalender-Sync"
          icon={ShieldAlert}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel>
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="section-title">Nächste Termine</h2>
            <LinkButton href="/termine">Kalender öffnen</LinkButton>
          </div>
          <div className="grid gap-3">
            {state.appointments.slice(0, 5).map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} />
            ))}
            {state.appointments.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                Keine Termine im aktuellen Sichtbereich.
              </p>
            ) : null}
          </div>
        </Panel>

        <Panel>
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="section-title">Akute Arbeit</h2>
            <LinkButton href="/aufgaben">Aufgaben öffnen</LinkButton>
          </div>
          <div className="grid gap-3">
            {state.tasks.slice(0, 6).map((task) => (
              <article
                key={task.id}
                className="rounded-lg border border-[var(--border)] bg-white p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-bold">{task.title}</p>
                    <p className="mt-1 text-sm text-[var(--muted)]">
                      {task.case?.customer_display_name || "Ohne Vorgang"} ·{" "}
                      {formatDateTime(task.due_at)}
                    </p>
                  </div>
                  <span className="badge">{priorityLabel(task.priority)}</span>
                </div>
              </article>
            ))}
            {state.tasks.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">Keine offenen Aufgaben.</p>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}
