import { NextResponse, type NextRequest } from "next/server";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";
  if (query.length < 3) {
    return NextResponse.json({ customers: [] });
  }

  const base = process.env.DKH_ADMIN_API_BASE_URL;
  if (!base) {
    return NextResponse.json(
      { error: "DKH_ADMIN_API_BASE_URL is required" },
      { status: 500 },
    );
  }

  const upstream = new URL(`${base.replace(/\/+$/, "")}/customers/search`);
  upstream.searchParams.set("q", query);

  const headers = new Headers({ accept: "application/json" });
  const token = process.env.DKH_ADMIN_API_TOKEN;
  if (token) headers.set("authorization", `Bearer ${token}`);
  const email = request.headers.get("x-dkh-user-email") ?? "";
  if (email) {
    headers.set("x-access-user-email", email);
    headers.set("cf-access-authenticated-user-email", email);
  }

  const response = await fetch(upstream, {
    headers,
    cache: "no-store",
  });

  return new NextResponse(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
    },
  });
}
