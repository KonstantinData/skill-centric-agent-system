const CONTRACT_VERSION = "0.1.0";
const REGISTRY_VERSION = "0.1.0";
const MAX_JSON_BODY_BYTES = 64 * 1024;

type JsonObject = Record<string, unknown>;

type ErrorResponse = {
  error: {
    code: string;
    message: string;
  };
};

type CompositionContextResponse = {
  contract_version: string;
  registry_version: string;
  composition_status: "pending_registry_implementation";
  candidate_modules: [];
  applicable_policies: [];
  allowed_knowledge_scopes: [];
  allowed_data_scopes: [];
  allowed_memory_scopes: [];
  validation_requirements: [];
};

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json; charset=utf-8");

  return new Response(JSON.stringify(body), {
    ...init,
    headers,
  });
}

function errorResponse(status: number, code: string, message: string): Response {
  return jsonResponse(
    {
      error: {
        code,
        message,
      },
    } satisfies ErrorResponse,
    { status },
  );
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isId(value: unknown): value is string {
  return typeof value === "string" && /^[a-z][a-z0-9-]*$/.test(value);
}

function isSemver(value: unknown): value is string {
  return typeof value === "string" && /^[0-9]+\.[0-9]+\.[0-9]+$/.test(value);
}

function hasProperty(value: JsonObject, property: string): boolean {
  return Object.prototype.hasOwnProperty.call(value, property);
}

function stringArray(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.every((item) => typeof item === "string" && item.length > 0)
  );
}

function idArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every(isId);
}

function validateCompositionRequest(body: unknown): string | null {
  if (!isObject(body)) {
    return "Request body must be a JSON object.";
  }

  if (!isSemver(body.contract_version)) {
    return "contract_version must be semver.";
  }

  if (!["dev", "staging", "prod"].includes(String(body.environment))) {
    return "environment must be dev, staging, or prod.";
  }

  if (!isObject(body.principal)) {
    return "principal is required.";
  }

  if (!["role", "user", "service"].includes(String(body.principal.kind))) {
    return "principal.kind must be role, user, or service.";
  }

  if (!isId(body.principal.id)) {
    return "principal.id must be a valid id.";
  }

  if (!isObject(body.requested_profile_generation)) {
    return "requested_profile_generation is required.";
  }

  if (!["initial", "recomposition"].includes(String(body.requested_profile_generation.mode))) {
    return "requested_profile_generation.mode must be initial or recomposition.";
  }

  if (!hasProperty(body.requested_profile_generation, "parent_profile_id")) {
    return "requested_profile_generation.parent_profile_id is required.";
  }

  const parentProfileId = body.requested_profile_generation.parent_profile_id;
  if (parentProfileId !== null && parentProfileId !== undefined && !isId(parentProfileId)) {
    return "requested_profile_generation.parent_profile_id must be null or a valid id.";
  }

  if (!isObject(body.task)) {
    return "task is required.";
  }

  if (!isId(body.task.id)) {
    return "task.id must be a valid id.";
  }

  if (!isId(body.task.type)) {
    return "task.type must be a valid id.";
  }

  if (typeof body.task.objective !== "string" || body.task.objective.length === 0) {
    return "task.objective is required.";
  }

  if (!["low", "medium", "high"].includes(String(body.task.risk_level))) {
    return "task.risk_level must be low, medium, or high.";
  }

  if (!isObject(body.task.signals)) {
    return "task.signals is required.";
  }

  if (!idArray(body.task.signals.domain_tags)) {
    return "task.signals.domain_tags must be an array of ids.";
  }

  if (!idArray(body.task.signals.capability_hints)) {
    return "task.signals.capability_hints must be an array of ids.";
  }

  if (!stringArray(body.task.signals.constraints)) {
    return "task.signals.constraints must be an array of non-empty strings.";
  }

  return null;
}

async function readJson(request: Request): Promise<unknown> {
  const contentLength = request.headers.get("content-length");
  if (contentLength !== null && Number(contentLength) > MAX_JSON_BODY_BYTES) {
    throw new Error("request_body_too_large");
  }

  const bodyText = await request.text();
  if (bodyText.length > MAX_JSON_BODY_BYTES) {
    throw new Error("request_body_too_large");
  }

  return JSON.parse(bodyText);
}

function compositionContextResponse(): CompositionContextResponse {
  return {
    contract_version: CONTRACT_VERSION,
    registry_version: REGISTRY_VERSION,
    composition_status: "pending_registry_implementation",
    candidate_modules: [],
    applicable_policies: [],
    allowed_knowledge_scopes: [],
    allowed_data_scopes: [],
    allowed_memory_scopes: [],
    validation_requirements: [],
  };
}

async function handleCompositionContext(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return errorResponse(405, "method_not_allowed", "Use POST for /composition/context.");
  }

  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return errorResponse(415, "unsupported_media_type", "Request body must be JSON.");
  }

  let body: unknown;
  try {
    body = await readJson(request);
  } catch (error) {
    if (error instanceof Error && error.message === "request_body_too_large") {
      return errorResponse(413, "request_body_too_large", "Request body exceeds 64 KiB.");
    }

    return errorResponse(400, "invalid_json", "Request body must be valid JSON.");
  }

  const validationError = validateCompositionRequest(body);
  if (validationError !== null) {
    return errorResponse(400, "invalid_composition_context_request", validationError);
  }

  return jsonResponse(compositionContextResponse());
}

function handleHealth(env: Env): Response {
  return jsonResponse({
    status: "ok",
    service: "scas-control-api",
    environment: env.ENVIRONMENT,
  });
}

export default {
  async fetch(request: Request, env: Env, _ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      if (request.method !== "GET") {
        return errorResponse(405, "method_not_allowed", "Use GET for /health.");
      }

      return handleHealth(env);
    }

    if (url.pathname === "/composition/context") {
      return handleCompositionContext(request);
    }

    return errorResponse(404, "not_found", "Endpoint not found.");
  },
} satisfies ExportedHandler<Env>;
