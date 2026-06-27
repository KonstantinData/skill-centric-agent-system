import type { TenantWorkbenchScope } from "@scas/tenant-workbench-domain";

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

export function createTenantScopedStorageKey(
  scope: TenantWorkbenchScope,
  key: string,
): string {
  if (!key || key.includes(":")) {
    throw new Error("Tenant scoped storage keys must be non-empty local names.");
  }
  return `${scope.tenantId}:${scope.areaId}:${key}`;
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
