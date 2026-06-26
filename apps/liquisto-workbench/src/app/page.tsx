import {
  ArrowRight,
  Braces,
  CircleDot,
  DatabaseZap,
  FileCheck2,
  LockKeyhole,
  Search,
  ShieldCheck,
  Workflow,
} from "lucide-react";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import {
  agentRuns,
  businessProcesses,
  commandSuggestions,
  cockpitMetrics,
  dataSourceHealth,
  evidenceTimeline,
  executionPhases,
  governanceRails,
  scasWorkbenchAreas,
  systemSignals,
  workQueue,
} from "@/lib/workbench-data";

export default function Home() {
  return (
    <div className="content-stack">
      <section className="command-surface">
        <div className="command-input">
          <Search size={18} aria-hidden />
          <span>Command Center</span>
          <strong>Search inventory, initiatives, partners, or SCAS evidence</strong>
        </div>
        <div className="command-suggestions">
          {commandSuggestions.map((suggestion) => (
            <button key={suggestion} type="button" className="command-chip">
              {suggestion}
            </button>
          ))}
        </div>
      </section>

      <section className="hero-band">
        <Panel className="hero-panel grid content-between gap-6">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="badge badge-strong">Liquisto.com</span>
              <span className="badge">liquisto.cloud</span>
              <span className="badge">Business Platform</span>
            </div>
            <h1 className="max-w-3xl text-3xl font-black leading-tight md:text-5xl">
              Business process platform for excess inventory, circular economy, and data-driven decisions.
            </h1>
            <p className="mt-3 max-w-2xl text-sm font-bold leading-6 text-[var(--muted)]">
              Liquisto coordinates inventory intake, excess and shortage
              analysis, initiatives, monetization, repurposing, and partner
              work. The SCAS Workbench is one register inside this platform,
              not the primary product purpose.
            </p>
          </div>
          <div className="phase-rail">
            {executionPhases.map((phase) => {
              const Icon = phase.icon;
              return (
                <div key={phase.label} className={`phase-step phase-${phase.value}`}>
                  <Icon size={15} aria-hidden />
                  <span>{phase.label}</span>
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2">
            <LinkButton href="/initiative-management" variant="primary">
              Open initiatives <ArrowRight size={16} aria-hidden />
            </LinkButton>
            <LinkButton href="/scas-workbench">
              SCAS Workbench <Workflow size={16} aria-hidden />
            </LinkButton>
          </div>
        </Panel>

        <Panel className="control-panel">
          <div className="mb-4 flex items-center gap-3">
            <div className="icon-btn">
              <LockKeyhole size={18} aria-hidden />
            </div>
            <div>
              <h2 className="section-title">Control Boundary</h2>
              <p className="text-sm text-[var(--muted)]">
                SCAS as the control layer beneath Liquisto processes
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
            <Panel key={metric.label} className={`metric-card tone-${metric.tone}`}>
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

      <div className="system-grid">
        {businessProcesses.map((process) => {
          const Icon = process.icon;
          return (
            <article key={process.title} className="system-tile tone-info">
              <div className="flex items-center justify-between gap-3">
                <Icon size={17} aria-hidden />
                <span className="status-dot" aria-hidden />
              </div>
              <p className="mt-3 text-xs font-black uppercase text-[var(--muted)]">
                Process
              </p>
              <p className="mt-1 text-lg font-black">{process.title}</p>
              <p className="mt-1 text-sm text-[var(--muted)]">{process.detail}</p>
            </article>
          );
        })}
      </div>

      <div className="system-grid">
        {systemSignals.map((signal) => {
          const Icon = signal.icon;
          return (
            <article key={signal.label} className={`system-tile tone-${signal.tone}`}>
              <div className="flex items-center justify-between gap-3">
                <Icon size={17} aria-hidden />
                <span className="status-dot" aria-hidden />
              </div>
              <p className="mt-3 text-xs font-black uppercase text-[var(--muted)]">
                {signal.label}
              </p>
              <p className="mt-1 text-lg font-black">{signal.value}</p>
              <p className="mt-1 text-sm text-[var(--muted)]">{signal.detail}</p>
            </article>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="section-title">Business Processes</h2>
              <p className="text-sm text-[var(--muted)]">
                Operational queue across intake, analysis, management, and monetization
              </p>
            </div>
            <LinkButton href="/approvals">Approvals</LinkButton>
          </div>
          <div className="work-table">
            {workQueue.map((item) => (
              <article
                key={item.title}
                className="work-row"
              >
                <div className="min-w-0">
                  <p className="font-black">{item.title}</p>
                  <p className="mt-1 text-sm text-[var(--muted)]">{item.scope}</p>
                </div>
                <div className="work-meta">
                  <span>{item.owner}</span>
                  <span>{item.due}</span>
                  <span>{item.confidence}</span>
                </div>
                <div className="work-badges">
                  <span className="badge">{item.status}</span>
                  <span className="badge badge-strong">{item.risk}</span>
                </div>
              </article>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className="mb-4">
            <h2 className="section-title">SCAS Workbench Register</h2>
            <p className="text-sm text-[var(--muted)]">
              Technical work areas as one register inside the business platform
            </p>
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            {scasWorkbenchAreas.map((area) => (
              <span key={area} className="badge badge-strong">
                {area}
              </span>
            ))}
          </div>
          <div className="grid gap-3">
            {agentRuns.map((run) => (
              <article
                key={run.id}
                className={`run-card tone-${run.tone}`}
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
                <div className="mt-3 flex items-center justify-between gap-3 text-xs font-black text-[var(--muted)]">
                  <span>{run.evidence}</span>
                  <span>{run.progress}</span>
                </div>
                <div className="progress-track mt-2">
                  <div style={{ width: run.progress }} />
                </div>
              </article>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel>
          <div className="mb-4 flex items-center gap-3">
            <FileCheck2 size={18} className="text-[var(--accent)]" aria-hidden />
            <div>
              <h2 className="section-title">Evidence Timeline</h2>
              <p className="text-sm text-[var(--muted)]">
                Audit trail instead of raw tool output
              </p>
            </div>
          </div>
          <div className="timeline">
            {evidenceTimeline.map((event) => (
              <article key={`${event.time}-${event.title}`} className="timeline-row">
                <span className="timeline-time">{event.time}</span>
                <span className="timeline-marker" aria-hidden />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-black">{event.title}</p>
                    <span className="badge">{event.state}</span>
                  </div>
                  <p className="mt-1 text-sm text-[var(--muted)]">{event.detail}</p>
                </div>
              </article>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <DatabaseZap size={18} className="text-[var(--accent)]" aria-hidden />
              <div>
                <h2 className="section-title">Data Source Health</h2>
                <p className="text-sm text-[var(--muted)]">
                  Visible scope and sync signals
                </p>
              </div>
            </div>
            <Braces size={18} className="text-[var(--muted)]" aria-hidden />
          </div>
          <div className="source-table">
            {dataSourceHealth.map((source) => (
              <article key={source.source} className="source-row">
                <div className="min-w-0">
                  <p className="font-black">{source.source}</p>
                  <p className="mt-1 text-sm text-[var(--muted)]">{source.scope}</p>
                </div>
                <span className="badge">{source.status}</span>
                <span className="source-updated">
                  <CircleDot size={13} aria-hidden />
                  {source.updated}
                </span>
              </article>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
