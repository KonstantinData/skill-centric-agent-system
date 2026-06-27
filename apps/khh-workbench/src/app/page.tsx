import { PageHero } from "@/components/chrome/page-hero";
import { LinkButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { createKhhWorkbenchClient } from "@scas/tenant-workbench-client";
import {
  createDashboardSurfaceContract,
  createDashboardViewModel,
  createWebWorkbenchAdapterPlan,
} from "@scas/tenant-workbench-ui";
import { resolveIcon } from "@/lib/icons";

export default async function Home() {
  const client = createKhhWorkbenchClient();
  const dashboardData = await client.getDashboard();
  const dashboard = createDashboardViewModel(dashboardData);
  const surface = createDashboardSurfaceContract(dashboardData);
  const webPlan = createWebWorkbenchAdapterPlan(surface);

  return (
    <div className="content-stack">
      <PageHero
        title={dashboard.hero.title}
        functionText={dashboard.hero.functionText}
      />

      <div className="day-strip">
        <span>Heute</span>
        {dashboard.dayStrip.map((item) => (
          <strong key={item}>{item}</strong>
        ))}
      </div>

      <div className="signal-grid">
        {dashboard.dailySignals.map((signal) => {
          const Icon = resolveIcon(signal.iconId);
          const className =
            webPlan.componentClassNames[`signal:${signal.signalId}`] ?? "status-card";
          return (
            <Panel key={signal.signalId} className={`${className} tone-${signal.tone}`}>
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
        {dashboard.quickActions.map((action) => {
          const Icon = resolveIcon(action.iconId);
          const className =
            webPlan.componentClassNames[`quick-action:${action.actionId}`] ?? "";
          return (
            <Panel key={action.actionId} className={className}>
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
