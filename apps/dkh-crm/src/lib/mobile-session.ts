import { SignJWT } from "jose";

export type MobileCRMUser = {
  id: number;
  displayName: string;
  email: string;
  roles: string[];
};

export type MobileIdentityResolution = {
  authorized: boolean;
  status: "pending" | "requested" | "active" | "revoked";
  user: MobileCRMUser | null;
};

function adminApiBase(): string {
  const base = process.env.DKH_ADMIN_API_BASE_URL;
  if (!base) throw new Error("DKH_ADMIN_API_BASE_URL is required");
  return base.replace(/\/+$/, "");
}

function adminApiHeaders(): Headers {
  const headers = new Headers({ "content-type": "application/json" });
  const token = process.env.DKH_ADMIN_API_TOKEN;
  if (token) headers.set("authorization", `Bearer ${token}`);
  return headers;
}

export async function resolveMobileIdentity(input: {
  appleSubject: string;
  appleEmail: string;
  emailVerified: boolean;
}): Promise<MobileIdentityResolution> {
  const response = await fetch(`${adminApiBase()}/mobile/apple-session`, {
    method: "POST",
    headers: adminApiHeaders(),
    body: JSON.stringify({
      apple_subject: input.appleSubject,
      apple_email: input.appleEmail,
      email_verified: input.emailVerified,
    }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Admin API mobile identity lookup failed: ${response.status}`);
  }
  return (await response.json()) as MobileIdentityResolution;
}

export async function createMobileSessionToken(user: MobileCRMUser): Promise<string> {
  const secret = process.env.DKH_MOBILE_SESSION_SECRET;
  if (!secret) {
    throw new Error("DKH_MOBILE_SESSION_SECRET is required");
  }

  return await new SignJWT({
    email: user.email,
    roles: user.roles,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(String(user.id))
    .setAudience("daskuechenhaus-ios")
    .setIssuer("daskuechenhaus-crm")
    .setIssuedAt()
    .setExpirationTime("12h")
    .sign(new TextEncoder().encode(secret));
}
