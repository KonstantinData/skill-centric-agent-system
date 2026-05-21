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

  if (!idArray(body.task.signals.available_inputs)) {
    return "task.signals.available_inputs must be an array of ids.";
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

function parseStringArray(rawValue: string, field: string): string[] {
  const value: unknown = JSON.parse(rawValue);
  if (!stringArray(value)) {
    throw new Error(`Invalid registry metadata array: ${field}`);
  }
  return value;
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
    candidateScores.length > 0 && allowedCandidates.length === 0 ? "denied" : "ready";

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

    return errorResponse(404, "not_found", "Endpoint not found.");
  },
} satisfies ExportedHandler<Env>;
