import { NextResponse, type NextRequest } from "next/server";
import { fetchDkhBinary } from "@/lib/dkh-api";
import { verifyMobileSessionToken } from "@/lib/mobile-session";

type RouteContext = {
  params: Promise<{ caseId: string; documentId: string }>;
};

function mobileToken(request: NextRequest): string {
  const header = request.headers.get("authorization") ?? "";
  const match = /^Bearer\s+(.+)$/i.exec(header);
  return match?.[1]?.trim() ?? "";
}

function inlineContentDisposition(contentDisposition: string | null): string {
  if (!contentDisposition) return "inline";
  if (/^attachment\b/i.test(contentDisposition)) {
    return contentDisposition.replace(/^attachment\b/i, "inline");
  }
  if (/^inline\b/i.test(contentDisposition)) return contentDisposition;
  return `inline; ${contentDisposition}`;
}

function numericId(value: string): string | null {
  return /^\d+$/.test(value) ? value : null;
}

export async function GET(request: NextRequest, context: RouteContext) {
  const token = mobileToken(request);
  if (!token) {
    return NextResponse.json({ status: "missing_mobile_session" }, { status: 401 });
  }

  const session = await verifyMobileSessionToken(token).catch(() => null);
  if (!session) {
    return NextResponse.json({ status: "invalid_mobile_session" }, { status: 401 });
  }

  const { caseId, documentId } = await context.params;
  const safeCaseId = numericId(caseId);
  const safeDocumentId = numericId(documentId);
  if (!safeCaseId || !safeDocumentId) {
    return NextResponse.json({ status: "not_found" }, { status: 404 });
  }

  try {
    const upstream = await fetchDkhBinary(
      `customers/cases/${safeCaseId}/documents/${safeDocumentId}/download`,
      session.email,
    );

    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: {
        "cache-control": "no-store",
        "content-type": upstream.headers.get("content-type") ?? "application/octet-stream",
        "content-disposition": inlineContentDisposition(
          upstream.headers.get("content-disposition"),
        ),
      },
    });
  } catch (error) {
    console.error(`Mobile CRM document preview failed: ${caseId}/${documentId}`, error);
    return NextResponse.json({ status: "mobile_document_unavailable" }, { status: 502 });
  }
}
