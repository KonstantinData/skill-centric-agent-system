import { notFound } from "next/navigation";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { sections, type SectionKey } from "@/lib/workbench-data";

type SectionPageProps = {
  params: Promise<{
    section: string;
  }>;
};

export function generateStaticParams() {
  return Object.keys(sections).map((section) => ({ section }));
}

export default async function SectionPage({ params }: SectionPageProps) {
  const { section } = await params;
  if (!(section in sections)) notFound();

  const config = sections[section as SectionKey];
  const Icon = config.icon;

  return (
    <div className="content-stack">
      <Panel>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="mb-3 flex items-center gap-3">
              <div className="icon-btn">
                <Icon size={18} aria-hidden />
              </div>
              <span className="badge badge-strong">Liquisto Platform</span>
            </div>
            <h1 className="text-3xl font-black">{config.title}</h1>
            <p className="mt-2 max-w-3xl text-sm font-bold leading-6 text-[var(--muted)]">
              {config.subtitle}
            </p>
          </div>
          <LinkButton href="/scas-workbench" variant="primary">
            SCAS Register <ArrowRight size={16} aria-hidden />
          </LinkButton>
        </div>
      </Panel>

      <div className="signal-grid">
        {config.items.map((item) => (
          <Panel key={item}>
            <CheckCircle2 size={18} className="mb-3 text-[var(--accent)]" aria-hidden />
            <p className="font-black">{item}</p>
          </Panel>
        ))}
      </div>

      <Panel>
        <h2 className="section-title">Process And SCAS Anchoring</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3">
            <p className="text-xs font-black uppercase text-[var(--muted)]">
              Composition
            </p>
            <p className="mt-2 text-sm font-bold">
              Task Analyzer and Agent Composer select skills, tools,
              knowledge, and validators.
            </p>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3">
            <p className="text-xs font-black uppercase text-[var(--muted)]">
              Runtime
            </p>
            <p className="mt-2 text-sm font-bold">
              One single agent works only with a validated, immutable
              runtime profile.
            </p>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-soft)] p-3">
            <p className="text-xs font-black uppercase text-[var(--muted)]">
              Evidence
            </p>
            <p className="mt-2 text-sm font-bold">
              Outputs, denials, and approvals remain traceable as auditable
              artifacts.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
