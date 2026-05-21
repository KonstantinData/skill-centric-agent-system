/// <reference types="@cloudflare/vitest-pool-workers/types" />

import { SELF } from "cloudflare:test";
import { describe, expect, it } from "vitest";

const compositionRequest = {
  contract_version: "0.1.0",
  environment: "dev",
  principal: {
    kind: "role",
    id: "developer",
  },
  requested_profile_generation: {
    mode: "initial",
    parent_profile_id: null,
  },
  task: {
    id: "task-code-review",
    type: "code-review",
    objective: "Review the current repository diff.",
    risk_level: "medium",
    signals: {
      domain_tags: ["software-engineering"],
      capability_hints: ["code-review"],
      constraints: ["least privilege"],
    },
  },
};

async function fetchJson(path: string, init?: RequestInit): Promise<Response> {
  return SELF.fetch(`https://control-api.test${path}`, init);
}

describe("control API worker", () => {
  it("returns health state", async () => {
    const response = await fetchJson("/health");
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body).toEqual({
      status: "ok",
      service: "scas-control-api",
      environment: "dev",
    });
  });

  it("returns an empty composition context while registry implementation is pending", async () => {
    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(compositionRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body).toEqual({
      contract_version: "0.1.0",
      registry_version: "0.1.0",
      composition_status: "pending_registry_implementation",
      candidate_modules: [],
      applicable_policies: [],
      allowed_knowledge_scopes: [],
      allowed_data_scopes: [],
      allowed_memory_scopes: [],
      validation_requirements: [],
    });
  });

  it("rejects unsupported methods on composition context", async () => {
    const response = await fetchJson("/composition/context");
    const body = await response.json();

    expect(response.status).toBe(405);
    expect(body).toEqual({
      error: {
        code: "method_not_allowed",
        message: "Use POST for /composition/context.",
      },
    });
  });

  it("rejects non-json composition context requests", async () => {
    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "content-type": "text/plain",
      },
      body: "not-json",
    });
    const body = await response.json();

    expect(response.status).toBe(415);
    expect(body.error.code).toBe("unsupported_media_type");
  });

  it("rejects invalid composition context bodies", async () => {
    const invalidRequest = structuredClone(compositionRequest);
    invalidRequest.requested_profile_generation = {
      mode: "initial",
    } as typeof compositionRequest.requested_profile_generation;

    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(invalidRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(400);
    expect(body.error).toEqual({
      code: "invalid_composition_context_request",
      message: "requested_profile_generation.parent_profile_id is required.",
    });
  });

  it("returns not found for unknown endpoints", async () => {
    const response = await fetchJson("/missing");
    const body = await response.json();

    expect(response.status).toBe(404);
    expect(body.error.code).toBe("not_found");
  });
});
