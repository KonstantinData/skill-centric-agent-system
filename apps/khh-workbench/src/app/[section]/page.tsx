import { notFound } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { PageHero } from "@/components/chrome/page-hero";
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
      <PageHero title={config.title} functionText={config.subtitle} icon={Icon} />

      <div className="section-list">
        {config.items.map((item) => (
          <div className="section-list-item" key={item}>
            <CheckCircle2 size={18} className="check-icon" aria-hidden />
            <p className="font-bold leading-6">{item}</p>
          </div>
        ))}
      </div>

      <Panel>
        <h2 className="section-title">Arbeitsansicht</h2>
        <div className="mt-4 work-table">
          <div className="work-row work-head">
            {config.focus.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <div className="work-row">
            <strong>Beispiel ohne Stammdaten</strong>
            <span>Vorname / Kuerzel / Rolle</span>
            <span className="badge">offen</span>
            <span>naechste Woche</span>
            <span>Originalunterlage pruefen</span>
          </div>
        </div>
      </Panel>
    </div>
  );
}
