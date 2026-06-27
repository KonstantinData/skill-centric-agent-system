import { PageHero } from "@/components/chrome/page-hero";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { dailySignals, quickActions } from "@/lib/workbench-data";

export default function Home() {
  return (
    <div className="content-stack">
      <PageHero
        title="Leitungs-Cockpit"
        functionText="Tageslage, Fristen, Personalrisiken, Dienste und Entwicklung schnell einordnen."
      />

      <div className="day-strip">
        <span>Heute</span>
        <strong>Personal: pruefen</strong>
        <strong>Fristen: 2 kritisch</strong>
        <strong>Kochdienst: bestaetigt</strong>
        <strong>Vorgaenge: 1 offen</strong>
      </div>

      <div className="signal-grid">
        {dailySignals.map((signal) => {
          const Icon = signal.icon;
          return (
            <Panel key={signal.title} className={`status-card tone-${signal.tone}`}>
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="icon-btn">
                  <Icon size={18} aria-hidden />
                </div>
                <span className="badge">{signal.status}</span>
              </div>
              <h2 className="section-title">{signal.title}</h2>
              <p className="mt-2 text-sm font-bold leading-6 text-[var(--muted)]">
                {signal.detail}
              </p>
              <p className="mt-3 text-sm font-black text-[var(--accent-strong)]">
                {signal.action}
              </p>
            </Panel>
          );
        })}
      </div>

      <div className="system-grid">
        {quickActions.map((action) => {
          const Icon = action.icon;
          return (
            <Panel key={action.title}>
              <div className="mb-4 flex items-center justify-between gap-3">
                <div className="icon-btn">
                  <Icon size={18} aria-hidden />
                </div>
                <LinkButton href={action.href}>{action.cta}</LinkButton>
              </div>
              <h2 className="section-title">{action.title}</h2>
              <p className="mt-2 text-sm font-bold leading-6 text-[var(--muted)]">
                {action.detail}
              </p>
            </Panel>
          );
        })}
      </div>
    </div>
  );
}
