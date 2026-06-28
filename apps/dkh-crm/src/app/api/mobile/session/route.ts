import { NextResponse, type NextRequest } from "next/server";
import { verifyAppleIdentityToken } from "@/lib/apple-auth";
import { createMobileSessionToken, resolveMobileIdentity } from "@/lib/mobile-session";

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ status: "invalid_request", user: null }, { status: 400 });
  }

  const identityToken =
    typeof body === "object" &&
    body !== null &&
    "identity_token" in body &&
    typeof body.identity_token === "string"
      ? body.identity_token
      : "";
  if (!identityToken) {
    return NextResponse.json({ status: "missing_identity_token", user: null }, { status: 400 });
  }

  try {
    const appleIdentity = await verifyAppleIdentityToken(identityToken);
    const resolution = await resolveMobileIdentity({
      appleSubject: appleIdentity.subject,
      appleEmail: appleIdentity.email,
      emailVerified: appleIdentity.emailVerified,
    });

    if (!resolution.authorized || !resolution.user) {
      return NextResponse.json(
        { status: resolution.status, user: null, sessionToken: null },
        { status: 403 },
      );
    }

    const sessionToken = await createMobileSessionToken(resolution.user);
    return NextResponse.json({
      status: "active",
      user: resolution.user,
      sessionToken,
    });
  } catch {
    return NextResponse.json({ status: "invalid_identity", user: null }, { status: 401 });
  }
}
