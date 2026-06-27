export type TenantId = "tenant_kinderhaus";
export type WorkAreaId = "kinderhaus-heuschrecken";

export type TenantWorkbenchScope = {
  readonly tenantId: TenantId;
  readonly areaId: WorkAreaId;
};

export type WorkbenchRouteId =
  | "today"
  | "deadlines"
  | "staffing"
  | "services"
  | "cases"
  | "occupancy"
  | "development"
  | "documents"
  | "tasks";

export type WorkbenchSectionId = Exclude<WorkbenchRouteId, "today">;

export type WorkbenchIconId =
  | "calendar-clock"
  | "clipboard-check"
  | "file-text"
  | "heart-handshake"
  | "home"
  | "layout-dashboard"
  | "list-checks"
  | "shield-check"
  | "sparkles"
  | "users-round";

export type WorkbenchTone = "success" | "warning" | "danger" | "info";

export type PrivacyClass =
  | "operational-summary"
  | "person-reference-minimal"
  | "protected-case-summary"
  | "document-reference";

export type WorkbenchNavigationItem = {
  readonly routeId: WorkbenchRouteId;
  readonly sectionId?: WorkbenchSectionId;
  readonly href: string;
  readonly label: string;
  readonly iconId: WorkbenchIconId;
  readonly privacyClass: PrivacyClass;
};

export type DailySignal = {
  readonly signalId: string;
  readonly title: string;
  readonly status: string;
  readonly detail: string;
  readonly action: string;
  readonly iconId: WorkbenchIconId;
  readonly tone: WorkbenchTone;
  readonly privacyClass: PrivacyClass;
};

export type QuickAction = {
  readonly actionId: string;
  readonly title: string;
  readonly detail: string;
  readonly href: string;
  readonly cta: string;
  readonly iconId: WorkbenchIconId;
  readonly privacyClass: PrivacyClass;
};

export type WorkbenchSection = {
  readonly sectionId: WorkbenchSectionId;
  readonly routeId: WorkbenchRouteId;
  readonly title: string;
  readonly subtitle: string;
  readonly iconId: WorkbenchIconId;
  readonly items: readonly string[];
  readonly focus: readonly string[];
  readonly privacyClass: PrivacyClass;
};

export type TenantWorkbenchDefinition = {
  readonly scope: TenantWorkbenchScope;
  readonly hero: {
    readonly title: string;
    readonly functionText: string;
  };
  readonly navigation: readonly WorkbenchNavigationItem[];
  readonly dailySignals: readonly DailySignal[];
  readonly quickActions: readonly QuickAction[];
  readonly sections: Readonly<Record<WorkbenchSectionId, WorkbenchSection>>;
  readonly privacyRules: readonly string[];
};

export function getSectionIds(
  definition: TenantWorkbenchDefinition,
): readonly WorkbenchSectionId[] {
  return Object.keys(definition.sections) as WorkbenchSectionId[];
}

export function getSectionByRouteId(
  definition: TenantWorkbenchDefinition,
  routeId: string,
): WorkbenchSection | null {
  const section = Object.values(definition.sections).find(
    (candidate) => candidate.routeId === routeId || candidate.sectionId === routeId,
  );
  return section ?? null;
}
