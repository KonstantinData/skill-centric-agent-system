import { CalendarDays } from "lucide-react";
import { PageHero } from "@/components/chrome/page-hero";
import { AppointmentCard } from "@/components/dashboard/appointment-card";
import { Panel } from "@/components/ui/panel";
import { getUserEmail } from "@/lib/auth";
import { fetchOverviewState } from "@/lib/dkh-api";
import { isToday } from "@/lib/utils";

export default async function AppointmentsPage() {
  const userEmail = await getUserEmail();
  const state = await fetchOverviewState(userEmail);
  const today = state.appointments.filter((item) => isToday(item.starts_at));

  return (
    <div className="content-stack">
      <PageHero
        title="Termine"
        subtitle="Kalenderdaten aus der bestehenden CRM-API mit Konfliktstatus und Vorgangsbezug."
      />
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel>
          <div className="flex items-center gap-3">
            <CalendarDays className="text-[var(--accent-strong)]" size={24} />
            <div>
              <h2 className="section-title">Heute</h2>
              <p className="text-sm text-[var(--muted)]">
                {today.length} Termine im Tagesfenster
              </p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            {today.map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} />
            ))}
            {today.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">Heute sind keine Termine sichtbar.</p>
            ) : null}
          </div>
        </Panel>
        <Panel>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 className="section-title">Alle sichtbaren Termine</h2>
            <div className="flex gap-2">
              <span className="badge">Tag</span>
              <span className="badge">Woche</span>
              <span className="badge">Monat</span>
            </div>
          </div>
          <div className="grid gap-3">
            {state.appointments.map((appointment) => (
              <AppointmentCard key={appointment.id} appointment={appointment} />
            ))}
            {state.appointments.length === 0 ? (
              <p className="text-sm text-[var(--muted)]">
                Die API liefert aktuell keine Termine.
              </p>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}
