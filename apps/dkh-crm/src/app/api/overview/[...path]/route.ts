import { type NextRequest } from "next/server";
import { proxyRoute } from "@/lib/proxy";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRoute(request, "overview", path);
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxyRoute(request, "overview", path);
}
