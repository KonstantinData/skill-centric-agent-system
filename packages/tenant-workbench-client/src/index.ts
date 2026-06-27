import {
  getSectionByRouteId,
  type TenantWorkbenchDefinition,
  type TenantWorkbenchScope,
  type WorkbenchRouteId,
  type WorkbenchSection,
  type WorkbenchNavigationItem,
} from "@scas/tenant-workbench-domain";
import {
  khhTenantWorkbenchDefinition,
} from "@scas/tenant-workbench-domain/khh";

export type TenantWorkbenchAuthState =
  | "authenticated"
  | "anonymous"
  | "expired";

export type TenantWorkbenchAuthClaims = {
  readonly email?: string;
  readonly principalId?: string;
  readonly tenantId?: string;
  readonly areaId?: string;
  readonly roles?: readonly string[];
  readonly expiresAt?: string;
};

export type TenantWorkbenchAuthSession = {
  readonly state: TenantWorkbenchAuthState;
  readonly claims: TenantWorkbenchAuthClaims;
};

export type TenantWorkbenchAuthAdapter = {
  readonly getSession?: () => Promise<TenantWorkbenchAuthSession>;
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

export type TenantWorkbenchSnapshot = {
  readonly scope: TenantWorkbenchScope;
  readonly navigation: readonly WorkbenchNavigationItem[];
  readonly dashboard: TenantWorkbenchDashboard;
  readonly sections: readonly WorkbenchSection[];
  readonly cachedAt: string;
};

export type TenantWorkbenchTaskSummary = {
  readonly taskId: string;
  readonly title: string;
  readonly routeId: WorkbenchRouteId;
  readonly status: "new" | "planned" | "in-progress" | "waiting" | "review" | "done";
};

export type TenantWorkbenchQueryKey =
  | "current-user"
  | "navigation"
  | "dashboard"
  | `section:${string}`
  | "tasks"
  | "snapshot";

export type TenantWorkbenchQueryState<T> = {
  readonly key: TenantWorkbenchQueryKey;
  readonly status: "fresh" | "stale" | "miss";
  readonly value: T | null;
  readonly updatedAt: string | null;
};

export type TenantWorkbenchQueryCache = {
  readonly read: <T>(key: TenantWorkbenchQueryKey) => TenantWorkbenchQueryState<T>;
  readonly write: <T>(key: TenantWorkbenchQueryKey, value: T) => TenantWorkbenchQueryState<T>;
  readonly clear: () => void;
};

export type TenantWorkbenchApiRequest = {
  readonly path: string;
  readonly method: "GET";
  readonly scope: TenantWorkbenchScope;
  readonly session: TenantWorkbenchAuthSession;
};

export type TenantWorkbenchApiTransport = {
  readonly requestJson: <T>(request: TenantWorkbenchApiRequest) => Promise<T>;
};

export type TenantWorkbenchOfflineSummaryStore = {
  readonly readSnapshot: (scope: TenantWorkbenchScope) => Promise<TenantWorkbenchSnapshot | null>;
  readonly writeSnapshot: (
    scope: TenantWorkbenchScope,
    snapshot: TenantWorkbenchSnapshot,
  ) => Promise<void>;
  readonly purge: (scope: TenantWorkbenchScope) => Promise<void>;
};

export class TenantScopeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TenantScopeError";
  }
}

export class TenantAuthError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TenantAuthError";
  }
}

export class TenantWriteIntentDeniedError extends Error {
  readonly reason = "write-intents-not-enabled";

  constructor() {
    super("Tenant workbench write intents are not enabled.");
    this.name = "TenantWriteIntentDeniedError";
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

export function createTenantWorkbenchMemoryCache(): TenantWorkbenchQueryCache {
  const entries = new Map<
    TenantWorkbenchQueryKey,
    { readonly value: unknown; readonly updatedAt: string }
  >();

  return {
    read<T>(key: TenantWorkbenchQueryKey): TenantWorkbenchQueryState<T> {
      const entry = entries.get(key);
      if (!entry) {
        return { key, status: "miss", value: null, updatedAt: null };
      }

      return {
        key,
        status: "fresh",
        value: entry.value as T,
        updatedAt: entry.updatedAt,
      };
    },
    write<T>(key: TenantWorkbenchQueryKey, value: T): TenantWorkbenchQueryState<T> {
      const updatedAt = new Date().toISOString();
      entries.set(key, { value, updatedAt });
      return { key, status: "fresh", value, updatedAt };
    },
    clear() {
      entries.clear();
    },
  };
}

export async function resolveTenantAuthSession(
  authAdapter: TenantWorkbenchAuthAdapter | undefined,
): Promise<TenantWorkbenchAuthSession> {
  if (!authAdapter) {
    return { state: "anonymous", claims: {} };
  }

  if (authAdapter.getSession) {
    return authAdapter.getSession();
  }

  const claims = await authAdapter.getClaims();
  return {
    state: claims.email ? "authenticated" : "anonymous",
    claims,
  };
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
    async getSession() {
      const claims = await this.getClaims();
      return {
        state: claims.email ? "authenticated" : "anonymous",
        claims,
      };
    },
  };
}

export function createStaticTenantAuthAdapter(
  claims: TenantWorkbenchAuthClaims,
): TenantWorkbenchAuthAdapter {
  return {
    async getClaims() {
      return claims;
    },
    async getSession() {
      return {
        state: claims.email ? "authenticated" : "anonymous",
        claims,
      };
    },
  };
}

export function createTenantWorkbenchClient({
  definition,
  authAdapter,
  apiTransport,
  queryCache = createTenantWorkbenchMemoryCache(),
  offlineSummaryStore,
}: {
  readonly definition: TenantWorkbenchDefinition;
  readonly authAdapter?: TenantWorkbenchAuthAdapter;
  readonly apiTransport?: TenantWorkbenchApiTransport;
  readonly queryCache?: TenantWorkbenchQueryCache;
  readonly offlineSummaryStore?: TenantWorkbenchOfflineSummaryStore;
}) {
  const expectedScope = definition.scope;
  assertTenantScopeMatches(expectedScope, expectedScope);

  async function getSession(): Promise<TenantWorkbenchAuthSession> {
    const session = await resolveTenantAuthSession(authAdapter);
    if (session.claims.tenantId || session.claims.areaId) {
      assertTenantScopeMatches(
        {
          tenantId: session.claims.tenantId,
          areaId: session.claims.areaId,
        },
        expectedScope,
      );
    }
    return session;
  }

  async function readQuery<T>(
    key: TenantWorkbenchQueryKey,
    loader: () => Promise<T>,
  ): Promise<T> {
    const cached = queryCache.read<T>(key);
    if (cached.status === "fresh" && cached.value !== null) {
      return cached.value;
    }

    const value = await loader();
    queryCache.write(key, value);
    return value;
  }

  async function requestFromApi<T>(path: string): Promise<T | null> {
    if (!apiTransport) return null;

    const session = await getSession();
    return apiTransport.requestJson<T>({
      path,
      method: "GET",
      scope: expectedScope,
      session,
    });
  }

  return {
    readonly: true,
    get scope() {
      return expectedScope;
    },
    get queryCache() {
      return queryCache;
    },
    getSession,
    async getCurrentUser(): Promise<TenantWorkbenchUser> {
      const session = await readQuery("current-user", getSession);
      const claims = session.claims;

      const email = claims.email ?? "";
      return {
        email,
        principalId: claims.principalId ?? email,
        roles: claims.roles ?? [],
        isAuthenticated: session.state === "authenticated" && Boolean(email),
        scope: expectedScope,
      };
    },
    async getNavigation() {
      return readQuery("navigation", async () => {
        const remote = await requestFromApi<readonly WorkbenchNavigationItem[]>("/navigation");
        return remote ?? definition.navigation;
      });
    },
    async getDashboard(): Promise<TenantWorkbenchDashboard> {
      return readQuery("dashboard", async () => {
        const remote = await requestFromApi<TenantWorkbenchDashboard>("/dashboard");
        return remote ?? getDashboardSnapshot(definition);
      });
    },
    getDashboardSnapshot(): TenantWorkbenchDashboard {
      return getDashboardSnapshot(definition);
    },
    async getSection(routeId: string) {
      return readQuery(`section:${routeId}`, async () => {
        const remote = await requestFromApi<WorkbenchSection | null>(
          `/sections/${encodeURIComponent(routeId)}`,
        );
        return remote ?? getSectionByRouteId(definition, routeId);
      });
    },
    getSectionSnapshot(routeId: string) {
      return getSectionByRouteId(definition, routeId);
    },
    async getSnapshot(): Promise<TenantWorkbenchSnapshot> {
      return readQuery("snapshot", async () => {
        const remote = await requestFromApi<TenantWorkbenchSnapshot>("/snapshot");
        if (remote) {
          assertTenantScopeMatches(remote.scope, expectedScope);
          return remote;
        }

        const offline = await offlineSummaryStore?.readSnapshot(expectedScope);
        if (offline) {
          assertTenantScopeMatches(offline.scope, expectedScope);
          return offline;
        }

        const snapshot = createDefinitionSnapshot(definition);
        await offlineSummaryStore?.writeSnapshot(expectedScope, snapshot);
        return snapshot;
      });
    },
    async listTasks(): Promise<readonly TenantWorkbenchTaskSummary[]> {
      return readQuery("tasks", async () => {
        const remote = await requestFromApi<readonly TenantWorkbenchTaskSummary[]>("/tasks");
        return remote ?? [];
      });
    },
    async mutateTask(): Promise<{ readonly ok: false; readonly reason: string }> {
      return {
        ok: false,
        reason: "write-intents-not-enabled",
      };
    },
    async submitWriteIntent(): Promise<never> {
      throw new TenantWriteIntentDeniedError();
    },
    async purgeOfflineSummary(): Promise<void> {
      queryCache.clear();
      await offlineSummaryStore?.purge(expectedScope);
    },
  };
}

export function createKhhWorkbenchClient(
  authAdapter?: TenantWorkbenchAuthAdapter,
  offlineSummaryStore?: TenantWorkbenchOfflineSummaryStore,
) {
  return createTenantWorkbenchClient({
    definition: khhTenantWorkbenchDefinition,
    authAdapter,
    offlineSummaryStore,
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

function createDefinitionSnapshot(
  definition: TenantWorkbenchDefinition,
): TenantWorkbenchSnapshot {
  return {
    scope: definition.scope,
    navigation: definition.navigation,
    dashboard: getDashboardSnapshot(definition),
    sections: Object.values(definition.sections),
    cachedAt: new Date().toISOString(),
  };
}
