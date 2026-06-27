import type { TenantWorkbenchScope } from "@scas/tenant-workbench-domain";
import {
  assertTenantScopeMatches,
  type TenantWorkbenchAuthClaims,
  type TenantWorkbenchAuthSession,
  type TenantWorkbenchOfflineSummaryStore,
  type TenantWorkbenchSnapshot,
} from "./index";

export type TenantScopedStorageAdapter = {
  readonly getItem: (tenantScopedKey: string) => Promise<string | null>;
  readonly setItem: (tenantScopedKey: string, value: string) => Promise<void>;
  readonly deleteItem: (tenantScopedKey: string) => Promise<void>;
  readonly purgeScope: (scope: TenantWorkbenchScope) => Promise<void>;
};

export type TenantOfflineCachePolicy = {
  readonly mode: "read-only-summaries";
  readonly maxAgeSeconds: number;
  readonly purgeOnLogout: true;
  readonly allowQueuedWrites: false;
};

export type TenantPushPolicy = {
  readonly optInRequired: true;
  readonly tenantScopedTopics: readonly string[];
  readonly sensitivePayloadsAllowed: false;
};

export type TenantPermissionPolicy = {
  readonly permissionId: "notifications" | "biometrics" | "documents";
  readonly defaultState: "denied";
  readonly roleGateRequired: true;
};

export type NativeTenantWorkbenchRuntimeContract = {
  readonly scope: TenantWorkbenchScope;
  readonly storage: TenantScopedStorageAdapter;
  readonly offlineCache: TenantOfflineCachePolicy;
  readonly push: TenantPushPolicy;
  readonly permissions: readonly TenantPermissionPolicy[];
};

export type NativeAuthHandoffAdapter = {
  readonly completeAuthHandoff: (
    claims: TenantWorkbenchAuthClaims,
  ) => Promise<TenantWorkbenchAuthSession>;
  readonly clearAuthSession: () => Promise<void>;
};

export type NativeSecureStorageBackend = {
  readonly getItem: (key: string) => Promise<string | null>;
  readonly setItem: (key: string, value: string) => Promise<void>;
  readonly deleteItem: (key: string) => Promise<void>;
};

export type NativePushOptInAdapter = {
  readonly getOptInState: () => Promise<"denied" | "prompt" | "granted">;
  readonly requestOptIn: () => Promise<"denied" | "granted">;
};

export type NativePermissionGateAdapter = {
  readonly getPermissionState: (
    permissionId: TenantPermissionPolicy["permissionId"],
  ) => Promise<"denied" | "granted">;
};

export function createTenantScopedStorageKey(
  scope: TenantWorkbenchScope,
  key: string,
): string {
  if (!key || key.includes(":")) {
    throw new Error("Tenant scoped storage keys must be non-empty local names.");
  }
  return `${scope.tenantId}:${scope.areaId}:${key}`;
}

export function createTenantScopedSecureStorageAdapter({
  scope,
  backend,
}: {
  readonly scope: TenantWorkbenchScope;
  readonly backend: NativeSecureStorageBackend;
}): TenantScopedStorageAdapter {
  const knownKeys = new Set<string>();

  return {
    async getItem(tenantScopedKey: string) {
      assertTenantScopedKey(scope, tenantScopedKey);
      return backend.getItem(tenantScopedKey);
    },
    async setItem(tenantScopedKey: string, value: string) {
      assertTenantScopedKey(scope, tenantScopedKey);
      knownKeys.add(tenantScopedKey);
      await backend.setItem(tenantScopedKey, value);
    },
    async deleteItem(tenantScopedKey: string) {
      assertTenantScopedKey(scope, tenantScopedKey);
      knownKeys.delete(tenantScopedKey);
      await backend.deleteItem(tenantScopedKey);
    },
    async purgeScope(purgeScope: TenantWorkbenchScope) {
      assertTenantScopeMatches(purgeScope, scope);
      await Promise.all(
        Array.from(knownKeys).map(async (key) => {
          knownKeys.delete(key);
          await backend.deleteItem(key);
        }),
      );
    },
  };
}

export function createNativeAuthHandoffAdapter({
  scope,
  storage,
}: {
  readonly scope: TenantWorkbenchScope;
  readonly storage: TenantScopedStorageAdapter;
}): NativeAuthHandoffAdapter {
  const sessionKey = createTenantScopedStorageKey(scope, "auth-session");

  return {
    async completeAuthHandoff(claims: TenantWorkbenchAuthClaims) {
      assertTenantScopeMatches(
        { tenantId: claims.tenantId, areaId: claims.areaId },
        scope,
      );
      const session: TenantWorkbenchAuthSession = {
        state: claims.email ? "authenticated" : "anonymous",
        claims,
      };
      await storage.setItem(sessionKey, JSON.stringify(session));
      return session;
    },
    async clearAuthSession() {
      await storage.deleteItem(sessionKey);
    },
  };
}

export function createOfflineSummaryStore({
  scope,
  storage,
}: {
  readonly scope: TenantWorkbenchScope;
  readonly storage: TenantScopedStorageAdapter;
}): TenantWorkbenchOfflineSummaryStore {
  const snapshotKey = createTenantScopedStorageKey(scope, "offline-summary");

  return {
    async readSnapshot(readScope: TenantWorkbenchScope) {
      assertTenantScopeMatches(readScope, scope);
      const raw = await storage.getItem(snapshotKey);
      return raw ? (JSON.parse(raw) as TenantWorkbenchSnapshot) : null;
    },
    async writeSnapshot(writeScope: TenantWorkbenchScope, snapshot: TenantWorkbenchSnapshot) {
      assertTenantScopeMatches(writeScope, scope);
      assertTenantScopeMatches(snapshot.scope, scope);
      await storage.setItem(snapshotKey, JSON.stringify(snapshot));
    },
    async purge(purgeScope: TenantWorkbenchScope) {
      assertTenantScopeMatches(purgeScope, scope);
      await storage.deleteItem(snapshotKey);
    },
  };
}

export function createDefaultDeniedPushOptInAdapter(): NativePushOptInAdapter {
  return {
    async getOptInState() {
      return "denied";
    },
    async requestOptIn() {
      return "denied";
    },
  };
}

export function createDefaultDeniedPermissionGateAdapter(
  policies: readonly TenantPermissionPolicy[] = defaultNativePermissionPolicies,
): NativePermissionGateAdapter {
  return {
    async getPermissionState(permissionId) {
      const policy = policies.find((candidate) => candidate.permissionId === permissionId);
      return policy?.defaultState ?? "denied";
    },
  };
}

export function createNativeTenantWorkbenchRuntimeContract({
  scope,
  storage,
}: {
  readonly scope: TenantWorkbenchScope;
  readonly storage: TenantScopedStorageAdapter;
}): NativeTenantWorkbenchRuntimeContract {
  return {
    scope,
    storage,
    offlineCache: readOnlySummaryOfflinePolicy,
    push: khhNativePushPolicy,
    permissions: defaultNativePermissionPolicies,
  };
}

export const readOnlySummaryOfflinePolicy: TenantOfflineCachePolicy = {
  mode: "read-only-summaries",
  maxAgeSeconds: 900,
  purgeOnLogout: true,
  allowQueuedWrites: false,
};

export const khhNativePushPolicy: TenantPushPolicy = {
  optInRequired: true,
  tenantScopedTopics: ["tenant_kinderhaus:leadership-summary"],
  sensitivePayloadsAllowed: false,
};

export const defaultNativePermissionPolicies: readonly TenantPermissionPolicy[] = [
  {
    permissionId: "notifications",
    defaultState: "denied",
    roleGateRequired: true,
  },
  {
    permissionId: "biometrics",
    defaultState: "denied",
    roleGateRequired: true,
  },
  {
    permissionId: "documents",
    defaultState: "denied",
    roleGateRequired: true,
  },
];

function assertTenantScopedKey(scope: TenantWorkbenchScope, key: string): void {
  const prefix = `${scope.tenantId}:${scope.areaId}:`;
  if (!key.startsWith(prefix)) {
    throw new Error("Tenant scoped storage key does not match runtime scope.");
  }
}
