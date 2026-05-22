const CONTRACT_VERSION = "0.1.0";
const DEFAULT_REGISTRY_VERSION = "0.1.0";
const MAX_JSON_BODY_BYTES = 64 * 1024;

const CANDIDATE_KINDS = new Set<ModuleKind>(["instruction", "skill", "tool"]);
const SCOPE_KINDS = new Set<ModuleKind>([
  "knowledge_scope",
  "data_scope",
  "memory_scope",
]);

type JsonObject = Record<string, unknown>;
type EnvironmentName = "dev" | "staging" | "prod";
type PrincipalKind = "role" | "user" | "service";
type RiskLevel = "low" | "medium" | "high";
type ModuleKind =
  | "skill"
  | "instruction"
  | "tool"
  | "knowledge_scope"
  | "data_scope"
  | "memory_scope"
  | "policy"
  | "validator";
type PolicyEffect = "allow" | "deny" | "needs_clarification";

type ErrorResponse = {
  error: {
    code: string;
    message: string;
  };
};

type CompositionRequest = {
  contract_version: string;
  environment: EnvironmentName;
  principal: {
    kind: PrincipalKind;
    id: string;
  };
  requested_profile_generation: {
    mode: "initial" | "recomposition";
    parent_profile_id: string | null;
  };
  task: {
    id: string;
    type: string;
    objective: string;
    risk_level: RiskLevel;
    signals: {
      domain_tags: string[];
      capability_hints: string[];
      available_inputs: string[];
      constraints: string[];
    };
  };
};

type ScoreModifier = {
  signal: string;
  weight: number;
  reason: string;
};

type ModuleIdentity = {
  id: string;
  name: string;
  kind: ModuleKind;
  version: string;
};

type ModuleReference = ModuleIdentity & {
  score: number;
  reason: string;
};

type PolicyDecision = {
  module: ModuleIdentity;
  effect: PolicyEffect;
  reasons: string[];
};

type GraphValidation = {
  is_valid: boolean;
  errors: string[];
  reachable_modules: ModuleIdentity[];
};

type CompositionContextResponse = {
  contract_version: string;
  registry_version: string;
  composition_status: "ready" | "denied";
  candidate_modules: ModuleReference[];
  applicable_policies: ModuleReference[];
  allowed_knowledge_scopes: ModuleReference[];
  allowed_data_scopes: ModuleReference[];
  allowed_memory_scopes: ModuleReference[];
  validation_requirements: ModuleReference[];
  policy_decisions: PolicyDecision[];
  graph_validation: GraphValidation;
};

type KnowledgeIngestRequest = {
  contract_version: string;
  source: {
    id: string;
    name: string;
    source_type: "repo" | "notion" | "r2" | "url" | "manual";
    uri: string;
    owner: string;
    sensitivity: "public" | "internal" | "confidential" | "secret";
  };
  document: {
    id: string;
    version: string;
    content: string;
    scope_id: string;
  };
};

type MemoryIngestRequest = {
  contract_version: string;
  memory: {
    id: string;
    memory_scope_id: string;
    version: string;
    content: Record<string, unknown>;
    source_run_id: string;
    source_profile_id: string;
    sensitivity: "public" | "internal" | "confidential" | "secret";
    retention_policy: string;
  };
};

type RetrievalRequest = {
  contract_version: string;
  principal: {
    kind: PrincipalKind;
    id: string;
  };
  query: string;
  query_embedding?: number[];
  knowledge_scope_ids: string[];
  memory_scope_ids: string[];
  top_k: number;
};

type KnowledgeRetrievalRow = {
  id: string;
  document_id: string;
  chunk_index: number;
  content_uri: string;
  vector_id: string;
  scope_id: string;
  token_count: number;
};

type MemoryRetrievalRow = {
  id: string;
  memory_scope_id: string;
  version: string;
  content_uri: string;
  manifest_uri: string;
  source_run_id: string;
  source_profile_id: string;
  sensitivity: string;
  retention_policy: string;
  status: string;
  vector_id: string;
};

type RegistryModuleRow = {
  id: string;
  name: string;
  kind: string;
  module_version_id: string;
  version: string;
  selection_base_score: number;
  description: string;
  capability_class: string;
  domain_tags_json: string;
  task_types_json: string;
  risk_levels_json: string;
  task_domains_json: string;
  required_inputs_json: string;
  phrases_json: string;
  negative_phrases_json: string;
  triggers_json: string;
  inputs_json: string;
  outputs_json: string;
  score_modifiers_json: string;
  requires_all_policies: number;
};

type RegistryModule = ModuleIdentity & {
  moduleVersionId: string;
  description: string;
  capabilityClass: string;
  domainTags: string[];
  taskTypes: string[];
  riskLevels: string[];
  taskDomains: string[];
  requiredInputs: string[];
  phrases: string[];
  negativePhrases: string[];
  triggers: string[];
  inputs: string[];
  outputs: string[];
  baseScore: number;
  scoreModifiers: ScoreModifier[];
  requiresAllPolicies: boolean;
};

type DependencyRow = {
  module_version_id: string;
  dependency_id: string;
  dependency_kind: string;
  is_required: number;
};

type ModuleDependency = {
  moduleVersionId: string;
  dependencyId: string;
  dependencyKind: ModuleKind;
  isRequired: boolean;
};

type PolicyBindingRow = {
  policy_id: string;
  target_kind: string;
  target_id: string;
  effect: string;
  priority: number;
};

type PolicyBinding = {
  policyId: string;
  targetKind: string;
  targetId: string;
  effect: "allow" | "deny";
  priority: number;
};

type ScopeBindingRow = {
  scope_id: string;
  scope_kind: string;
  policy_id: string;
  effect: string;
};

type ScopeBinding = {
  scopeId: string;
  scopeKind: ModuleKind;
  policyId: string;
  effect: "allow" | "deny";
};

type ScoredModule = {
  module: RegistryModule;
  score: number;
  matchedSignals: string[];
  negativeSignals: string[];
  reasons: string[];
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

function isModuleKind(value: unknown): value is ModuleKind {
  return (
    value === "skill" ||
    value === "instruction" ||
    value === "tool" ||
    value === "knowledge_scope" ||
    value === "data_scope" ||
    value === "memory_scope" ||
    value === "policy" ||
    value === "validator"
  );
}

function isSensitivity(value: unknown): value is "public" | "internal" | "confidential" | "secret" {
  return (
    value === "public" ||
    value === "internal" ||
    value === "confidential" ||
    value === "secret"
  );
}

function isSourceType(value: unknown): value is "repo" | "notion" | "r2" | "url" | "manual" {
  return (
    value === "repo" ||
    value === "notion" ||
    value === "r2" ||
    value === "url" ||
    value === "manual"
  );
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

function finiteNumberArray(value: unknown): value is number[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.length <= 4096 &&
    value.every((item) => typeof item === "number" && Number.isFinite(item))
  );
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

  if (!idArray(body.task.signals.available_inputs)) {
    return "task.signals.available_inputs must be an array of ids.";
  }

  if (!stringArray(body.task.signals.constraints)) {
    return "task.signals.constraints must be an array of non-empty strings.";
  }

  return null;
}

function validateKnowledgeIngestRequest(body: unknown): string | null {
  if (!isObject(body)) {
    return "Request body must be a JSON object.";
  }
  if (!isSemver(body.contract_version)) {
    return "contract_version must be semver.";
  }
  if (!isObject(body.source)) {
    return "source is required.";
  }
  if (!isId(body.source.id)) {
    return "source.id must be a valid id.";
  }
  if (typeof body.source.name !== "string" || body.source.name.length === 0) {
    return "source.name is required.";
  }
  if (!isSourceType(body.source.source_type)) {
    return "source.source_type is invalid.";
  }
  if (typeof body.source.uri !== "string" || body.source.uri.length === 0) {
    return "source.uri is required.";
  }
  if (typeof body.source.owner !== "string" || body.source.owner.length === 0) {
    return "source.owner is required.";
  }
  if (!isSensitivity(body.source.sensitivity)) {
    return "source.sensitivity is invalid.";
  }
  if (!isObject(body.document)) {
    return "document is required.";
  }
  if (!isId(body.document.id)) {
    return "document.id must be a valid id.";
  }
  if (!isSemver(body.document.version)) {
    return "document.version must be semver.";
  }
  if (typeof body.document.content !== "string" || body.document.content.length === 0) {
    return "document.content is required.";
  }
  if (!isId(body.document.scope_id)) {
    return "document.scope_id must be a valid id.";
  }
  return null;
}

function validateMemoryIngestRequest(body: unknown): string | null {
  if (!isObject(body)) {
    return "Request body must be a JSON object.";
  }
  if (hasProperty(body, "raw_runtime_trace") || hasProperty(body, "tool_output")) {
    return "Raw runtime traces and tool outputs must not be ingested into Cloudflare.";
  }
  if (!isSemver(body.contract_version)) {
    return "contract_version must be semver.";
  }
  if (!isObject(body.memory)) {
    return "memory is required.";
  }
  if (!isId(body.memory.id)) {
    return "memory.id must be a valid id.";
  }
  if (!isId(body.memory.memory_scope_id)) {
    return "memory.memory_scope_id must be a valid id.";
  }
  if (!isSemver(body.memory.version)) {
    return "memory.version must be semver.";
  }
  if (!isObject(body.memory.content)) {
    return "memory.content must be a JSON object.";
  }
  if (!isId(body.memory.source_run_id)) {
    return "memory.source_run_id must be a valid id.";
  }
  if (!isId(body.memory.source_profile_id)) {
    return "memory.source_profile_id must be a valid id.";
  }
  if (!isSensitivity(body.memory.sensitivity)) {
    return "memory.sensitivity is invalid.";
  }
  if (!isId(body.memory.retention_policy)) {
    return "memory.retention_policy must be a valid id.";
  }
  return null;
}

function validateRetrievalRequest(body: unknown): string | null {
  if (!isObject(body)) {
    return "Request body must be a JSON object.";
  }
  if (!isSemver(body.contract_version)) {
    return "contract_version must be semver.";
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
  if (typeof body.query !== "string" || body.query.length === 0) {
    return "query is required.";
  }
  if (hasProperty(body, "query_embedding") && !finiteNumberArray(body.query_embedding)) {
    return "query_embedding must be a non-empty finite number array with at most 4096 values.";
  }
  if (!idArray(body.knowledge_scope_ids)) {
    return "knowledge_scope_ids must be an array of ids.";
  }
  if (!idArray(body.memory_scope_ids)) {
    return "memory_scope_ids must be an array of ids.";
  }
  if (typeof body.top_k !== "number" || body.top_k < 1 || body.top_k > 20) {
    return "top_k must be between 1 and 20.";
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

function parseStringArray(rawValue: string, field: string): string[] {
  const value: unknown = JSON.parse(rawValue);
  if (!stringArray(value)) {
    throw new Error(`Invalid registry metadata array: ${field}`);
  }
  return value;
}

function nowIso(): string {
  return new Date().toISOString();
}

function versionPath(version: string): string {
  return `v${version}`;
}

function versionId(version: string): string {
  return version.replaceAll(".", "-");
}

function r2Uri(bucketName: string, key: string): string {
  return `r2://${bucketName}/${key}`;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function normalizeKnowledgeContent(content: string): string {
  return content.replaceAll("\r\n", "\n").trim() + "\n";
}

function chunkContent(content: string, maxChars = 1200): string[] {
  const chunks: string[] = [];
  let remaining = content.trim();
  while (remaining.length > 0) {
    const chunk = remaining.slice(0, maxChars).trim();
    chunks.push(chunk);
    remaining = remaining.slice(maxChars).trim();
  }
  return chunks.length > 0 ? chunks : [content.trim()];
}

async function putJson(bucket: R2Bucket, key: string, value: unknown): Promise<void> {
  await bucket.put(key, JSON.stringify(value, null, 2), {
    httpMetadata: {
      contentType: "application/json; charset=utf-8",
    },
  });
}

function parseScoreModifiers(rawValue: string): ScoreModifier[] {
  const value: unknown = JSON.parse(rawValue);
  if (!Array.isArray(value)) {
    throw new Error("Invalid registry metadata array: score_modifiers");
  }

  return value.map((item) => {
    if (
      !isObject(item) ||
      typeof item.signal !== "string" ||
      typeof item.weight !== "number" ||
      typeof item.reason !== "string"
    ) {
      throw new Error("Invalid score modifier metadata.");
    }

    return {
      signal: item.signal,
      weight: item.weight,
      reason: item.reason,
    };
  });
}

function parseRegistryModule(row: RegistryModuleRow): RegistryModule {
  if (!isModuleKind(row.kind)) {
    throw new Error(`Invalid module kind in registry: ${row.kind}`);
  }

  return {
    id: row.id,
    name: row.name,
    kind: row.kind,
    moduleVersionId: row.module_version_id,
    version: row.version,
    description: row.description,
    capabilityClass: row.capability_class,
    domainTags: parseStringArray(row.domain_tags_json, "domain_tags"),
    taskTypes: parseStringArray(row.task_types_json, "task_types"),
    riskLevels: parseStringArray(row.risk_levels_json, "risk_levels"),
    taskDomains: parseStringArray(row.task_domains_json, "task_domains"),
    requiredInputs: parseStringArray(row.required_inputs_json, "required_inputs"),
    phrases: parseStringArray(row.phrases_json, "phrases"),
    negativePhrases: parseStringArray(row.negative_phrases_json, "negative_phrases"),
    triggers: parseStringArray(row.triggers_json, "triggers"),
    inputs: parseStringArray(row.inputs_json, "inputs"),
    outputs: parseStringArray(row.outputs_json, "outputs"),
    baseScore: row.selection_base_score,
    scoreModifiers: parseScoreModifiers(row.score_modifiers_json),
    requiresAllPolicies: row.requires_all_policies === 1,
  };
}

async function registryVersion(env: Env): Promise<string> {
  try {
    const version = await env.SCAS_CONFIG.get("registry:version");
    return isSemver(version) ? version : DEFAULT_REGISTRY_VERSION;
  } catch {
    return DEFAULT_REGISTRY_VERSION;
  }
}

async function loadRegistryModules(env: Env): Promise<RegistryModule[]> {
  const result = await env.SCAS_CONTROL_DB.prepare(
    `
    SELECT
      m.id,
      m.name,
      m.kind,
      mv.id AS module_version_id,
      mv.version,
      mv.selection_base_score,
      msm.description,
      msm.capability_class,
      msm.domain_tags_json,
      msm.task_types_json,
      msm.risk_levels_json,
      msm.task_domains_json,
      msm.required_inputs_json,
      msm.phrases_json,
      msm.negative_phrases_json,
      msm.triggers_json,
      msm.inputs_json,
      msm.outputs_json,
      msm.score_modifiers_json,
      msm.requires_all_policies
    FROM modules AS m
    INNER JOIN module_versions AS mv
      ON mv.id = m.current_version_id
      AND mv.module_id = m.id
    INNER JOIN module_selection_metadata AS msm
      ON msm.module_version_id = mv.id
    WHERE m.status = 'active'
    ORDER BY m.name ASC
    `,
  ).all<RegistryModuleRow>();

  return (result.results ?? []).map(parseRegistryModule);
}

async function loadDependencies(env: Env): Promise<ModuleDependency[]> {
  const result = await env.SCAS_CONTROL_DB.prepare(
    `
    SELECT
      module_version_id,
      dependency_id,
      dependency_kind,
      is_required
    FROM module_dependencies
    ORDER BY module_version_id ASC, dependency_id ASC
    `,
  ).all<DependencyRow>();

  return (result.results ?? []).map((row) => {
    if (!isModuleKind(row.dependency_kind)) {
      throw new Error(`Invalid dependency kind in registry: ${row.dependency_kind}`);
    }

    return {
      moduleVersionId: row.module_version_id,
      dependencyId: row.dependency_id,
      dependencyKind: row.dependency_kind,
      isRequired: row.is_required === 1,
    };
  });
}

async function loadPolicyBindings(env: Env): Promise<PolicyBinding[]> {
  const result = await env.SCAS_CONTROL_DB.prepare(
    `
    SELECT
      policy_id,
      target_kind,
      target_id,
      effect,
      priority
    FROM policy_bindings
    ORDER BY priority DESC
    `,
  ).all<PolicyBindingRow>();

  return (result.results ?? []).flatMap((row) => {
    if (row.effect !== "allow" && row.effect !== "deny") {
      return [];
    }

    return [
      {
        policyId: row.policy_id,
        targetKind: row.target_kind,
        targetId: row.target_id,
        effect: row.effect,
        priority: row.priority,
      },
    ];
  });
}

async function loadScopeBindings(
  env: Env,
  principal: CompositionRequest["principal"],
): Promise<ScopeBinding[]> {
  const result = await env.SCAS_CONTROL_DB.prepare(
    `
    SELECT
      scope_id,
      scope_kind,
      policy_id,
      effect
    FROM scope_bindings
    WHERE principal_kind = ?
      AND principal_id = ?
    ORDER BY scope_kind ASC, scope_id ASC
    `,
  )
    .bind(principal.kind, principal.id)
    .all<ScopeBindingRow>();

  return (result.results ?? []).flatMap((row) => {
    if (!isModuleKind(row.scope_kind) || !SCOPE_KINDS.has(row.scope_kind)) {
      return [];
    }
    if (row.effect !== "allow" && row.effect !== "deny") {
      return [];
    }

    return [
      {
        scopeId: row.scope_id,
        scopeKind: row.scope_kind,
        policyId: row.policy_id,
        effect: row.effect,
      },
    ];
  });
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function intersects(left: Iterable<string>, right: Iterable<string>): string[] {
  const rightValues = new Set(Array.from(right, normalize));
  return Array.from(left).filter((value) => rightValues.has(normalize(value)));
}

function includesAll(values: Iterable<string>, requiredValues: Iterable<string>): boolean {
  const valueSet = new Set(Array.from(values, normalize));
  return Array.from(requiredValues).every((value) => valueSet.has(normalize(value)));
}

function normalizedTaskText(request: CompositionRequest): string {
  return normalize([request.task.objective, ...request.task.signals.constraints].join(" "));
}

function signalMatches(
  signal: string,
  module: RegistryModule,
  request: CompositionRequest,
): boolean {
  const separatorIndex = signal.indexOf(":");
  if (separatorIndex < 0) {
    return false;
  }

  const prefix = signal.slice(0, separatorIndex);
  const value = signal.slice(separatorIndex + 1);
  const normalizedValue = normalize(value);
  const domainValues = [...module.domainTags, ...module.taskDomains];

  if (prefix === "task_type") {
    return normalize(request.task.type) === normalizedValue;
  }
  if (prefix === "risk_level") {
    return normalize(request.task.risk_level) === normalizedValue;
  }
  if (prefix === "domain") {
    return (
      domainValues.map(normalize).includes(normalizedValue) &&
      request.task.signals.domain_tags.map(normalize).includes(normalizedValue)
    );
  }
  if (prefix === "input") {
    return request.task.signals.available_inputs.map(normalize).includes(normalizedValue);
  }
  if (prefix === "capability_class") {
    return (
      normalize(module.capabilityClass) === normalizedValue ||
      request.task.signals.capability_hints.map(normalize).includes(normalizedValue)
    );
  }
  if (prefix === "phrase" || prefix === "trigger" || prefix === "constraint") {
    return normalizedTaskText(request).includes(normalizedValue);
  }

  return false;
}

function scoreModule(module: RegistryModule, request: CompositionRequest): ScoredModule | null {
  if (!includesAll(request.task.signals.available_inputs, module.requiredInputs)) {
    return null;
  }

  const matchedSignals = new Set<string>();
  const negativeSignals = new Set<string>();
  const reasons: string[] = [];

  if (module.taskTypes.map(normalize).includes(normalize(request.task.type))) {
    matchedSignals.add(`task_type:${request.task.type}`);
  }
  if (module.riskLevels.map(normalize).includes(normalize(request.task.risk_level))) {
    matchedSignals.add(`risk_level:${request.task.risk_level}`);
  }

  for (const domain of intersects(
    [...module.domainTags, ...module.taskDomains],
    request.task.signals.domain_tags,
  )) {
    matchedSignals.add(`domain:${domain}`);
  }

  for (const inputName of intersects(module.requiredInputs, request.task.signals.available_inputs)) {
    matchedSignals.add(`input:${inputName}`);
  }

  if (
    request.task.signals.capability_hints.map(normalize).includes(normalize(module.capabilityClass))
  ) {
    matchedSignals.add(`capability_class:${module.capabilityClass}`);
  }

  if (matchedSignals.size === 0) {
    return null;
  }

  let score = module.baseScore;
  for (const modifier of module.scoreModifiers) {
    if (signalMatches(modifier.signal, module, request)) {
      score += modifier.weight;
      reasons.push(modifier.reason);
      if (modifier.weight < 0) {
        negativeSignals.add(modifier.signal);
      } else {
        matchedSignals.add(modifier.signal);
      }
    }
  }

  const taskText = normalizedTaskText(request);
  for (const phrase of module.negativePhrases) {
    if (taskText.includes(normalize(phrase))) {
      negativeSignals.add(`phrase:${phrase}`);
    }
  }

  const clampedScore = Math.max(0, Math.min(1, score));
  const reason =
    reasons.length > 0
      ? reasons.join(" ")
      : `Matched ${Array.from(matchedSignals).sort().join(", ")}.`;

  return {
    module,
    score: Math.round(clampedScore * 10000) / 10000,
    matchedSignals: Array.from(matchedSignals).sort(),
    negativeSignals: Array.from(negativeSignals).sort(),
    reasons: [reason],
  };
}

function moduleIdentity(module: RegistryModule): ModuleIdentity {
  return {
    id: module.id,
    name: module.name,
    kind: module.kind,
    version: module.version,
  };
}

function moduleReference(module: RegistryModule, score: number, reason: string): ModuleReference {
  return {
    ...moduleIdentity(module),
    score,
    reason,
  };
}

function dedupeReferences(references: ModuleReference[]): ModuleReference[] {
  const byId = new Map<string, ModuleReference>();
  for (const reference of references) {
    const existing = byId.get(reference.id);
    if (existing === undefined || reference.score > existing.score) {
      byId.set(reference.id, reference);
    }
  }

  return Array.from(byId.values()).sort(
    (left, right) => right.score - left.score || left.name.localeCompare(right.name),
  );
}

function dependenciesByVersionId(
  dependencies: ModuleDependency[],
): Map<string, ModuleDependency[]> {
  const byVersionId = new Map<string, ModuleDependency[]>();
  for (const dependency of dependencies) {
    const existing = byVersionId.get(dependency.moduleVersionId) ?? [];
    existing.push(dependency);
    byVersionId.set(dependency.moduleVersionId, existing);
  }
  return byVersionId;
}

function policyDecisionForModule(
  module: RegistryModule,
  dependencies: ModuleDependency[],
  policyBindings: PolicyBinding[],
): PolicyDecision {
  const directBindings = policyBindings.filter(
    (binding) => binding.targetKind === "module" && binding.targetId === module.id,
  );
  const denied = directBindings.find((binding) => binding.effect === "deny");
  if (denied !== undefined) {
    return {
      module: moduleIdentity(module),
      effect: "deny",
      reasons: [`Policy ${denied.policyId} denies module ${module.name}.`],
    };
  }

  const requiredPolicyIds = dependencies
    .filter((dependency) => dependency.dependencyKind === "policy" && dependency.isRequired)
    .map((dependency) => dependency.dependencyId);

  if (module.requiresAllPolicies) {
    const allowedPolicyIds = new Set(
      directBindings
        .filter((binding) => binding.effect === "allow")
        .map((binding) => binding.policyId),
    );
    const missingPolicyIds = requiredPolicyIds.filter((policyId) => !allowedPolicyIds.has(policyId));

    if (missingPolicyIds.length > 0) {
      return {
        module: moduleIdentity(module),
        effect: "needs_clarification",
        reasons: [`Missing required policy allows: ${missingPolicyIds.join(", ")}.`],
      };
    }
  }

  return {
    module: moduleIdentity(module),
    effect: "allow",
    reasons: ["Required policies are allowed for the module."],
  };
}

function scopeBindingAllows(scopeId: string, scopeBindings: ScopeBinding[]): boolean {
  const bindings = scopeBindings.filter((binding) => binding.scopeId === scopeId);
  if (bindings.some((binding) => binding.effect === "deny")) {
    return false;
  }
  return bindings.some((binding) => binding.effect === "allow");
}

function validateGraph(
  selectedModules: RegistryModule[],
  modulesById: Map<string, RegistryModule>,
  dependenciesByVersion: Map<string, ModuleDependency[]>,
  scopeBindings: ScopeBinding[],
): GraphValidation {
  const reachableIds = new Set<string>();
  const errors: string[] = [];
  const visiting = new Set<string>();

  function visit(module: RegistryModule, path: string[]): void {
    if (visiting.has(module.id)) {
      errors.push(`circular dependency: ${[...path, module.name].join(" -> ")}`);
      return;
    }

    if (reachableIds.has(module.id)) {
      return;
    }

    visiting.add(module.id);
    reachableIds.add(module.id);

    const dependencies = dependenciesByVersion.get(module.moduleVersionId) ?? [];
    for (const dependency of dependencies) {
      const dependencyModule = modulesById.get(dependency.dependencyId);
      if (dependencyModule === undefined) {
        errors.push(`${module.name} references missing ${dependency.dependencyKind}.`);
        continue;
      }
      if (dependencyModule.kind !== dependency.dependencyKind) {
        errors.push(
          `${module.name} references ${dependencyModule.name} as ${dependency.dependencyKind}, got ${dependencyModule.kind}.`,
        );
      }
      if (SCOPE_KINDS.has(dependencyModule.kind) && !scopeBindingAllows(dependencyModule.id, scopeBindings)) {
        errors.push(`${dependencyModule.name} is not allowed for the principal.`);
      }

      visit(dependencyModule, [...path, module.name]);
    }

    visiting.delete(module.id);
  }

  for (const module of selectedModules) {
    visit(module, []);
  }

  const reachableModules = Array.from(reachableIds)
    .map((id) => modulesById.get(id))
    .filter((module): module is RegistryModule => module !== undefined)
    .map(moduleIdentity)
    .sort((left, right) => left.name.localeCompare(right.name));

  return {
    is_valid: errors.length === 0,
    errors: Array.from(new Set(errors)),
    reachable_modules: reachableModules,
  };
}

function referencesForDependencies(
  dependencies: ModuleDependency[],
  modulesById: Map<string, RegistryModule>,
  scoredByModuleId: Map<string, ScoredModule>,
  kind: ModuleKind,
  reason: string,
): ModuleReference[] {
  return dependencies.flatMap((dependency) => {
    if (dependency.dependencyKind !== kind) {
      return [];
    }

    const module = modulesById.get(dependency.dependencyId);
    if (module === undefined) {
      return [];
    }

    const scored = scoredByModuleId.get(module.id);
    return [moduleReference(module, scored?.score ?? module.baseScore, reason)];
  });
}

async function compositionContextResponse(
  env: Env,
  request: CompositionRequest,
): Promise<CompositionContextResponse> {
  const [version, modules, dependencies, policyBindings, scopeBindings] = await Promise.all([
    registryVersion(env),
    loadRegistryModules(env),
    loadDependencies(env),
    loadPolicyBindings(env),
    loadScopeBindings(env, request.principal),
  ]);

  const modulesById = new Map(modules.map((module) => [module.id, module]));
  const dependenciesByVersion = dependenciesByVersionId(dependencies);
  const scoredModules = modules
    .map((module) => scoreModule(module, request))
    .filter((module): module is ScoredModule => module !== null);
  const scoredByModuleId = new Map(
    scoredModules.map((scoredModule) => [scoredModule.module.id, scoredModule]),
  );
  const candidateScores = scoredModules.filter((scoredModule) =>
    CANDIDATE_KINDS.has(scoredModule.module.kind),
  );
  const policyDecisions = candidateScores.map((scoredModule) =>
    policyDecisionForModule(
      scoredModule.module,
      dependenciesByVersion.get(scoredModule.module.moduleVersionId) ?? [],
      policyBindings,
    ),
  );
  const allowedCandidateIds = new Set(
    policyDecisions
      .filter((decision) => decision.effect === "allow")
      .map((decision) => decision.module.id),
  );
  const allowedCandidates = candidateScores.filter((scoredModule) =>
    allowedCandidateIds.has(scoredModule.module.id),
  );
  const selectedCandidateDependencies = allowedCandidates.flatMap(
    (scoredModule) => dependenciesByVersion.get(scoredModule.module.moduleVersionId) ?? [],
  );

  const candidateModules = dedupeReferences(
    allowedCandidates.map((scoredModule) =>
      moduleReference(
        scoredModule.module,
        scoredModule.score,
        scoredModule.reasons.join(" "),
      ),
    ),
  );
  const applicablePolicies = dedupeReferences(
    referencesForDependencies(
      selectedCandidateDependencies,
      modulesById,
      scoredByModuleId,
      "policy",
      "Required by selected module.",
    ),
  );
  const validationRequirements = dedupeReferences(
    referencesForDependencies(
      selectedCandidateDependencies,
      modulesById,
      scoredByModuleId,
      "validator",
      "Required by selected module.",
    ),
  );
  const allowedScopes = dedupeReferences(
    scoredModules
      .filter((scoredModule) => SCOPE_KINDS.has(scoredModule.module.kind))
      .filter((scoredModule) => scopeBindingAllows(scoredModule.module.id, scopeBindings))
      .map((scoredModule) =>
        moduleReference(
          scoredModule.module,
          scoredModule.score,
          "Allowed for principal by scope binding.",
        ),
      ),
  );
  const graphValidation = validateGraph(
    allowedCandidates.map((scoredModule) => scoredModule.module),
    modulesById,
    dependenciesByVersion,
    scopeBindings,
  );
  const compositionStatus =
    candidateScores.length === 0 || allowedCandidates.length === 0 ? "denied" : "ready";

  return {
    contract_version: CONTRACT_VERSION,
    registry_version: version,
    composition_status: graphValidation.is_valid ? compositionStatus : "denied",
    candidate_modules: candidateModules,
    applicable_policies: applicablePolicies,
    allowed_knowledge_scopes: allowedScopes.filter(
      (reference) => reference.kind === "knowledge_scope",
    ),
    allowed_data_scopes: allowedScopes.filter((reference) => reference.kind === "data_scope"),
    allowed_memory_scopes: allowedScopes.filter((reference) => reference.kind === "memory_scope"),
    validation_requirements: validationRequirements,
    policy_decisions: policyDecisions,
    graph_validation: graphValidation,
  };
}

async function handleCompositionContext(request: Request, env: Env): Promise<Response> {
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

  try {
    return jsonResponse(await compositionContextResponse(env, body as CompositionRequest));
  } catch {
    return errorResponse(503, "registry_unavailable", "Registry metadata is unavailable.");
  }
}

async function readValidatedJson<T>(
  request: Request,
  validate: (body: unknown) => string | null,
  invalidRequestCode = "invalid_ingestion_request",
): Promise<{ body: T } | { response: Response }> {
  if (request.method !== "POST") {
    return { response: errorResponse(405, "method_not_allowed", "Use POST for this endpoint.") };
  }
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return { response: errorResponse(415, "unsupported_media_type", "Request body must be JSON.") };
  }

  let body: unknown;
  try {
    body = await readJson(request);
  } catch (error) {
    if (error instanceof Error && error.message === "request_body_too_large") {
      return {
        response: errorResponse(413, "request_body_too_large", "Request body exceeds 64 KiB."),
      };
    }
    return { response: errorResponse(400, "invalid_json", "Request body must be valid JSON.") };
  }

  const validationError = validate(body);
  if (validationError !== null) {
    return { response: errorResponse(400, invalidRequestCode, validationError) };
  }

  return { body: body as T };
}

async function handleKnowledgeIngest(request: Request, env: Env): Promise<Response> {
  const parsed = await readValidatedJson<KnowledgeIngestRequest>(
    request,
    validateKnowledgeIngestRequest,
  );
  if ("response" in parsed) {
    return parsed.response;
  }

  const body = parsed.body;
  const timestamp = nowIso();
  const bucketName = `scas-knowledge-${env.ENVIRONMENT}`;
  const baseKey = `knowledge/${body.source.id}/${body.document.id}/${versionPath(body.document.version)}`;
  const normalized = normalizeKnowledgeContent(body.document.content);
  const chunks = chunkContent(normalized);
  const checksum = await sha256Hex(normalized);
  const normalizedKey = `${baseKey}/normalized.md`;
  const chunksKey = `${baseKey}/chunks.jsonl`;
  const manifestKey = `${baseKey}/manifest.json`;
  const chunkRows = chunks.map((chunk, index) => ({
    id: `chunk-${body.document.id}-${index}`,
    document_id: body.document.id,
    chunk_index: index,
    content_uri: r2Uri(bucketName, `${baseKey}/chunks/${index}.json`),
    vector_id: `vec-${body.document.id}-${index}`,
    scope_id: body.document.scope_id,
    token_count: Math.max(1, Math.ceil(chunk.length / 4)),
    content: chunk,
  }));

  await env.SCAS_KNOWLEDGE_BUCKET.put(normalizedKey, normalized, {
    httpMetadata: {
      contentType: "text/markdown; charset=utf-8",
    },
  });
  await env.SCAS_KNOWLEDGE_BUCKET.put(
    chunksKey,
    chunkRows.map((chunk) => JSON.stringify(chunk)).join("\n") + "\n",
    {
      httpMetadata: {
        contentType: "application/x-ndjson; charset=utf-8",
      },
    },
  );
  await putJson(env.SCAS_KNOWLEDGE_BUCKET, manifestKey, {
    source_id: body.source.id,
    document_id: body.document.id,
    version: body.document.version,
    checksum,
    normalized_uri: r2Uri(bucketName, normalizedKey),
    chunks_uri: r2Uri(bucketName, chunksKey),
    chunk_count: chunkRows.length,
  });
  for (const chunk of chunkRows) {
    await putJson(env.SCAS_KNOWLEDGE_BUCKET, `${baseKey}/chunks/${chunk.chunk_index}.json`, {
      id: chunk.id,
      document_id: chunk.document_id,
      chunk_index: chunk.chunk_index,
      content: chunk.content,
    });
  }

  await env.SCAS_CONTROL_DB.batch([
    env.SCAS_CONTROL_DB.prepare(
      `
      INSERT OR REPLACE INTO knowledge_sources (
        id, name, source_type, uri, owner, sensitivity, status
      )
      VALUES (?, ?, ?, ?, ?, ?, 'active')
      `,
    ).bind(
      body.source.id,
      body.source.name,
      body.source.source_type,
      body.source.uri,
      body.source.owner,
      body.source.sensitivity,
    ),
    env.SCAS_CONTROL_DB.prepare(
      `
      INSERT OR REPLACE INTO knowledge_documents (
        id, source_id, version, content_uri, manifest_uri, checksum, status
      )
      VALUES (?, ?, ?, ?, ?, ?, 'active')
      `,
    ).bind(
      body.document.id,
      body.source.id,
      body.document.version,
      r2Uri(bucketName, normalizedKey),
      r2Uri(bucketName, manifestKey),
      `sha256:${checksum}`,
    ),
  ]);
  await env.SCAS_CONTROL_DB.prepare("DELETE FROM knowledge_chunks WHERE document_id = ?")
    .bind(body.document.id)
    .run();
  for (const chunk of chunkRows) {
    await env.SCAS_CONTROL_DB.prepare(
      `
      INSERT INTO knowledge_chunks (
        id, document_id, chunk_index, content_uri, vector_id, scope_id, token_count
      )
      VALUES (?, ?, ?, ?, ?, ?, ?)
      `,
    )
      .bind(
        chunk.id,
        chunk.document_id,
        chunk.chunk_index,
        chunk.content_uri,
        chunk.vector_id,
        chunk.scope_id,
        chunk.token_count,
      )
      .run();
  }
  await writeIngestionAudit(
    env,
    "knowledge_import",
    body.source.uri,
    "knowledge_document",
    body.document.id,
    timestamp,
  );

  return jsonResponse({
    status: "succeeded",
    document_id: body.document.id,
    content_uri: r2Uri(bucketName, normalizedKey),
    manifest_uri: r2Uri(bucketName, manifestKey),
    chunk_count: chunkRows.length,
    vector_status: "embedding_update_queued",
  });
}

async function handleMemoryIngest(request: Request, env: Env): Promise<Response> {
  const parsed = await readValidatedJson<MemoryIngestRequest>(
    request,
    validateMemoryIngestRequest,
  );
  if ("response" in parsed) {
    return parsed.response;
  }

  const body = parsed.body;
  const timestamp = nowIso();
  const bucketName = `scas-memory-${env.ENVIRONMENT}`;
  const memoryScope = await env.SCAS_CONTROL_DB.prepare(
    `
    SELECT id
    FROM modules
    WHERE id = ?
      AND kind = 'memory_scope'
      AND status = 'active'
    LIMIT 1
    `,
  )
    .bind(body.memory.memory_scope_id)
    .first();
  if (memoryScope === null) {
    return errorResponse(
      403,
      "memory_scope_not_allowed",
      "memory.memory_scope_id must reference an active memory_scope module.",
    );
  }
  const baseKey = `memory/${body.memory.memory_scope_id}/${body.memory.id}/${versionPath(body.memory.version)}`;
  const contentKey = `${baseKey}/content.json`;
  const manifestKey = `${baseKey}/manifest.json`;
  await putJson(env.SCAS_MEMORY_BUCKET, contentKey, body.memory.content);
  await putJson(env.SCAS_MEMORY_BUCKET, manifestKey, {
    memory_id: body.memory.id,
    memory_scope_id: body.memory.memory_scope_id,
    version: body.memory.version,
    source_run_id: body.memory.source_run_id,
    source_profile_id: body.memory.source_profile_id,
    sensitivity: body.memory.sensitivity,
    retention_policy: body.memory.retention_policy,
    content_uri: r2Uri(bucketName, contentKey),
  });

  await env.SCAS_CONTROL_DB.prepare(
    `
    INSERT OR REPLACE INTO memory_records (
      id, memory_scope_id, version, content_uri, manifest_uri, source_run_id,
      source_profile_id, sensitivity, retention_policy, status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
    `,
  )
    .bind(
      body.memory.id,
      body.memory.memory_scope_id,
      body.memory.version,
      r2Uri(bucketName, contentKey),
      r2Uri(bucketName, manifestKey),
      body.memory.source_run_id,
      body.memory.source_profile_id,
      body.memory.sensitivity,
      body.memory.retention_policy,
    )
    .run();
  await writeIngestionAudit(
    env,
    "memory_import",
    r2Uri(bucketName, contentKey),
    "memory_record",
    body.memory.id,
    timestamp,
  );

  return jsonResponse({
    status: "succeeded",
    memory_id: body.memory.id,
    content_uri: r2Uri(bucketName, contentKey),
    manifest_uri: r2Uri(bucketName, manifestKey),
    vector_status: "embedding_update_queued",
  });
}

async function writeIngestionAudit(
  env: Env,
  jobType: "knowledge_import" | "memory_import",
  sourceUri: string,
  targetKind: "knowledge_document" | "memory_record",
  targetId: string,
  timestamp: string,
): Promise<void> {
  const jobId = `job-${targetId}-${versionId(timestamp.slice(0, 10))}`;
  const auditId = `audit-${targetId}-${versionId(timestamp.slice(0, 10))}`;
  await env.SCAS_CONTROL_DB.batch([
    env.SCAS_CONTROL_DB.prepare(
      `
      INSERT OR REPLACE INTO ingestion_jobs (
        id, job_type, status, source_uri, target_kind, target_id, attempts,
        created_at, updated_at
      )
      VALUES (?, ?, 'succeeded', ?, ?, ?, 1, ?, ?)
      `,
    ).bind(jobId, jobType, sourceUri, targetKind, targetId, timestamp, timestamp),
    env.SCAS_CONTROL_DB.prepare(
      `
      INSERT OR REPLACE INTO audit_events (
        id, event_type, actor_id, target_kind, target_id, created_at,
        retention_policy, archive_after, archive_uri
      )
      VALUES (?, ?, 'control-api', ?, ?, ?, 'control-plane-audit-90d', ?, NULL)
      `,
    ).bind(
      auditId,
      `${jobType}_succeeded`,
      targetKind,
      targetId,
      timestamp,
      new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString(),
    ),
  ]);
}

async function handleRetrievalContext(request: Request, env: Env): Promise<Response> {
  const parsed = await readValidatedJson<RetrievalRequest>(
    request,
    validateRetrievalRequest,
    "invalid_retrieval_request",
  );
  if ("response" in parsed) {
    return parsed.response;
  }
  const body = parsed.body;
  const scopeBindings = await loadScopeBindings(env, body.principal);
  const allowedKnowledgeScopes = body.knowledge_scope_ids.filter((scopeId) =>
    scopeBindingAllows(scopeId, scopeBindings),
  );
  const allowedMemoryScopes = body.memory_scope_ids.filter((scopeId) =>
    scopeBindingAllows(scopeId, scopeBindings),
  );
  const knowledgeChunks: KnowledgeRetrievalRow[] = [];
  for (const scopeId of allowedKnowledgeScopes) {
    const result = await env.SCAS_CONTROL_DB.prepare(
      `
      SELECT
        kc.id,
        kc.document_id,
        kc.chunk_index,
        kc.content_uri,
        kc.vector_id,
        kc.scope_id,
        kc.token_count
      FROM knowledge_chunks AS kc
      INNER JOIN knowledge_documents AS kd
        ON kd.id = kc.document_id
      WHERE kc.scope_id = ?
        AND kd.status = 'active'
      ORDER BY kc.document_id ASC, kc.chunk_index ASC
      LIMIT ?
      `,
    )
      .bind(scopeId, body.top_k)
      .all<KnowledgeRetrievalRow>();
    knowledgeChunks.push(...(result.results ?? []));
  }
  const memoryRecords: MemoryRetrievalRow[] = [];
  for (const scopeId of allowedMemoryScopes) {
    const result = await env.SCAS_CONTROL_DB.prepare(
      `
      SELECT
        id,
        memory_scope_id,
        version,
        content_uri,
        manifest_uri,
        source_run_id,
        source_profile_id,
        sensitivity,
        retention_policy,
        status
      FROM memory_records
      WHERE memory_scope_id = ?
        AND status = 'active'
      ORDER BY id ASC
      LIMIT ?
      `,
    )
      .bind(scopeId, body.top_k)
      .all<Omit<MemoryRetrievalRow, "vector_id">>();
    memoryRecords.push(
      ...(result.results ?? []).map((row) => ({
        ...row,
        vector_id: `vec-${row.id}`,
      })),
    );
  }
  const boundedKnowledgeChunks = knowledgeChunks.slice(0, body.top_k);
  const boundedMemoryRecords = memoryRecords.slice(0, body.top_k);
  const knowledgeVectorIds = new Set(boundedKnowledgeChunks.map((chunk) => chunk.vector_id));
  const memoryVectorIds = new Set(boundedMemoryRecords.map((memory) => memory.vector_id));
  const vectorize = {
    status:
      body.query_embedding === undefined
        ? "d1_prefilter_ready"
        : "vectorize_query_post_validated",
    knowledge_index: "scas-knowledge-dev",
    memory_index: "scas-memory-dev",
    bindings: {
      knowledge: Boolean(env.SCAS_KNOWLEDGE_INDEX),
      memory: Boolean(env.SCAS_MEMORY_INDEX),
    },
    note: "D1 computes allowed IDs before Vectorize semantic lookup and post-validates Vectorize matches.",
  };
  const vectorizeMatches =
    body.query_embedding === undefined
      ? {
          knowledge: [],
          memory: [],
        }
      : await queryVectorize(
          env,
          body.query_embedding,
          allowedKnowledgeScopes,
          allowedMemoryScopes,
          knowledgeVectorIds,
          memoryVectorIds,
          body.top_k,
        );

  return jsonResponse({
    contract_version: CONTRACT_VERSION,
    retrieval_status: "ready",
    query: body.query,
    vectorize,
    allowed_knowledge_scope_ids: allowedKnowledgeScopes,
    allowed_memory_scope_ids: allowedMemoryScopes,
    knowledge_chunks: boundedKnowledgeChunks,
    memory_records: boundedMemoryRecords,
    vectorize_matches: vectorizeMatches,
  });
}

async function queryVectorize(
  env: Env,
  embedding: number[],
  allowedKnowledgeScopes: string[],
  allowedMemoryScopes: string[],
  allowedKnowledgeVectorIds: Set<string>,
  allowedMemoryVectorIds: Set<string>,
  topK: number,
): Promise<{ knowledge: VectorizeMatch[]; memory: VectorizeMatch[] }> {
  const [knowledgeMatches, memoryMatches] = await Promise.all([
    allowedKnowledgeScopes.length === 0
      ? Promise.resolve({ matches: [] })
      : env.SCAS_KNOWLEDGE_INDEX.query(embedding, {
          topK,
          returnMetadata: "indexed",
          filter: {
            scope_id: {
              $in: allowedKnowledgeScopes,
            },
          },
        }),
    allowedMemoryScopes.length === 0
      ? Promise.resolve({ matches: [] })
      : env.SCAS_MEMORY_INDEX.query(embedding, {
          topK,
          returnMetadata: "indexed",
          filter: {
            memory_scope_id: {
              $in: allowedMemoryScopes,
            },
          },
        }),
  ]);

  return {
    knowledge: knowledgeMatches.matches.filter((match) => allowedKnowledgeVectorIds.has(match.id)),
    memory: memoryMatches.matches.filter((match) => allowedMemoryVectorIds.has(match.id)),
  };
}

function aiGatewayEnv(env: Env): {
  accountId: string;
  gatewayId: string;
  openAiApiKey?: string;
} {
  const extended = env as Env & {
    AI_GATEWAY_ACCOUNT_ID?: string;
    AI_GATEWAY_ID?: string;
    OPENAI_API_KEY?: string;
  };
  return {
    accountId: extended.AI_GATEWAY_ACCOUNT_ID ?? "",
    gatewayId: extended.AI_GATEWAY_ID ?? "default",
    openAiApiKey: extended.OPENAI_API_KEY,
  };
}

function aiGatewayOpenAiChatUrl(env: Env): string {
  const gateway = aiGatewayEnv(env);
  return `https://gateway.ai.cloudflare.com/v1/${gateway.accountId}/${gateway.gatewayId}/openai/chat/completions`;
}

async function handleAiGatewayOpenAiChat(request: Request, env: Env): Promise<Response> {
  if (request.method !== "POST") {
    return errorResponse(405, "method_not_allowed", "Use POST for AI Gateway routing.");
  }
  const gateway = aiGatewayEnv(env);
  if (
    gateway.accountId.length === 0 ||
    gateway.accountId === "unset" ||
    gateway.openAiApiKey === undefined ||
    gateway.openAiApiKey.length === 0
  ) {
    return errorResponse(
      503,
      "ai_gateway_not_configured",
      "AI Gateway account and OPENAI_API_KEY Worker secret must be configured.",
    );
  }

  let body: unknown;
  try {
    body = await readJson(request);
  } catch {
    return errorResponse(400, "invalid_json", "Request body must be valid JSON.");
  }
  if (!isObject(body)) {
    return errorResponse(400, "invalid_ai_gateway_request", "Request body must be a JSON object.");
  }

  let response: Response;
  try {
    response = await fetch(aiGatewayOpenAiChatUrl(env), {
      method: "POST",
      headers: {
        "authorization": `Bearer ${gateway.openAiApiKey}`,
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
    });
  } catch {
    return errorResponse(502, "ai_gateway_unavailable", "AI Gateway upstream request failed.");
  }

  return new Response(response.body, {
    status: response.status,
    headers: {
      "content-type": response.headers.get("content-type") ?? "application/json",
    },
  });
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
      return handleCompositionContext(request, env);
    }

    if (url.pathname === "/knowledge/ingest") {
      return handleKnowledgeIngest(request, env);
    }

    if (url.pathname === "/memory/ingest") {
      return handleMemoryIngest(request, env);
    }

    if (url.pathname === "/retrieval/context") {
      return handleRetrievalContext(request, env);
    }

    if (url.pathname === "/ai-gateway/openai/chat/completions") {
      return handleAiGatewayOpenAiChat(request, env);
    }

    return errorResponse(404, "not_found", "Endpoint not found.");
  },
} satisfies ExportedHandler<Env>;
