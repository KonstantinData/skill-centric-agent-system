import { AlertTriangle } from "lucide-react";
import { PageHero } from "@/components/chrome/page-hero";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { agentNotes, dailySignals, privacyRules, quickActions } from "@/lib/workbench-data";

export default function Home() {
  return (
    <div className="content-stack">
      <PageHero
        title="Leitungs-Cockpit"
        functionText="Tageslage, Fristen, Personalrisiken, Dienste und Entwicklung schnell einordnen."
      />

      <Panel className="privacy-panel">
        <div className="privacy-card">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle size={18} aria-hidden />
            <p className="font-black">Datenschutz-Leitplanke</p>
          </div>
          <ul className="grid gap-2 text-sm font-bold leading-6 text-[var(--muted)]">
            {privacyRules.slice(0, 3).map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </div>
      </Panel>

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

      <Panel>
        <h2 className="section-title">Agent-Hinweise</h2>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {agentNotes.map((note) => (
            <div className="agent-note" key={note.observation}>
              <p className="text-sm font-black">{note.observation}</p>
              <p className="mt-2 text-sm font-bold text-[var(--muted)]">
                {note.reason}
              </p>
              <p className="mt-2 text-sm font-bold">{note.proposal}</p>
              <span className="badge badge-strong mt-3">{note.approval}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
