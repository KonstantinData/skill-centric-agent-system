import {
  getSectionByRouteId,
  type TenantWorkbenchDefinition,
  type TenantWorkbenchScope,
  type WorkbenchRouteId,
} from "@scas/tenant-workbench-domain";
import {
  khhTenantWorkbenchDefinition,
} from "@scas/tenant-workbench-domain/khh";

export type TenantWorkbenchAuthClaims = {
  readonly email?: string;
  readonly principalId?: string;
  readonly tenantId?: string;
  readonly areaId?: string;
  readonly roles?: readonly string[];
};

export type TenantWorkbenchAuthAdapter = {
  readonly getClaims: () => Promise<TenantWorkbenchAuthClaims>;
};

export type TenantWorkbenchUser = {
  readonly email: string;
  readonly principalId: string;
  readonly roles: readonly string[];
  readonly isAuthenticated: boolean;
  readonly scope: TenantWorkbenchScope;
};

export type TenantWorkbenchDashboard = Pick<
  TenantWorkbenchDefinition,
  "hero" | "dailySignals" | "quickActions" | "privacyRules"
>;

export type TenantWorkbenchTaskSummary = {
  readonly taskId: string;
  readonly title: string;
  readonly routeId: WorkbenchRouteId;
  readonly status: "new" | "planned" | "in-progress" | "waiting" | "review" | "done";
};

export class TenantScopeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TenantScopeError";
  }
}

export function assertTenantScopeMatches(
  actual: { readonly tenantId?: string; readonly areaId?: string } | undefined,
  expected: TenantWorkbenchScope,
): void {
  if (!actual?.tenantId || !actual.areaId) {
    throw new TenantScopeError("Tenant workbench scope is incomplete.");
  }
  if (actual.tenantId !== expected.tenantId || actual.areaId !== expected.areaId) {
    throw new TenantScopeError("Tenant workbench scope mismatch.");
  }
}

export function createCloudflareAccessHeaderAuthAdapter({
  scope,
  getHeader,
}: {
  readonly scope: TenantWorkbenchScope;
  readonly getHeader: (name: string) => string | null | undefined;
}): TenantWorkbenchAuthAdapter {
  return {
    async getClaims() {
      const email =
        getHeader("x-khh-user-email") ??
        getHeader("cf-access-authenticated-user-email") ??
        "";
      const principalId = getHeader("cf-access-user-id") ?? email;

      return {
        email,
        principalId,
        tenantId: scope.tenantId,
        areaId: scope.areaId,
        roles: email ? ["khh-workbench-user"] : [],
      };
    },
  };
}

export function createTenantWorkbenchClient({
  definition,
  authAdapter,
}: {
  readonly definition: TenantWorkbenchDefinition;
  readonly authAdapter?: TenantWorkbenchAuthAdapter;
}) {
  const expectedScope = definition.scope;
  assertTenantScopeMatches(expectedScope, expectedScope);

  return {
    async getCurrentUser(): Promise<TenantWorkbenchUser> {
      const claims = authAdapter ? await authAdapter.getClaims() : {};
      if (claims.tenantId || claims.areaId) {
        assertTenantScopeMatches(
          { tenantId: claims.tenantId, areaId: claims.areaId },
          expectedScope,
        );
      }

      const email = claims.email ?? "";
      return {
        email,
        principalId: claims.principalId ?? email,
        roles: claims.roles ?? [],
        isAuthenticated: Boolean(email),
        scope: expectedScope,
      };
    },
    async getNavigation() {
      return definition.navigation;
    },
    async getDashboard(): Promise<TenantWorkbenchDashboard> {
      return getDashboardSnapshot(definition);
    },
    getDashboardSnapshot(): TenantWorkbenchDashboard {
      return getDashboardSnapshot(definition);
    },
    async getSection(routeId: string) {
      return getSectionByRouteId(definition, routeId);
    },
    getSectionSnapshot(routeId: string) {
      return getSectionByRouteId(definition, routeId);
    },
    async listTasks(): Promise<readonly TenantWorkbenchTaskSummary[]> {
      return [];
    },
    async mutateTask(): Promise<{ readonly ok: false; readonly reason: string }> {
      return {
        ok: false,
        reason: "write-intents-not-enabled",
      };
    },
  };
}

export function createKhhWorkbenchClient(authAdapter?: TenantWorkbenchAuthAdapter) {
  return createTenantWorkbenchClient({
    definition: khhTenantWorkbenchDefinition,
    authAdapter,
  });
}

function getDashboardSnapshot(
  definition: TenantWorkbenchDefinition,
): TenantWorkbenchDashboard {
  return {
    hero: definition.hero,
    dailySignals: definition.dailySignals,
    quickActions: definition.quickActions,
    privacyRules: definition.privacyRules,
  };
}
