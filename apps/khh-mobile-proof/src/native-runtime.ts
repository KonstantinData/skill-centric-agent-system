import { khhTenantWorkbenchDefinition } from "@scas/tenant-workbench-domain/khh";
import {
  createDefaultDeniedPermissionGateAdapter,
  createDefaultDeniedPushOptInAdapter,
  createNativeAuthHandoffAdapter,
  createNativeTenantWorkbenchRuntimeContract,
  createOfflineSummaryStore,
  createTenantScopedSecureStorageAdapter,
  type NativeSecureStorageBackend,
} from "@scas/tenant-workbench-client/native-contracts";

class ProofSecureStorageBackend implements NativeSecureStorageBackend {
  private readonly values = new Map<string, string>();

  async getItem(key: string): Promise<string | null> {
    return this.values.get(key) ?? null;
  }

  async setItem(key: string, value: string): Promise<void> {
    this.values.set(key, value);
  }

  async deleteItem(key: string): Promise<void> {
    this.values.delete(key);
  }
}

const scope = khhTenantWorkbenchDefinition.scope;
const storage = createTenantScopedSecureStorageAdapter({
  scope,
  backend: new ProofSecureStorageBackend(),
});

export const khhNativeRuntime = createNativeTenantWorkbenchRuntimeContract({
  scope,
  storage,
});

export const khhNativeAuthHandoff = createNativeAuthHandoffAdapter({
  scope,
  storage,
});

export const khhOfflineSummaryStore = createOfflineSummaryStore({
  scope,
  storage,
});

export const khhPushOptIn = createDefaultDeniedPushOptInAdapter();

export const khhPermissionGate = createDefaultDeniedPermissionGateAdapter();
