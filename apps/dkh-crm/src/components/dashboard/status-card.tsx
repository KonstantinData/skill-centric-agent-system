import type { LucideIcon } from "lucide-react";

export function StatusCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <section className="panel panel-pad">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-[var(--muted)]">{label}</p>
          <p className="mt-2 text-3xl font-bold">{value}</p>
          <p className="mt-1 text-sm text-[var(--muted)]">{detail}</p>
        </div>
        <div className="grid h-11 w-11 place-items-center rounded-lg bg-[var(--surface-soft)] text-[var(--accent-strong)]">
          <Icon size={22} aria-hidden />
        </div>
      </div>
    </section>
  );
}
