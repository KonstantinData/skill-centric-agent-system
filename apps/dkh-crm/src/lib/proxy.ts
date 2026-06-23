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
    /^cases$/,
    /^customers$/,
    /^customers\/\d+$/,
    /^customers\/\d+\/sections\/[a-z0-9_-]+$/i,
    /^cases\/\d+$/,
    /^cases\/\d+\/documents$/,
    /^cases\/\d+\/documents\/\d+\/archive$/,
    /^cases\/\d+\/carat-imports\/\d+\/positions$/,
    /^cases\/\d+\/confirmations$/,
    /^confirmations\/\d+\/exceptions\/\d+\/decide$/,
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
  const email = request.headers.get("x-dkh-user-email") ?? "";
  if (email) {
    headers.set("x-access-user-email", email);
    headers.set("cf-access-authenticated-user-email", email);
  }
  return headers;
}

function isLocalRedirectHost(host: string): boolean {
  const normalized = host.toLowerCase().split(":")[0];
  return (
    normalized === "localhost" ||
    normalized === "127.0.0.1" ||
    normalized === "::1" ||
    normalized.endsWith(".local")
  );
}

function publicRedirectOrigin(request: NextRequest): string {
  const forwardedHost = request.headers.get("x-forwarded-host") ?? "";
  const host = forwardedHost || request.headers.get("host") || "";
  const forwardedProto = request.headers.get("x-forwarded-proto") ?? "";
  const proto = forwardedProto === "http" || forwardedProto === "https" ? forwardedProto : "https";

  if (host && !isLocalRedirectHost(host)) {
    return `${proto}://${host}`;
  }

  const configured = process.env.DKH_CRM_PUBLIC_BASE_URL?.replace(/\/+$/, "");
  return configured || "https://www.es-daskuechenhaus.de";
}

async function bodyAndHeadersFor(request: NextRequest, headers: Headers) {
  if (request.method === "GET" || request.method === "HEAD") return undefined;
  const contentType = request.headers.get("content-type") ?? "";
  if (contentType.includes("multipart/form-data")) {
    headers.set("content-type", contentType);
    return await request.arrayBuffer();
  }
  headers.set("content-type", "application/x-www-form-urlencoded");
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
  const body = await bodyAndHeadersFor(request, headers);

  const response = await fetch(built.upstream, {
    method,
    headers,
    body,
    redirect: "manual",
    cache: "no-store",
  });

  if (!["GET", "HEAD"].includes(method)) {
    const acceptsJson = request.headers.get("accept")?.includes("application/json");
    if (acceptsJson || !response.ok) {
      const contentType = response.headers.get("content-type") ?? "application/json";
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          "content-type": contentType,
          "cache-control": "no-store",
        },
      });
    }
    const returnTo = safeReturnTo(
      request.nextUrl.searchParams.get("return_to"),
      request.headers.get("referer") ? new URL(request.headers.get("referer")!).pathname : "/",
    );
    return NextResponse.redirect(new URL(returnTo, publicRedirectOrigin(request)), 303);
  }

  const contentType = response.headers.get("content-type") ?? "application/json";
  const responseHeaders: Record<string, string> = {
    "content-type": contentType,
    "cache-control": "no-store",
  };
  const contentDisposition = response.headers.get("content-disposition");
  if (contentDisposition) {
    responseHeaders["content-disposition"] = contentDisposition;
  }
  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}
