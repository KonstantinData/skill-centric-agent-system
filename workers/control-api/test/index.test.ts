/// <reference types="@cloudflare/vitest-pool-workers/types" />

import { SELF, env, reset } from "cloudflare:test";
import { beforeEach, describe, expect, it } from "vitest";

import migration0001 from "../../../migrations/cloudflare/d1/0001_control_plane.sql?raw";
import migration0002 from "../../../migrations/cloudflare/d1/0002_module_selection_metadata.sql?raw";

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

async function fetchJson(path: string, init?: RequestInit): Promise<Response> {
  return SELF.fetch(`https://control-api.test${path}`, init);
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

beforeEach(async () => {
  await reset();
  await migrateControlPlane();
  await seedControlPlane();
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
