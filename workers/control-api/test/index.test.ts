/// <reference types="@cloudflare/vitest-pool-workers/types" />

import { env, reset } from "cloudflare:test";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import migration0001 from "../../../migrations/cloudflare/d1/0001_control_plane.sql?raw";
import migration0002 from "../../../migrations/cloudflare/d1/0002_module_selection_metadata.sql?raw";
import worker from "../src/index";

const compositionRequest = {
  contract_version: "0.1.0",
  environment: "dev",
  principal: {
    kind: "role",
    id: "repository-maintainer",
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
      domain_tags: ["repository", "contracts"],
      capability_hints: ["analysis"],
      available_inputs: ["repository", "diff"],
      constraints: ["least privilege"],
    },
  },
};

const knowledgeIngestRequest = {
  contract_version: "0.1.0",
  source: {
    id: "knowledge-source-scas-docs",
    name: "SCAS Docs",
    source_type: "repo",
    uri: "repo://docs",
    owner: "repository-maintainer",
    sensitivity: "internal",
  },
  document: {
    id: "knowledge-doc-runtime",
    version: "0.1.0",
    content: "# Runtime\n\nRuntime notes for the control plane.",
    scope_id: "mod-architecture-docs",
  },
};

const memoryIngestRequest = {
  contract_version: "0.1.0",
  memory: {
    id: "memory-runtime-decision",
    memory_scope_id: "mod-project-memory",
    version: "0.1.0",
    content: {
      summary: "Use Flight Recorder events for runtime reconstruction.",
      evidence_uri: "hetzner://runtime/traces/run-code-review/events/000.json",
    },
    source_run_id: "run-code-review",
    source_profile_id: "profile-code-review",
    sensitivity: "internal",
    retention_policy: "project-memory-180d",
  },
};

const ADMIN_TOKEN = "test-admin-token";
const COMPOSITION_TOKEN = "test-composition-token";
const INGESTION_TOKEN = "test-ingestion-token";
const RETRIEVAL_TOKEN = "test-retrieval-token";
const AI_GATEWAY_TOKEN = "test-ai-gateway-token";

type TestEnv = Env & {
  CONTROL_API_TOKEN?: string;
  CONTROL_API_COMPOSITION_TOKEN?: string;
  CONTROL_API_INGESTION_TOKEN?: string;
  CONTROL_API_RETRIEVAL_TOKEN?: string;
  CONTROL_API_AI_GATEWAY_TOKEN?: string;
  AI_GATEWAY_ACCOUNT_ID?: string;
  AI_GATEWAY_ID?: string;
  OPENAI_API_KEY?: string;
  AI_GATEWAY_AUTH_TOKEN?: string;
};

function testEnv(overrides: Partial<TestEnv> = {}): TestEnv {
  return {
    ...env,
    CONTROL_API_TOKEN: ADMIN_TOKEN,
    CONTROL_API_COMPOSITION_TOKEN: COMPOSITION_TOKEN,
    CONTROL_API_INGESTION_TOKEN: INGESTION_TOKEN,
    CONTROL_API_RETRIEVAL_TOKEN: RETRIEVAL_TOKEN,
    CONTROL_API_AI_GATEWAY_TOKEN: AI_GATEWAY_TOKEN,
    ...overrides,
  } as TestEnv;
}

function testContext(): ExecutionContext {
  return {
    waitUntil() {},
    passThroughOnException() {},
  } as unknown as ExecutionContext;
}

async function fetchJson(
  path: string,
  init?: RequestInit,
  overrides: Partial<TestEnv> = {},
): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (!headers.has("authorization") && path !== "/health") {
    headers.set("authorization", `Bearer ${ADMIN_TOKEN}`);
  }
  return worker.fetch(
    new Request(`https://control-api.test${path}`, {
      ...init,
      headers,
    }),
    testEnv(overrides),
    testContext(),
  );
}

async function migrateControlPlane(): Promise<void> {
  const migrationSql = `${migration0001}\n${migration0002}`.replaceAll(
    "PRAGMA foreign_keys = ON;",
    "",
  );
  const statements = migrationSql
    .split(";")
    .map((statement) => statement.trim())
    .filter((statement) => statement.length > 0);

  for (const statement of statements) {
    await env.SCAS_CONTROL_DB.prepare(statement).run();
  }
}

async function seedControlPlane(): Promise<void> {
  const db = env.SCAS_CONTROL_DB;
  await db.batch([
    db.prepare(
      `
      INSERT INTO modules (
        id,
        name,
        kind,
        status,
        current_version_id,
        created_at,
        updated_at
      )
      VALUES (?, ?, ?, 'active', ?, '2026-05-21T20:00:00Z', '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mod-git-diff-analysis",
      "git-diff-analysis",
      "skill",
      "mv-git-diff-analysis-0-1-0",
    ),
    db.prepare(
      `
      INSERT INTO modules (
        id,
        name,
        kind,
        status,
        current_version_id,
        created_at,
        updated_at
      )
      VALUES (?, ?, ?, 'active', ?, '2026-05-21T20:00:00Z', '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mod-architecture-docs",
      "architecture-docs",
      "knowledge_scope",
      "mv-architecture-docs-0-1-0",
    ),
    db.prepare(
      `
      INSERT INTO modules (
        id,
        name,
        kind,
        status,
        current_version_id,
        created_at,
        updated_at
      )
      VALUES (?, ?, ?, 'active', ?, '2026-05-21T20:00:00Z', '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mod-project-memory",
      "project-memory",
      "memory_scope",
      "mv-project-memory-0-1-0",
    ),
    db.prepare(
      `
      INSERT INTO modules (
        id,
        name,
        kind,
        status,
        current_version_id,
        created_at,
        updated_at
      )
      VALUES (?, ?, ?, 'active', ?, '2026-05-21T20:00:00Z', '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mod-no-destructive-commands",
      "no-destructive-commands",
      "policy",
      "mv-no-destructive-commands-0-1-0",
    ),
    db.prepare(
      `
      INSERT INTO module_versions (
        id,
        module_id,
        version,
        source_uri,
        checksum,
        selection_base_score,
        created_at
      )
      VALUES (?, ?, '0.1.0', ?, ?, ?, '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mv-git-diff-analysis-0-1-0",
      "mod-git-diff-analysis",
      "repo://examples/modules/git-diff-analysis.json",
      "sha256:test-git-diff-analysis",
      0.74,
    ),
    db.prepare(
      `
      INSERT INTO module_versions (
        id,
        module_id,
        version,
        source_uri,
        checksum,
        selection_base_score,
        created_at
      )
      VALUES (?, ?, '0.1.0', ?, ?, ?, '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mv-architecture-docs-0-1-0",
      "mod-architecture-docs",
      "repo://docs/architecture.md",
      "sha256:test-architecture-docs",
      0.5,
    ),
    db.prepare(
      `
      INSERT INTO module_versions (
        id,
        module_id,
        version,
        source_uri,
        checksum,
        selection_base_score,
        created_at
      )
      VALUES (?, ?, '0.1.0', ?, ?, ?, '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mv-project-memory-0-1-0",
      "mod-project-memory",
      "r2://scas-memory-dev/memory/project-memory/manifest.json",
      "sha256:test-project-memory",
      0.5,
    ),
    db.prepare(
      `
      INSERT INTO module_versions (
        id,
        module_id,
        version,
        source_uri,
        checksum,
        selection_base_score,
        created_at
      )
      VALUES (?, ?, '0.1.0', ?, ?, ?, '2026-05-21T20:00:00Z')
      `,
    ).bind(
      "mv-no-destructive-commands-0-1-0",
      "mod-no-destructive-commands",
      "repo://policies/no-destructive-commands",
      "sha256:test-no-destructive-commands",
      1,
    ),
  ]);

  await db.batch([
    db.prepare(
      `
      INSERT INTO module_selection_metadata (
        id,
        module_version_id,
        description,
        capability_class,
        domain_tags_json,
        task_types_json,
        risk_levels_json,
        task_domains_json,
        required_inputs_json,
        phrases_json,
        negative_phrases_json,
        triggers_json,
        inputs_json,
        outputs_json,
        score_modifiers_json,
        requires_all_policies
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
    ).bind(
      "msm-git-diff-analysis-0-1-0",
      "mv-git-diff-analysis-0-1-0",
      "Analyze repository diffs for code review tasks.",
      "analysis",
      JSON.stringify(["repository", "contracts"]),
      JSON.stringify(["code-review"]),
      JSON.stringify(["low", "medium", "high"]),
      JSON.stringify(["repository", "contracts"]),
      JSON.stringify(["repository", "diff"]),
      JSON.stringify(["review", "diff"]),
      JSON.stringify(["deploy"]),
      JSON.stringify(["review", "diff"]),
      JSON.stringify(["repository", "diff"]),
      JSON.stringify(["review-findings"]),
      JSON.stringify([
        {
          signal: "task_type:code-review",
          weight: 0.1,
          reason: "Task type matches code review.",
        },
        {
          signal: "domain:repository",
          weight: 0.08,
          reason: "Repository domain matches.",
        },
        {
          signal: "input:diff",
          weight: 0.05,
          reason: "Diff input is available.",
        },
        {
          signal: "capability_class:analysis",
          weight: 0.05,
          reason: "Analysis capability was requested.",
        },
      ]),
      1,
    ),
    db.prepare(
      `
      INSERT INTO module_selection_metadata (
        id,
        module_version_id,
        description,
        capability_class,
        domain_tags_json,
        task_types_json,
        risk_levels_json,
        task_domains_json,
        required_inputs_json,
        phrases_json,
        negative_phrases_json,
        triggers_json,
        inputs_json,
        outputs_json,
        score_modifiers_json,
        requires_all_policies
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
    ).bind(
      "msm-architecture-docs-0-1-0",
      "mv-architecture-docs-0-1-0",
      "Repository architecture documentation knowledge scope.",
      "knowledge_access",
      JSON.stringify(["repository", "architecture"]),
      JSON.stringify(["code-review"]),
      JSON.stringify(["low", "medium", "high"]),
      JSON.stringify(["repository", "architecture"]),
      JSON.stringify([]),
      JSON.stringify(["architecture", "contract"]),
      JSON.stringify([]),
      JSON.stringify(["architecture"]),
      JSON.stringify([]),
      JSON.stringify(["architecture-context"]),
      JSON.stringify([
        {
          signal: "domain:repository",
          weight: 0.1,
          reason: "Repository domain matches architecture documentation.",
        },
      ]),
      0,
    ),
    db.prepare(
      `
      INSERT INTO module_selection_metadata (
        id,
        module_version_id,
        description,
        capability_class,
        domain_tags_json,
        task_types_json,
        risk_levels_json,
        task_domains_json,
        required_inputs_json,
        phrases_json,
        negative_phrases_json,
        triggers_json,
        inputs_json,
        outputs_json,
        score_modifiers_json,
        requires_all_policies
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
    ).bind(
      "msm-project-memory-0-1-0",
      "mv-project-memory-0-1-0",
      "Long-lived project memory scope for consolidated decisions.",
      "memory_access",
      JSON.stringify(["repository", "project-memory"]),
      JSON.stringify(["code-review"]),
      JSON.stringify(["low", "medium", "high"]),
      JSON.stringify(["repository"]),
      JSON.stringify([]),
      JSON.stringify(["memory"]),
      JSON.stringify([]),
      JSON.stringify(["memory"]),
      JSON.stringify([]),
      JSON.stringify(["project-memory"]),
      JSON.stringify([]),
      0,
    ),
    db.prepare(
      `
      INSERT INTO module_selection_metadata (
        id,
        module_version_id,
        description,
        capability_class,
        domain_tags_json,
        task_types_json,
        risk_levels_json,
        task_domains_json,
        required_inputs_json,
        phrases_json,
        negative_phrases_json,
        triggers_json,
        inputs_json,
        outputs_json,
        score_modifiers_json,
        requires_all_policies
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
    ).bind(
      "msm-no-destructive-commands-0-1-0",
      "mv-no-destructive-commands-0-1-0",
      "Policy that blocks destructive repository commands by default.",
      "policy",
      JSON.stringify(["repository", "safety"]),
      JSON.stringify(["code-review"]),
      JSON.stringify(["low", "medium", "high"]),
      JSON.stringify(["repository"]),
      JSON.stringify([]),
      JSON.stringify(["least privilege"]),
      JSON.stringify([]),
      JSON.stringify(["no destructive commands"]),
      JSON.stringify([]),
      JSON.stringify(["policy-decision"]),
      JSON.stringify([]),
      0,
    ),
  ]);

  await db.batch([
    db.prepare(
      `
      INSERT INTO module_dependencies (
        id,
        module_version_id,
        dependency_kind,
        dependency_id,
        is_required
      )
      VALUES (?, ?, ?, ?, 1)
      `,
    ).bind(
      "dep-git-diff-architecture-docs",
      "mv-git-diff-analysis-0-1-0",
      "knowledge_scope",
      "mod-architecture-docs",
    ),
    db.prepare(
      `
      INSERT INTO module_dependencies (
        id,
        module_version_id,
        dependency_kind,
        dependency_id,
        is_required
      )
      VALUES (?, ?, ?, ?, 1)
      `,
    ).bind(
      "dep-git-diff-no-destructive",
      "mv-git-diff-analysis-0-1-0",
      "policy",
      "mod-no-destructive-commands",
    ),
    db.prepare(
      `
      INSERT INTO policy_bindings (
        id,
        policy_id,
        target_kind,
        target_id,
        effect,
        priority
      )
      VALUES (?, ?, 'module', ?, 'allow', 100)
      `,
    ).bind(
      "pb-no-destructive-git-diff",
      "mod-no-destructive-commands",
      "mod-git-diff-analysis",
    ),
    db.prepare(
      `
      INSERT INTO scope_bindings (
        id,
        scope_id,
        scope_kind,
        principal_kind,
        principal_id,
        policy_id,
        effect
      )
      VALUES (?, ?, ?, 'role', 'repository-maintainer', ?, 'allow')
      `,
    ).bind(
      "sb-maintainer-architecture-docs",
      "mod-architecture-docs",
      "knowledge_scope",
      "mod-no-destructive-commands",
    ),
    db.prepare(
      `
      INSERT INTO scope_bindings (
        id,
        scope_id,
        scope_kind,
        principal_kind,
        principal_id,
        policy_id,
        effect
      )
      VALUES (?, ?, ?, 'role', 'repository-maintainer', ?, 'allow')
      `,
    ).bind(
      "sb-maintainer-project-memory",
      "mod-project-memory",
      "memory_scope",
      "mod-no-destructive-commands",
    ),
  ]);

  await env.SCAS_CONFIG.put("registry:version", "0.1.0");
}

function embeddingVector(seed: number): number[] {
  return Array.from({ length: 1536 }, (_value, index) => (index === 0 ? seed : 0));
}

function stubEmbeddingFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body));
      const inputs = Array.isArray(body.input) ? body.input : [body.input];
      return new Response(
        JSON.stringify({
          object: "list",
          data: inputs.map((_inputValue: unknown, index: number) => ({
            object: "embedding",
            index,
            embedding: embeddingVector(index + 1),
          })),
          model: "text-embedding-3-small",
          usage: {
            prompt_tokens: inputs.length,
            total_tokens: inputs.length,
          },
        }),
        {
          headers: {
            "content-type": "application/json",
          },
        },
      );
    }),
  );
}

function queueMessage(body: unknown): {
  message: Message<unknown>;
  ack: ReturnType<typeof vi.fn>;
  retry: ReturnType<typeof vi.fn>;
} {
  const ack = vi.fn();
  const retry = vi.fn();
  return {
    message: {
      id: "msg-embedding-1",
      timestamp: new Date("2026-05-23T16:00:00Z"),
      body,
      attempts: 1,
      ack,
      retry,
    } as unknown as Message<unknown>,
    ack,
    retry,
  };
}

function messageBatch(message: Message<unknown>): MessageBatch<unknown> {
  return {
    queue: "scas-ingest-dev",
    messages: [message],
    metadata: {
      metrics: {
        backlogCount: 1,
        backlogBytes: 256,
      },
    },
    retryAll() {},
    ackAll() {},
  };
}

beforeEach(async () => {
  await reset();
  await migrateControlPlane();
  await seedControlPlane();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

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

  it("requires bearer authorization for protected endpoints", async () => {
    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "authorization": "",
        "content-type": "application/json",
      },
      body: JSON.stringify(compositionRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(401);
    expect(body.error.code).toBe("authorization_required");
  });

  it("rejects invalid bearer authorization", async () => {
    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "authorization": "Bearer wrong-token",
        "content-type": "application/json",
      },
      body: JSON.stringify(compositionRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(401);
    expect(body.error.code).toBe("authorization_invalid");
  });

  it("fails closed when protected endpoint auth is not configured", async () => {
    const response = await fetchJson(
      "/composition/context",
      {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify(compositionRequest),
      },
      {
        CONTROL_API_TOKEN: undefined,
        CONTROL_API_COMPOSITION_TOKEN: undefined,
        CONTROL_API_INGESTION_TOKEN: undefined,
        CONTROL_API_RETRIEVAL_TOKEN: undefined,
        CONTROL_API_AI_GATEWAY_TOKEN: undefined,
      },
    );
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body.error.code).toBe("control_api_auth_unconfigured");
  });

  it("enforces endpoint-scoped bearer authorization", async () => {
    const allowed = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "authorization": `Bearer ${COMPOSITION_TOKEN}`,
        "content-type": "application/json",
      },
      body: JSON.stringify(compositionRequest),
    });
    expect(allowed.status).toBe(200);

    const denied = await fetchJson("/retrieval/context", {
      method: "POST",
      headers: {
        "authorization": `Bearer ${COMPOSITION_TOKEN}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        contract_version: "0.1.0",
        principal: {
          kind: "role",
          id: "repository-maintainer",
        },
        query: "runtime reconstruction",
        knowledge_scope_ids: ["mod-architecture-docs"],
        memory_scope_ids: ["mod-project-memory"],
        top_k: 5,
      }),
    });
    const body = await denied.json();

    expect(denied.status).toBe(403);
    expect(body.error.code).toBe("authorization_scope_denied");
  });

  it("returns a D1-backed composition context", async () => {
    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(compositionRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.composition_status).toBe("ready");
    expect(body.candidate_modules).toEqual([
      expect.objectContaining({
        id: "mod-git-diff-analysis",
        name: "git-diff-analysis",
        kind: "skill",
        version: "0.1.0",
        score: 1,
      }),
    ]);
    expect(body.applicable_policies).toEqual([
      expect.objectContaining({
        id: "mod-no-destructive-commands",
        kind: "policy",
      }),
    ]);
    expect(body.allowed_knowledge_scopes).toEqual([
      expect.objectContaining({
        id: "mod-architecture-docs",
        kind: "knowledge_scope",
        score: 0.6,
      }),
    ]);
    expect(body.allowed_memory_scopes).toEqual([
      expect.objectContaining({
        id: "mod-project-memory",
        kind: "memory_scope",
        score: 0.5,
      }),
    ]);
    expect(body.policy_decisions).toEqual([
      {
        module: {
          id: "mod-git-diff-analysis",
          name: "git-diff-analysis",
          kind: "skill",
          version: "0.1.0",
        },
        effect: "allow",
        reasons: ["Required policies are allowed for the module."],
      },
    ]);
    expect(body.graph_validation).toEqual({
      is_valid: true,
      errors: [],
      reachable_modules: [
        {
          id: "mod-architecture-docs",
          name: "architecture-docs",
          kind: "knowledge_scope",
          version: "0.1.0",
        },
        {
          id: "mod-git-diff-analysis",
          name: "git-diff-analysis",
          kind: "skill",
          version: "0.1.0",
        },
        {
          id: "mod-no-destructive-commands",
          name: "no-destructive-commands",
          kind: "policy",
          version: "0.1.0",
        },
      ],
    });
  });

  it("denies candidates when required policies are not allowed", async () => {
    await env.SCAS_CONTROL_DB.prepare("DELETE FROM policy_bindings").run();

    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(compositionRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.composition_status).toBe("denied");
    expect(body.candidate_modules).toEqual([]);
    expect(body.policy_decisions[0].effect).toBe("needs_clarification");
  });

  it("fails closed when no module candidate matches the task", async () => {
    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        ...compositionRequest,
        task: {
          ...compositionRequest.task,
          id: "task-unknown",
          type: "unknown-task",
          signals: {
            domain_tags: ["unknown"],
            capability_hints: ["unknown"],
            available_inputs: ["unknown"],
            constraints: [],
          },
        },
      }),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.composition_status).toBe("denied");
    expect(body.candidate_modules).toEqual([]);
    expect(body.graph_validation).toEqual({
      is_valid: true,
      errors: [],
      reachable_modules: [],
    });
  });

  it("returns denied composition status when graph validation fails", async () => {
    await env.SCAS_CONTROL_DB.prepare(
      "UPDATE module_dependencies SET dependency_kind = ? WHERE id = ?",
    )
      .bind("tool", "dep-git-diff-architecture-docs")
      .run();

    const response = await fetchJson("/composition/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(compositionRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.composition_status).toBe("denied");
    expect(body.graph_validation.is_valid).toBe(false);
    expect(body.graph_validation.errors[0]).toContain("as tool, got knowledge_scope");
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

  it("ingests normalized knowledge into R2 and D1 metadata", async () => {
    const response = await fetchJson("/knowledge/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(knowledgeIngestRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.status).toBe("succeeded");
    expect(body.document_id).toBe("knowledge-doc-runtime");
    expect(body.content_uri).toContain("knowledge/knowledge-source-scas-docs");
    expect(body.chunk_count).toBe(1);
    expect(body.vector_status).toBe("embedding_update_queued");
    expect(body.embedding_job_id).toBe("ij-embedding-knowledge-doc-runtime");

    const stored = await env.SCAS_KNOWLEDGE_BUCKET.get(
      "knowledge/knowledge-source-scas-docs/knowledge-doc-runtime/v0.1.0/normalized.md",
    );
    expect(await stored?.text()).toBe("# Runtime\n\nRuntime notes for the control plane.\n");

    const document = await env.SCAS_CONTROL_DB.prepare(
      "SELECT id, source_id, content_uri, manifest_uri, status FROM knowledge_documents WHERE id = ?",
    )
      .bind("knowledge-doc-runtime")
      .first();
    expect(document).toEqual(
      expect.objectContaining({
        id: "knowledge-doc-runtime",
        source_id: "knowledge-source-scas-docs",
        status: "active",
      }),
    );

    const chunk = await env.SCAS_CONTROL_DB.prepare(
      "SELECT id, document_id, scope_id, vector_id FROM knowledge_chunks WHERE document_id = ?",
    )
      .bind("knowledge-doc-runtime")
      .first();
    expect(chunk).toEqual(
      expect.objectContaining({
        id: "chunk-knowledge-doc-runtime-0",
        document_id: "knowledge-doc-runtime",
        scope_id: "mod-architecture-docs",
        vector_id: "vec-knowledge-doc-runtime-0",
      }),
    );

    const embeddingJob = await env.SCAS_CONTROL_DB.prepare(
      "SELECT id, job_type, status, target_kind, target_id, attempts FROM ingestion_jobs WHERE id = ?",
    )
      .bind("ij-embedding-knowledge-doc-runtime")
      .first();
    expect(embeddingJob).toEqual(
      expect.objectContaining({
        id: "ij-embedding-knowledge-doc-runtime",
        job_type: "embedding_update",
        status: "queued",
        target_kind: "knowledge_document",
        target_id: "knowledge-doc-runtime",
        attempts: 0,
      }),
    );
  });

  it("ingests validated memory without copying raw runtime traces", async () => {
    const response = await fetchJson("/memory/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(memoryIngestRequest),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.status).toBe("succeeded");
    expect(body.memory_id).toBe("memory-runtime-decision");
    expect(body.vector_status).toBe("embedding_update_queued");
    expect(body.embedding_job_id).toBe("ij-embedding-memory-runtime-decision");

    const stored = await env.SCAS_MEMORY_BUCKET.get(
      "memory/mod-project-memory/memory-runtime-decision/v0.1.0/content.json",
    );
    expect(await stored?.json()).toEqual(memoryIngestRequest.memory.content);

    const memory = await env.SCAS_CONTROL_DB.prepare(
      "SELECT id, memory_scope_id, source_run_id, status FROM memory_records WHERE id = ?",
    )
      .bind("memory-runtime-decision")
      .first();
    expect(memory).toEqual(
      expect.objectContaining({
        id: "memory-runtime-decision",
        memory_scope_id: "mod-project-memory",
        source_run_id: "run-code-review",
        status: "active",
      }),
    );

    const embeddingJob = await env.SCAS_CONTROL_DB.prepare(
      "SELECT id, job_type, status, target_kind, target_id FROM ingestion_jobs WHERE id = ?",
    )
      .bind("ij-embedding-memory-runtime-decision")
      .first();
    expect(embeddingJob).toEqual(
      expect.objectContaining({
        id: "ij-embedding-memory-runtime-decision",
        job_type: "embedding_update",
        status: "queued",
        target_kind: "memory_record",
        target_id: "memory-runtime-decision",
      }),
    );

    const rejectedResponse = await fetchJson("/memory/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        ...memoryIngestRequest,
        raw_runtime_trace: {
          copied: true,
        },
      }),
    });
    const rejectedBody = await rejectedResponse.json();

    expect(rejectedResponse.status).toBe(400);
    expect(rejectedBody.error.message).toContain("Raw runtime traces");
  });

  it("processes queued knowledge embeddings through AI Gateway and Vectorize", async () => {
    const ingestResponse = await fetchJson("/knowledge/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(knowledgeIngestRequest),
    });
    const ingestBody = await ingestResponse.json();
    const knowledgeUpsert = vi.fn(async (vectors: VectorizeVector[]) => ({
      ids: vectors.map((vector) => vector.id),
      count: vectors.length,
    }));
    const { message, ack, retry } = queueMessage({
      contract_version: "0.1.0",
      job_id: ingestBody.embedding_job_id,
      target_kind: "knowledge_document",
      target_id: "knowledge-doc-runtime",
      source_uri: "repo://docs",
      queued_at: "2026-05-23T16:00:00Z",
    });
    stubEmbeddingFetch();

    await worker.queue?.(
      messageBatch(message),
      testEnv({
        AI_GATEWAY_ACCOUNT_ID: "test-account",
        AI_GATEWAY_ID: "default",
        OPENAI_API_KEY: "test-openai-key",
        SCAS_KNOWLEDGE_INDEX: {
          upsert: knowledgeUpsert,
        } as unknown as VectorizeIndex,
      }),
      testContext(),
    );

    expect(ack).toHaveBeenCalledTimes(1);
    expect(retry).not.toHaveBeenCalled();
    expect(knowledgeUpsert).toHaveBeenCalledWith([
      expect.objectContaining({
        id: "vec-knowledge-doc-runtime-0",
        values: embeddingVector(1),
        metadata: expect.objectContaining({
          document_id: "knowledge-doc-runtime",
          chunk_id: "chunk-knowledge-doc-runtime-0",
          scope_id: "mod-architecture-docs",
          target_kind: "knowledge_chunk",
        }),
      }),
    ]);

    const job = await env.SCAS_CONTROL_DB.prepare(
      "SELECT status, attempts FROM ingestion_jobs WHERE id = ?",
    )
      .bind("ij-embedding-knowledge-doc-runtime")
      .first();
    expect(job).toEqual(
      expect.objectContaining({
        status: "succeeded",
        attempts: 1,
      }),
    );
  });

  it("marks embedding jobs failed and retries when AI Gateway is unavailable", async () => {
    const ingestResponse = await fetchJson("/memory/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(memoryIngestRequest),
    });
    const ingestBody = await ingestResponse.json();
    const { message, ack, retry } = queueMessage({
      contract_version: "0.1.0",
      job_id: ingestBody.embedding_job_id,
      target_kind: "memory_record",
      target_id: "memory-runtime-decision",
      source_uri: "r2://scas-memory-dev/memory/mod-project-memory/memory-runtime-decision/v0.1.0/content.json",
      queued_at: "2026-05-23T16:00:00Z",
    });

    await worker.queue?.(messageBatch(message), testEnv(), testContext());

    expect(ack).not.toHaveBeenCalled();
    expect(retry).toHaveBeenCalledWith({
      delaySeconds: 30,
    });

    const job = await env.SCAS_CONTROL_DB.prepare(
      "SELECT status, attempts FROM ingestion_jobs WHERE id = ?",
    )
      .bind("ij-embedding-memory-runtime-decision")
      .first();
    expect(job).toEqual(
      expect.objectContaining({
        status: "failed",
        attempts: 1,
      }),
    );

    const audit = await env.SCAS_CONTROL_DB.prepare(
      "SELECT event_type, target_kind, target_id FROM audit_events WHERE event_type = ? AND target_id = ?",
    )
      .bind("embedding_update_failed", "memory-runtime-decision")
      .first();
    expect(audit).toEqual(
      expect.objectContaining({
        event_type: "embedding_update_failed",
        target_kind: "memory_record",
        target_id: "memory-runtime-decision",
      }),
    );
  });

  it("fails closed when memory ingestion references an unknown memory scope", async () => {
    const response = await fetchJson("/memory/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        ...memoryIngestRequest,
        memory: {
          ...memoryIngestRequest.memory,
          memory_scope_id: "mod-unknown-memory",
        },
      }),
    });
    const body = await response.json();

    expect(response.status).toBe(403);
    expect(body.error.code).toBe("memory_scope_not_allowed");
  });

  it("returns D1-post-validated retrieval context for Vectorize-ready records", async () => {
    await fetchJson("/knowledge/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(knowledgeIngestRequest),
    });
    await fetchJson("/memory/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(memoryIngestRequest),
    });

    const response = await fetchJson("/retrieval/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        contract_version: "0.1.0",
        principal: {
          kind: "role",
          id: "repository-maintainer",
        },
        query: "runtime reconstruction",
        knowledge_scope_ids: ["mod-architecture-docs"],
        memory_scope_ids: ["mod-project-memory"],
        top_k: 5,
      }),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.retrieval_status).toBe("ready");
    expect(body.vectorize.status).toBe("d1_prefilter_ready");
    expect(body.vectorize.bindings).toEqual({
      knowledge: true,
      memory: true,
    });
    expect(body.vectorize_matches).toEqual({
      knowledge: [],
      memory: [],
    });
    expect(body.knowledge_chunks[0]).toEqual(
      expect.objectContaining({
        id: "chunk-knowledge-doc-runtime-0",
        scope_id: "mod-architecture-docs",
        vector_id: "vec-knowledge-doc-runtime-0",
      }),
    );
    expect(body.memory_records[0]).toEqual(
      expect.objectContaining({
        id: "memory-runtime-decision",
        memory_scope_id: "mod-project-memory",
      }),
    );
  });

  it("returns no retrieval records for unauthorized principals", async () => {
    await fetchJson("/knowledge/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(knowledgeIngestRequest),
    });
    await fetchJson("/memory/ingest", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify(memoryIngestRequest),
    });

    const response = await fetchJson("/retrieval/context", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        contract_version: "0.1.0",
        principal: {
          kind: "role",
          id: "guest",
        },
        query: "runtime reconstruction",
        knowledge_scope_ids: ["mod-architecture-docs"],
        memory_scope_ids: ["mod-project-memory"],
        top_k: 5,
      }),
    });
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.allowed_knowledge_scope_ids).toEqual([]);
    expect(body.allowed_memory_scope_ids).toEqual([]);
    expect(body.knowledge_chunks).toEqual([]);
    expect(body.memory_records).toEqual([]);
  });

  it("fails closed when AI Gateway routing is not fully configured", async () => {
    const response = await fetchJson("/ai-gateway/openai/chat/completions", {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4.1-mini",
        messages: [{ role: "user", content: "hello" }],
      }),
    });
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body.error).toEqual({
      code: "ai_gateway_not_configured",
      message: "AI Gateway account and OPENAI_API_KEY Worker secret must be configured.",
    });
  });

  it("forwards authenticated AI Gateway and OpenAI auth as separate headers", async () => {
    const upstreamFetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toBe(
        "https://gateway.ai.cloudflare.com/v1/test-account/test-gateway/openai/chat/completions",
      );
      expect(init?.headers).toEqual({
        "authorization": "Bearer test-openai-key",
        "content-type": "application/json",
        "cf-aig-authorization": "Bearer test-cloudflare-gateway-token",
      });
      return new Response(
        JSON.stringify({
          id: "chatcmpl-test",
          object: "chat.completion",
          model: "gpt-4.1-mini",
          choices: [
            {
              index: 0,
              message: {
                role: "assistant",
                content: "ok",
              },
              finish_reason: "stop",
            },
          ],
        }),
        {
          headers: {
            "content-type": "application/json",
          },
        },
      );
    });
    vi.stubGlobal("fetch", upstreamFetch);

    const response = await fetchJson(
      "/ai-gateway/openai/chat/completions",
      {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          model: "gpt-4.1-mini",
          messages: [{ role: "user", content: "hello" }],
        }),
      },
      {
        AI_GATEWAY_ACCOUNT_ID: "test-account",
        AI_GATEWAY_ID: "test-gateway",
        OPENAI_API_KEY: "test-openai-key",
        AI_GATEWAY_AUTH_TOKEN: "test-cloudflare-gateway-token",
      },
    );
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(body.choices[0].message.content).toBe("ok");
    expect(upstreamFetch).toHaveBeenCalledTimes(1);
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
