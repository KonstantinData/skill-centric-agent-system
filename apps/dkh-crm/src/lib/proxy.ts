import { NextResponse, type NextRequest } from "next/server";
import { safeDecodeSegment, safeReturnTo } from "./utils";

type ProxyKind = "overview" | "admin" | "customers";

const ALLOWED_WRITE_PATHS: Record<ProxyKind, RegExp[]> = {
  overview: [
    /^tasks$/,
    /^tasks\/\d+$/,
    /^tasks\/\d+\/archive$/,
    /^tasks\/\d+\/delete$/,
    /^emails\/assign$/,
    /^emails\/suggestions\/\d+\/accept$/,
    /^emails\/\d+\/archive$/,
    /^emails\/\d+\/delete$/,
  ],
  admin: [
    /^users$/,
    /^users\/\d+$/,
    /^users\/\d+\/delete$/,
    /^users\/\d+\/roles$/,
    /^users\/\d+\/workdays$/,
    /^company-settings$/,
    /^integrations$/,
  ],
  customers: [
    /^customers$/,
    /^customers\/\d+$/,
    /^customers\/\d+\/sections\/[a-z0-9_-]+$/i,
    /^cases\/\d+\/notes$/,
    /^cases\/\d+\/sections\/[a-z0-9_-]+$/i,
  ],
};

function upstreamBase() {
  const base = process.env.DKH_ADMIN_API_BASE_URL;
  if (!base) throw new Error("DKH_ADMIN_API_BASE_URL is required");
  return base.replace(/\/+$/, "");
}

function buildUpstreamUrl(kind: ProxyKind, segments: string[], request: NextRequest) {
  const decoded = segments.map(safeDecodeSegment);
  if (decoded.some((segment) => !segment)) return null;

  const path = decoded.join("/");
  const upstream = new URL(`${upstreamBase()}/${kind}/${path}`);
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    if (key !== "return_to") upstream.searchParams.append(key, value);
  }
  return { path, upstream };
}

function proxyHeaders(request: NextRequest) {
  const headers = new Headers();
  const token = process.env.DKH_ADMIN_API_TOKEN;
  if (token) headers.set("authorization", `Bearer ${token}`);
  const email =
    request.headers.get("x-dkh-user-email") ??
    request.headers.get("cf-access-authenticated-user-email") ??
    "";
  if (email) {
    headers.set("x-access-user-email", email);
    headers.set("cf-access-authenticated-user-email", email);
  }
  return headers;
}

async function bodyFor(request: NextRequest) {
  if (request.method === "GET" || request.method === "HEAD") return undefined;
  const formData = await request.formData();
  return new URLSearchParams(
    Array.from(formData.entries()).map(([key, value]) => [
      key,
      typeof value === "string" ? value : value.name,
    ]),
  );
}

export async function proxyRoute(
  request: NextRequest,
  kind: ProxyKind,
  segments: string[],
) {
  const built = buildUpstreamUrl(kind, segments, request);
  if (!built) {
    return NextResponse.json({ error: "Malformed API path" }, { status: 400 });
  }

  const method = request.method.toUpperCase();
  const allowedForWrite = ALLOWED_WRITE_PATHS[kind].some((regex) =>
    regex.test(built.path),
  );
  if (!["GET", "HEAD"].includes(method) && !allowedForWrite) {
    return NextResponse.json({ error: "Disallowed API path" }, { status: 403 });
  }

  const headers = proxyHeaders(request);
  if (!["GET", "HEAD"].includes(method)) {
    headers.set("content-type", "application/x-www-form-urlencoded");
  }

  const response = await fetch(built.upstream, {
    method,
    headers,
    body: await bodyFor(request),
    redirect: "manual",
    cache: "no-store",
  });

  if (!["GET", "HEAD"].includes(method)) {
    const returnTo = safeReturnTo(
      request.nextUrl.searchParams.get("return_to"),
      request.headers.get("referer") ? new URL(request.headers.get("referer")!).pathname : "/",
    );
    return NextResponse.redirect(new URL(returnTo, request.url), 303);
  }

  const contentType = response.headers.get("content-type") ?? "application/json";
  return new NextResponse(response.body, {
    status: response.status,
    headers: {
      "content-type": contentType,
      "cache-control": "no-store",
    },
  });
}
