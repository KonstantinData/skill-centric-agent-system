import {
  LockKeyhole,
  Search,
  Workflow,
} from "lucide-react";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import {
  commandSuggestions,
  workspaceActions,
} from "@/lib/workbench-data";

export default function Home() {
  return (
    <div className="content-stack">
      <section className="command-surface">
        <div className="command-input">
          <Search size={18} aria-hidden />
          <span>Command Center</span>
          <strong>Search research tasks or admin settings</strong>
        </div>
        <div className="command-suggestions">
          {commandSuggestions.map((suggestion) => (
            <button key={suggestion} type="button" className="command-chip">
              {suggestion}
            </button>
          ))}
        </div>
      </section>

      <Panel className="hero-panel grid gap-6">
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <span className="badge badge-strong">Liquisto.com</span>
            <span className="badge">liquisto.cloud</span>
          </div>
          <h1 className="max-w-3xl text-3xl font-black leading-tight md:text-5xl">
            Liquisto workspace
          </h1>
          <p className="mt-3 max-w-2xl text-sm font-bold leading-6 text-[var(--muted)]">
            Start research work or manage the Liquisto tenant.
          </p>
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

      <div className="system-grid">
        {workspaceActions.map((action) => {
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
