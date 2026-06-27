import { headers } from "next/headers";

export async function getUserEmail(): Promise<string> {
  const headerStore = await headers();
  return (
    headerStore.get("x-khh-user-email") ??
    headerStore.get("cf-access-authenticated-user-email") ??
    ""
  );
}
