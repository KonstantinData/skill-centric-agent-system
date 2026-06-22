import type { OverviewState } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

type Appointment = OverviewState["appointments"][number];

export function AppointmentCard({ appointment }: { appointment: Appointment }) {
  const conflict =
    appointment.conflict_status && appointment.conflict_status !== "clear";
  return (
    <article className="rounded-lg border border-[var(--border)] bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-bold">{appointment.title}</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {formatDateTime(appointment.starts_at)}
            {appointment.ends_at ? ` bis ${formatDateTime(appointment.ends_at)}` : ""}
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {appointment.location ||
              appointment.case?.customer_display_name ||
              "Ohne Ort"}
          </p>
        </div>
        <span className="badge">
          {conflict ? "Konflikt" : appointment.appointment_type || "Termin"}
        </span>
      </div>
    </article>
  );
}
