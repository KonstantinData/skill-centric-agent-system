import { ArrowRight, LockKeyhole, ShieldCheck, Workflow } from "lucide-react";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import {
  agentRuns,
  cockpitMetrics,
  governanceRails,
  workQueue,
} from "@/lib/workbench-data";

export default function Home() {
  return (
    <div className="content-stack">
      <section className="hero-band">
        <Panel className="grid content-between gap-6 bg-[var(--surface)]">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="badge badge-strong">Liquisto.com</span>
              <span className="badge">liquisto.cloud</span>
              <span className="badge">SCAS Tenant</span>
            </div>
            <h1 className="max-w-3xl text-3xl font-black leading-tight md:text-4xl">
              Operations Workbench für kontrollierte Agent-Arbeit.
            </h1>
            <p className="mt-3 max-w-2xl text-sm font-bold leading-6 text-[var(--muted)]">
              Cockpit, Tasks, Knowledge, Agent Runs, Approvals und Audit laufen
              über die bestehende SCAS-Struktur: ein Runtime-Agent,
              tenant-spezifische Profile, kontrollierte Skills und überprüfbare
              Evidence.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <LinkButton href="/tasks" variant="primary">
              Tasks öffnen <ArrowRight size={16} aria-hidden />
            </LinkButton>
            <LinkButton href="/agent-runs">
              Runs prüfen <Workflow size={16} aria-hidden />
            </LinkButton>
          </div>
        </Panel>

        <Panel>
          <div className="mb-4 flex items-center gap-3">
            <div className="icon-btn">
              <LockKeyhole size={18} aria-hidden />
            </div>
            <div>
              <h2 className="section-title">Control Boundary</h2>
              <p className="text-sm text-[var(--muted)]">
                Sichtbare Betriebsregeln für Liquisto
              </p>
            </div>
          </div>
          <div className="grid gap-2">
            {governanceRails.map((rail) => (
              <div
                key={rail}
                className="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] px-3 py-2 text-sm font-bold"
              >
                <ShieldCheck size={16} className="text-[var(--accent)]" aria-hidden />
                <span>{rail}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      <div className="metric-grid">
        {cockpitMetrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <Panel key={metric.label}>
              <div className="mb-4 flex items-center justify-between gap-3">
                <p className="text-sm font-black text-[var(--muted)]">
                  {metric.label}
                </p>
                <Icon size={18} className="text-[var(--accent)]" aria-hidden />
              </div>
              <p className="text-3xl font-black">{metric.value}</p>
              <p className="mt-1 text-sm text-[var(--muted)]">{metric.detail}</p>
            </Panel>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="section-title">Akute Arbeit</h2>
              <p className="text-sm text-[var(--muted)]">
                Outcome-first Queue mit Review- und Risikosignal
              </p>
            </div>
            <LinkButton href="/approvals">Freigaben</LinkButton>
          </div>
          <div className="grid gap-3">
            {workQueue.map((item) => (
              <article
                key={item.title}
                className="rounded-lg border border-[var(--border)] bg-[var(--field-surface)] p-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-black">{item.title}</p>
                    <p className="mt-1 text-sm text-[var(--muted)]">{item.scope}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <span className="badge">{item.status}</span>
                    <span className="badge badge-strong">{item.risk}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className="mb-4">
            <h2 className="section-title">Agent Runs</h2>
            <p className="text-sm text-[var(--muted)]">
              Single-Agent-Runtime mit Profil- und Validator-Sicht
            </p>
          </div>
          <div className="grid gap-3">
            {agentRuns.map((run) => (
              <article
                key={run.id}
                className="rounded-lg border border-[var(--border)] bg-[var(--field-surface)] p-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-xs font-black text-[var(--muted)]">
                    {run.id}
                  </p>
                  <span className="badge">{run.state}</span>
                </div>
                <p className="mt-2 font-black">{run.objective}</p>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  {run.profile} · {run.validator}
                </p>
              </article>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
