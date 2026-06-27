import { notFound } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { PageHero } from "@/components/chrome/page-hero";
import { Panel } from "@/components/ui/panel";
import { createKhhWorkbenchClient } from "@scas/tenant-workbench-client";
import {
  khhSectionAliases,
  type KhhSectionSlug,
} from "@scas/tenant-workbench-domain/khh";
import {
  createSectionSurfaceContract,
  createSectionViewModel,
  createWebWorkbenchAdapterPlan,
} from "@scas/tenant-workbench-ui";
import { resolveIcon } from "@/lib/icons";

type SectionPageProps = {
  params: Promise<{
    section: string;
  }>;
};

export function generateStaticParams() {
  return Object.keys(khhSectionAliases).map((section) => ({ section }));
}

export default async function SectionPage({ params }: SectionPageProps) {
  const { section } = await params;
  if (!(section in khhSectionAliases)) notFound();

  const routeId = khhSectionAliases[section as KhhSectionSlug];
  const client = createKhhWorkbenchClient();
  const sectionConfig = await client.getSection(routeId);
  if (!sectionConfig) notFound();

  const config = createSectionViewModel(sectionConfig);
  const surface = createSectionSurfaceContract(sectionConfig);
  const webPlan = createWebWorkbenchAdapterPlan(surface);
  const Icon = resolveIcon(config.iconId);
  const workTableClassName =
    webPlan.componentClassNames[`section:${config.sectionId}:work-table`] ?? "work-table";

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
        <div className={`mt-4 ${workTableClassName}`}>
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
