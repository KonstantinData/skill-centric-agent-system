import type {
  DailySignal,
  QuickAction,
  TenantWorkbenchDefinition,
  PrivacyClass,
  WorkbenchIconId,
  WorkbenchNavigationItem,
  WorkbenchSection,
  WorkbenchTone,
} from "@scas/tenant-workbench-domain";
import type { TenantWorkbenchDashboard } from "@scas/tenant-workbench-client";

export type WorkbenchPlatform = "web" | "native";

export type WorkbenchDensity = "desktop-dense" | "touch-comfortable";

export type WorkbenchDesignTokens = {
  readonly color: {
    readonly background: string;
    readonly surface: string;
    readonly surfaceStrong: string;
    readonly foreground: string;
    readonly muted: string;
    readonly accent: string;
    readonly accentStrong: string;
    readonly border: string;
    readonly dangerSoft: string;
    readonly warningSoft: string;
    readonly successSoft: string;
  };
  readonly radius: {
    readonly panel: number;
    readonly control: number;
    readonly chip: number;
  };
  readonly spacing: {
    readonly xs: number;
    readonly sm: number;
    readonly md: number;
    readonly lg: number;
    readonly xl: number;
  };
  readonly typography: {
    readonly title: number;
    readonly sectionTitle: number;
    readonly body: number;
    readonly caption: number;
  };
};

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

export type WorkbenchActionContract = {
  readonly actionId: string;
  readonly label: string;
  readonly href: string;
  readonly privacyClass: PrivacyClass;
  readonly writeIntent: "disabled";
};

export type WorkbenchComponentContract = {
  readonly componentId: string;
  readonly kind:
    | "navigation-item"
    | "dashboard-signal"
    | "quick-action"
    | "section-summary"
    | "work-table";
  readonly title: string;
  readonly body?: string;
  readonly icon: WorkbenchIconContract;
  readonly tone?: WorkbenchTone;
  readonly privacyClass: PrivacyClass;
  readonly density: WorkbenchDensity;
  readonly actions: readonly WorkbenchActionContract[];
};

export type WorkbenchSurfaceContract = {
  readonly surfaceId: "dashboard" | `section:${string}` | "navigation";
  readonly title: string;
  readonly components: readonly WorkbenchComponentContract[];
  readonly tokens: WorkbenchDesignTokens;
  readonly supportedPlatforms: readonly WorkbenchPlatform[];
};

export type WebWorkbenchAdapterPlan = {
  readonly platform: "web";
  readonly density: "desktop-dense";
  readonly preserveDesktopSidebar: true;
  readonly componentClassNames: Readonly<Record<string, string>>;
};

export type NativeWorkbenchAdapterPlan = {
  readonly platform: "native";
  readonly density: "touch-comfortable";
  readonly safeAreaRequired: true;
  readonly scrollContainerRequired: true;
  readonly componentRoles: Readonly<Record<string, "button" | "summary" | "table" | "tab">>;
};

export const khhWorkbenchDesignTokens: WorkbenchDesignTokens = {
  color: {
    background: "#fafaf7",
    surface: "#fffefb",
    surfaceStrong: "#f2efe5",
    foreground: "#1e293b",
    muted: "#475569",
    accent: "#6f8f72",
    accentStrong: "#36533b",
    border: "#d8d0bf",
    dangerSoft: "#f8dddd",
    warningSoft: "#f7e7b7",
    successSoft: "#dcebd8",
  },
  radius: {
    panel: 8,
    control: 8,
    chip: 999,
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
  },
  typography: {
    title: 28,
    sectionTitle: 18,
    body: 15,
    caption: 12,
  },
};

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

export function createDashboardSurfaceContract(
  dashboard: TenantWorkbenchDashboard,
): WorkbenchSurfaceContract {
  return {
    surfaceId: "dashboard",
    title: dashboard.hero.title,
    tokens: khhWorkbenchDesignTokens,
    supportedPlatforms: ["web", "native"],
    components: [
      ...dashboard.dailySignals.map((signal): WorkbenchComponentContract => ({
        componentId: `signal:${signal.signalId}`,
        kind: "dashboard-signal",
        title: signal.title,
        body: signal.detail,
        icon: {
          iconId: signal.iconId,
          accessibilityLabel: signal.title,
        },
        tone: signal.tone,
        privacyClass: signal.privacyClass,
        density: "desktop-dense",
        actions: [
          {
            actionId: `${signal.signalId}:inspect`,
            label: signal.action,
            href: "/",
            privacyClass: signal.privacyClass,
            writeIntent: "disabled",
          },
        ],
      })),
      ...dashboard.quickActions.map((action): WorkbenchComponentContract => ({
        componentId: `quick-action:${action.actionId}`,
        kind: "quick-action",
        title: action.title,
        body: action.detail,
        icon: {
          iconId: action.iconId,
          accessibilityLabel: action.title,
        },
        privacyClass: action.privacyClass,
        density: "desktop-dense",
        actions: [
          {
            actionId: action.actionId,
            label: action.cta,
            href: action.href,
            privacyClass: action.privacyClass,
            writeIntent: "disabled",
          },
        ],
      })),
    ],
  };
}

export function createSectionSurfaceContract(
  section: WorkbenchSection,
): WorkbenchSurfaceContract {
  return {
    surfaceId: `section:${section.sectionId}`,
    title: section.title,
    tokens: khhWorkbenchDesignTokens,
    supportedPlatforms: ["web", "native"],
    components: [
      {
        componentId: `section:${section.sectionId}:summary`,
        kind: "section-summary",
        title: section.title,
        body: section.subtitle,
        icon: {
          iconId: section.iconId,
          accessibilityLabel: section.title,
        },
        privacyClass: section.privacyClass,
        density: "desktop-dense",
        actions: [],
      },
      {
        componentId: `section:${section.sectionId}:work-table`,
        kind: "work-table",
        title: "Arbeitsansicht",
        body: section.focus.join(" | "),
        icon: {
          iconId: section.iconId,
          accessibilityLabel: `${section.title} Arbeitsansicht`,
        },
        privacyClass: section.privacyClass,
        density: "desktop-dense",
        actions: [],
      },
    ],
  };
}

export function createWebWorkbenchAdapterPlan(
  surface: WorkbenchSurfaceContract,
): WebWorkbenchAdapterPlan {
  return {
    platform: "web",
    density: "desktop-dense",
    preserveDesktopSidebar: true,
    componentClassNames: Object.fromEntries(
      surface.components.map((component) => [
        component.componentId,
        component.kind === "work-table" ? "work-table" : "status-card",
      ]),
    ),
  };
}

export function createNativeWorkbenchAdapterPlan(
  surface: WorkbenchSurfaceContract,
): NativeWorkbenchAdapterPlan {
  return {
    platform: "native",
    density: "touch-comfortable",
    safeAreaRequired: true,
    scrollContainerRequired: true,
    componentRoles: Object.fromEntries(
      surface.components.map((component) => [
        component.componentId,
        component.kind === "quick-action"
          ? "button"
          : component.kind === "work-table"
            ? "table"
            : component.kind === "navigation-item"
              ? "tab"
              : "summary",
      ]),
    ) as NativeWorkbenchAdapterPlan["componentRoles"],
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
