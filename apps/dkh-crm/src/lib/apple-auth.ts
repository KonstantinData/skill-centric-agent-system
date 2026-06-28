import { createRemoteJWKSet, jwtVerify } from "jose";

const APPLE_ISSUER = "https://appleid.apple.com";
const APPLE_KEYS_URL = new URL("https://appleid.apple.com/auth/keys");

let appleJwks: ReturnType<typeof createRemoteJWKSet> | null = null;

export type AppleIdentity = {
  subject: string;
  email: string;
  emailVerified: boolean;
};

export async function verifyAppleIdentityToken(identityToken: string): Promise<AppleIdentity> {
  const bundleId = process.env.DKH_IOS_APP_BUNDLE_ID;
  if (!bundleId) {
    throw new Error("DKH_IOS_APP_BUNDLE_ID is required");
  }

  appleJwks ??= createRemoteJWKSet(APPLE_KEYS_URL);
  const { payload } = await jwtVerify(identityToken, appleJwks, {
    issuer: APPLE_ISSUER,
    audience: bundleId,
  });

  if (typeof payload.sub !== "string" || payload.sub.trim() === "") {
    throw new Error("Apple identity token is missing subject");
  }

  const email = typeof payload.email === "string" ? payload.email.toLowerCase() : "";
  const emailVerified =
    payload.email_verified === true || payload.email_verified === "true";

  return {
    subject: payload.sub,
    email,
    emailVerified,
  };
}
