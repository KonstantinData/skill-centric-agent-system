import { unstable_noStore as noStore } from "next/cache";
import {
  EMPTY_ADMIN_STATE,
  EMPTY_CUSTOMERS_STATE,
  EMPTY_OVERVIEW_STATE,
  type AdminState,
  type CustomersState,
  type OverviewState,
} from "./types";

function withFallback<T>(value: T | null | undefined, fallback: T): T {
  return value ?? fallback;
}

function adminApiUrl(path: string): string {
  const base = process.env.DKH_ADMIN_API_BASE_URL;
  if (!base) {
    throw new Error("DKH_ADMIN_API_BASE_URL is required");
  }
  return `${base.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

function dkhRequestHeaders(userEmail: string, init: RequestInit = {}): Headers {
  const token = process.env.DKH_ADMIN_API_TOKEN;
  const headers = new Headers(init.headers);
  if (token) headers.set("authorization", `Bearer ${token}`);
  if (userEmail) {
    headers.set("x-access-user-email", userEmail);
    headers.set("cf-access-authenticated-user-email", userEmail);
  }
  return headers;
}

export async function fetchDkhJson<T>(
  path: string,
  userEmail: string,
  init: RequestInit = {},
): Promise<T> {
  noStore();
  const headers = dkhRequestHeaders(userEmail, init);
  headers.set("accept", "application/json");

  const response = await fetch(adminApiUrl(path), {
    ...init,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(2500),
  });

  if (!response.ok) {
    throw new Error(`DKH API ${path} failed with ${response.status}`);
  }

  return (await response.json()) as T;
}

export async function fetchDkhBinary(
  path: string,
  userEmail: string,
  init: RequestInit = {},
): Promise<Response> {
  noStore();
  const headers = dkhRequestHeaders(userEmail, init);

  const response = await fetch(adminApiUrl(path), {
    ...init,
    headers,
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });

  if (!response.ok) {
    throw new Error(`DKH API ${path} failed with ${response.status}`);
  }

  return response;
}

export async function fetchOverviewState(userEmail: string) {
  try {
    return withFallback(
      await fetchDkhJson<OverviewState | null>("overview/state", userEmail),
      EMPTY_OVERVIEW_STATE,
    );
  } catch {
    return EMPTY_OVERVIEW_STATE;
  }
}

export async function fetchAdminState(userEmail: string) {
  try {
    return withFallback(
      await fetchDkhJson<AdminState | null>("admin/state", userEmail),
      EMPTY_ADMIN_STATE,
    );
  } catch {
    return EMPTY_ADMIN_STATE;
  }
}

export async function fetchCustomersState(userEmail: string) {
  try {
    return withFallback(
      await fetchDkhJson<CustomersState | null>("customers/state", userEmail),
      EMPTY_CUSTOMERS_STATE,
    );
  } catch {
    return EMPTY_CUSTOMERS_STATE;
  }
}
