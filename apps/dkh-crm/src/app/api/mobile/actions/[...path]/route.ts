import { NextResponse, type NextRequest } from "next/server";
import { fetchDkhJson } from "@/lib/dkh-api";
import { verifyMobileSessionToken } from "@/lib/mobile-session";

type RouteContext = {
  params: Promise<{ path?: string[] }>;
};

const ACTION_ALLOWLIST: RegExp[] = [
  /^overview\/tasks$/,
  /^overview\/tasks\/\d+$/,
  /^overview\/tasks\/\d+\/archive$/,
  /^overview\/tasks\/\d+\/delete$/,
  /^overview\/emails\/assign$/,
  /^overview\/emails\/suggestions\/\d+\/accept$/,
  /^overview\/emails\/\d+\/archive$/,
  /^overview\/emails\/\d+\/delete$/,
  /^customers\/customers$/,
  /^customers\/customers\/\d+$/,
  /^customers\/cases$/,
  /^customers\/cases\/\d+$/,
  /^customers\/cases\/\d+\/notes$/,
  /^customers\/cases\/\d+\/sections\/[a-z0-9_/-]+$/,
];

function mobileToken(request: NextRequest): string {
  const header = request.headers.get("authorization") ?? "";
  const match = /^Bearer\s+(.+)$/i.exec(header);
  return match?.[1]?.trim() ?? "";
}

function allowedActionPath(path: string): boolean {
  return ACTION_ALLOWLIST.some((pattern) => pattern.test(path));
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path = [] } = await context.params;
  const actionPath = path.join("/");
  if (!actionPath || !allowedActionPath(actionPath)) {
    return NextResponse.json({ status: "not_found" }, { status: 404 });
  }

  const token = mobileToken(request);
  if (!token) {
    return NextResponse.json({ status: "missing_mobile_session" }, { status: 401 });
  }

  const session = await verifyMobileSessionToken(token).catch(() => null);
  if (!session) {
    return NextResponse.json({ status: "invalid_mobile_session" }, { status: 401 });
  }

  try {
    const contentType = request.headers.get("content-type") ?? "application/x-www-form-urlencoded";
    const body = await request.text();
    const result = await fetchDkhJson<Record<string, unknown>>(actionPath, session.email, {
      method: "POST",
      headers: {
        "content-type": contentType,
      },
      body,
    });

    return NextResponse.json({
      status: "active",
      action: actionPath,
      result,
    });
  } catch (error) {
    console.error(`Mobile CRM action failed: ${actionPath}`, error);
    return NextResponse.json({ status: "mobile_action_unavailable" }, { status: 502 });
  }
}
