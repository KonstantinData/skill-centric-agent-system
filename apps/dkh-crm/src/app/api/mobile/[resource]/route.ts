import { NextResponse, type NextRequest } from "next/server";
import { fetchDkhJson } from "@/lib/dkh-api";
import { verifyMobileSessionToken } from "@/lib/mobile-session";
import type { AdminState, CustomersState, OverviewState } from "@/lib/types";

type RouteContext = {
  params: Promise<{ resource: string }>;
};

type MobileResource = "overview" | "customers" | "admin";

const RESOURCE_PATHS: Record<MobileResource, string> = {
  overview: "overview/state",
  customers: "customers/state",
  admin: "admin/state",
};

function mobileToken(request: NextRequest): string {
  const header = request.headers.get("authorization") ?? "";
  const match = /^Bearer\s+(.+)$/i.exec(header);
  return match?.[1]?.trim() ?? "";
}

function isMobileResource(resource: string): resource is MobileResource {
  return resource === "overview" || resource === "customers" || resource === "admin";
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { resource } = await context.params;
  if (!isMobileResource(resource)) {
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

  if (resource === "admin" && !session.roles.includes("admin")) {
    return NextResponse.json({ status: "forbidden" }, { status: 403 });
  }

  try {
    const path = RESOURCE_PATHS[resource];
    const state = await fetchDkhJson<OverviewState | CustomersState | AdminState>(
      path,
      session.email,
    );

    return NextResponse.json({
      status: "active",
      resource,
      user: {
        id: session.userId,
        email: session.email,
        roles: session.roles,
      },
      state,
    });
  } catch (error) {
    console.error(`Mobile CRM resource failed: ${resource}`, error);
    return NextResponse.json({ status: "mobile_resource_unavailable" }, { status: 502 });
  }
}
