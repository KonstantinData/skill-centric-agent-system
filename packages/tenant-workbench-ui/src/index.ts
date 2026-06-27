import type {
  DailySignal,
  QuickAction,
  TenantWorkbenchDefinition,
  WorkbenchIconId,
  WorkbenchNavigationItem,
  WorkbenchSection,
} from "@scas/tenant-workbench-domain";
import type { TenantWorkbenchDashboard } from "@scas/tenant-workbench-client";

export type WorkbenchIconContract = {
  readonly iconId: WorkbenchIconId;
  readonly accessibilityLabel: string;
};

export type DashboardSignalViewModel = DailySignal & WorkbenchIconContract;
export type QuickActionViewModel = QuickAction & WorkbenchIconContract;

export type DashboardViewModel = {
  readonly hero: TenantWorkbenchDashboard["hero"];
  readonly dayStrip: readonly string[];
  readonly dailySignals: readonly DashboardSignalViewModel[];
  readonly quickActions: readonly QuickActionViewModel[];
  readonly privacyRules: readonly string[];
};

export type SectionViewModel = WorkbenchSection & WorkbenchIconContract;

export function createNavigationViewModel(
  navigation: readonly WorkbenchNavigationItem[],
) {
  return navigation.map((item) => ({
    ...item,
    accessibilityLabel: item.label,
  }));
}

export function createMobileNavigationViewModel(
  navigation: readonly WorkbenchNavigationItem[],
  limit = 5,
) {
  return createNavigationViewModel(navigation).slice(0, limit);
}

export function createDashboardViewModel(
  dashboard: TenantWorkbenchDashboard,
): DashboardViewModel {
  return {
    hero: dashboard.hero,
    dayStrip: ["Personal: pruefen", "Fristen: 2 kritisch", "Kochdienst: bestaetigt", "Vorgaenge: 1 offen"],
    dailySignals: dashboard.dailySignals.map((signal) => ({
      ...signal,
      accessibilityLabel: signal.title,
    })),
    quickActions: dashboard.quickActions.map((action) => ({
      ...action,
      accessibilityLabel: action.title,
    })),
    privacyRules: dashboard.privacyRules,
  };
}

export function createSectionViewModel(section: WorkbenchSection): SectionViewModel {
  return {
    ...section,
    accessibilityLabel: section.title,
  };
}

export function createWorkbenchDefinitionSummary(
  definition: TenantWorkbenchDefinition,
) {
  return {
    scope: definition.scope,
    routeIds: definition.navigation.map((item) => item.routeId),
    sectionIds: Object.keys(definition.sections),
  } as const;
}
