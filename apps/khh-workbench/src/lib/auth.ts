import { headers } from "next/headers";
import {
  createCloudflareAccessHeaderAuthAdapter,
  createKhhWorkbenchClient,
} from "@scas/tenant-workbench-client";
import { khhTenantWorkbenchDefinition } from "@scas/tenant-workbench-domain/khh";

export async function getUserEmail(): Promise<string> {
  const headerStore = await headers();
  const authAdapter = createCloudflareAccessHeaderAuthAdapter({
    scope: khhTenantWorkbenchDefinition.scope,
    getHeader: (name) => headerStore.get(name),
  });
  const client = createKhhWorkbenchClient(authAdapter);
  const user = await client.getCurrentUser();

  return user.email;
}
