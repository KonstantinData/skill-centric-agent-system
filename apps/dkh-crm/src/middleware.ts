import { jwtVerify, createRemoteJWKSet } from "jose";
import { NextResponse, type NextRequest } from "next/server";

const STRIP_HEADERS = [
  "authorization",
  "cf-access-authenticated-user-email",
  "cf-access-client-id",
  "cf-access-client-secret",
  "cf-access-jwt-assertion",
  "cf-access-user-email",
  "x-access-user-email",
  "x-dkh-user-email",
];

let jwks: ReturnType<typeof createRemoteJWKSet> | null = null;

async function accessEmailFromJwt(request: NextRequest): Promise<string> {
  const token = request.headers.get("cf-access-jwt-assertion");
  const teamDomain = process.env.CF_ACCESS_TEAM_DOMAIN;
  const audience = process.env.CF_ACCESS_AUD;
  if (!token || !teamDomain || !audience) return "";

  jwks ??= createRemoteJWKSet(
    new URL(`https://${teamDomain}/cdn-cgi/access/certs`),
  );
  const { payload } = await jwtVerify(token, jwks, { audience });
  return typeof payload.email === "string" ? payload.email : "";
}

async function resolveAccessEmail(request: NextRequest): Promise<string> {
  const verified = await accessEmailFromJwt(request).catch(() => "");
  if (verified) return verified;
  return (
    request.headers.get("cf-access-authenticated-user-email") ??
    request.headers.get("cf-access-user-email") ??
    ""
  );
}

export async function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);
  for (const header of STRIP_HEADERS) {
    requestHeaders.delete(header);
  }

  const email = await resolveAccessEmail(request);
  if (email) {
    requestHeaders.set("x-dkh-user-email", email);
  }

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|crm-hero.jpg|logo.svg).*)"],
};
