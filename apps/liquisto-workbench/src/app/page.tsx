import {
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
  commandSuggestions,
  cockpitMetrics,
  dataSourceHealth,
  evidenceTimeline,
  executionPhases,
  governanceRails,
  runtimeSurfaces,
  runtimeWorkflowCards,
  scasWorkbenchAreas,
  systemSignals,
  workflowQueue,
} from "@/lib/workbench-data";

export default function Home() {
  return (
    <div className="content-stack">
      <section className="command-surface">
        <div className="command-input">
          <Search size={18} aria-hidden />
          <span>Command Center</span>
          <strong>Search tenant authority, research scope, or isolation evidence</strong>
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
              <span className="badge">Runtime-backed tenant surface</span>
            </div>
            <h1 className="max-w-3xl text-3xl font-black leading-tight md:text-5xl">
              Liquisto tenant workbench for configured research and administration workflows.
            </h1>
            <p className="mt-3 max-w-2xl text-sm font-bold leading-6 text-[var(--muted)]">
              This surface only exposes workflows that are present in the
              Liquisto tenant configuration: tenant-scoped research, owner-only
              tenant administration, and fail-closed isolation evidence.
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
            <LinkButton href="/research" variant="primary">
              Open research <Workflow size={16} aria-hidden />
            </LinkButton>
            <LinkButton href="/admin">
              Admin <LockKeyhole size={16} aria-hidden />
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
                SCAS control layer for the Liquisto tenant
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
        {runtimeSurfaces.map((surface) => {
          const Icon = surface.icon;
          return (
            <article key={surface.title} className="system-tile tone-info">
              <div className="flex items-center justify-between gap-3">
                <Icon size={17} aria-hidden />
                <span className="status-dot" aria-hidden />
              </div>
              <p className="mt-3 text-xs font-black uppercase text-[var(--muted)]">
                Configured Surface
              </p>
              <p className="mt-1 text-lg font-black">{surface.title}</p>
              <p className="mt-1 text-sm text-[var(--muted)]">{surface.detail}</p>
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
              <h2 className="section-title">Configured Runtime Paths</h2>
              <p className="text-sm text-[var(--muted)]">
                Workflows and policy gates present in the Liquisto tenant configuration
              </p>
            </div>
            <LinkButton href="/admin">Admin</LinkButton>
          </div>
          <div className="work-table">
            {workflowQueue.map((item) => (
              <article
                key={item.title}
                className="work-row"
              >
                <div className="min-w-0">
                  <p className="font-black">{item.title}</p>
                  <p className="mt-1 text-sm text-[var(--muted)]">{item.scope}</p>
                </div>
                <div className="work-meta">
                  <span>{item.role}</span>
                  <span>{item.validator}</span>
                </div>
                <div className="work-badges">
                  <span className="badge">{item.status}</span>
                </div>
              </article>
            ))}
          </div>
        </Panel>

        <Panel>
          <div className="mb-4">
            <h2 className="section-title">Runtime Configuration</h2>
            <p className="text-sm text-[var(--muted)]">
              Visible areas are limited to configured Liquisto capabilities
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
            {runtimeWorkflowCards.map((workflow) => (
              <article
                key={workflow.id}
                className={`run-card tone-${workflow.tone}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-xs font-black text-[var(--muted)]">
                    {workflow.id}
                  </p>
                  <span className="badge">{workflow.capability}</span>
                </div>
                <p className="mt-2 font-black">{workflow.title}</p>
                <p className="mt-1 text-sm text-[var(--muted)]">
                  {workflow.validator}
                </p>
                <div className="mt-3 flex items-center justify-between gap-3 text-xs font-black text-[var(--muted)]">
                  <span>{workflow.evidence}</span>
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
                <h2 className="section-title">Runtime Evidence</h2>
                <p className="text-sm text-[var(--muted)]">
                  Configuration and isolation signals behind the visible workflows
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
