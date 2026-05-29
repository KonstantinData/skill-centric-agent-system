# ADR-0004: Cloudflare Control Plane, Hetzner Runtime Plane, And Memory Feedback Boundary

## Status

Accepted

## Date

2026-05-21

## Context

The system separates stable composition contracts from task-local execution. That same boundary must exist in infrastructure:

- Cloudflare should store non-runtime control data: registries, knowledge, policies, scope metadata, long-term memory, semantic indexes, and ingestion state.
- Hetzner should store runtime results: runs, steps, tool outputs, execution traces, validation results, and artifacts.
- Runtime work can produce useful long-term memory, but raw runtime artifacts must not be copied into Cloudflare.

GitHub already provides deployment secrets for Cloudflare and OpenAI:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ZONE_ID`
- `OPENAI_API_KEY`

The decision needs to cover Cloudflare, Hetzner, and the feedback channel between both planes.

## Decision

Use Cloudflare as the Control Plane and Hetzner as the Runtime Plane.

Cloudflare owns:

- Registry metadata and module versions.
- Knowledge catalog metadata.
- Knowledge source objects, normalized documents, chunks, and manifests.
- Consolidated long-term memory entries.
- Policy and scope bindings.
- Semantic indexes for knowledge and memory.
- Control-plane APIs and ingestion pipelines.
- AI Gateway for production OpenAI calls.

Hetzner owns:

- Runtime runs and execution steps.
- Tool invocations and raw tool outputs.
- Execution traces and logs.
- Validation results.
- Runtime artifacts.
- Memory candidates derived from execution.

Cloudflare must not store ephemeral runtime artifacts. It may store only validated and consolidated memory or knowledge records that were derived from runtime data.

## Cloudflare Shape

Use these Cloudflare products by responsibility:

- Workers: Control API for registry lookup, knowledge search, memory lookup, and ingestion.
- D1: Source of truth for structured control metadata.
- R2: Object store for raw knowledge, normalized content, chunks, manifests, and consolidated memory objects.
- Vectorize: Semantic search index for knowledge and memory embeddings.
- Workers KV: Cache only for versioned registry snapshots and non-sensitive config.
- Queues or Workflows: Asynchronous ingestion, embedding, re-indexing, and archival jobs.
- AI Gateway: Day-1 production path for OpenAI calls.

Workers Bindings are the capability boundary. A Worker receives only the D1 databases, R2 buckets, Vectorize indexes, KV namespaces, queues, and secrets it needs.

## Hetzner Shape

Hetzner runtime storage should start with:

- Postgres for structured runtime records.
- Object storage or filesystem-backed artifact storage for large outputs and traces.

Minimum Postgres tables:

- `runtime_runs`
- `runtime_steps`
- `tool_invocations`
- `validation_results`
- `memory_candidates`

Minimum artifact paths:

- `artifacts/`
- `tool_outputs/`
- `traces/`
- `logs/`

`memory_candidates` is the handoff table between runtime execution and Cloudflare memory ingestion.

## Memory Feedback Loop

Memory updates flow from Hetzner to Cloudflare only through an explicit feedback pipeline:

1. Runtime stores raw execution data on Hetzner.
2. Runtime or a post-run process creates a `memory_candidate`.
3. A validator checks scope, policy, sensitivity, source run, and retention.
4. A policy gate approves, rejects, or requests clarification.
5. Approved candidates are sent to the Cloudflare Memory Ingestion API.
6. Cloudflare queues the ingestion job.
7. Cloudflare writes D1 metadata.
8. Cloudflare writes the consolidated memory object and manifest to R2.
9. Cloudflare writes or updates the corresponding Vectorize embedding.

The ingestion payload must be a consolidated memory record, not a raw runtime log. It may include stable references such as `run_id`, `profile_id`, `validator_id`, and `source_artifact_uri`, but Cloudflare must not require raw Hetzner artifacts to serve normal memory lookup.

## Composer Query Flow

The Composer should avoid many cross-cloud calls during profile composition.

The Control API should provide a batched composition endpoint that can return candidate modules, relevant policies, allowed scopes, and current registry versions for one analyzer output.

KV may cache versioned registry snapshots, but D1 remains the source of truth. Cache reads must include a registry version or ETag. If the requested version is missing, stale, or policy-sensitive, the Control API must fall back to D1.

Registry and policy decisions must not depend only on KV.

## D1 Constraints

D1 is SQLite-based and should not be treated as a high-write event stream or unbounded log store.

Design constraints:

- Serialize or throttle ingestion writes where needed.
- Keep registry writes and ingestion writes explicit and auditable.
- Do not store raw execution events in D1.
- Archive audit history to R2 according to retention policy.
- Keep `audit_events` bounded by time, volume, or both.
- Define an exit criterion for sharding or moving high-write workloads to another database if D1 becomes the bottleneck.

## Vectorize Constraints

Vectorize is the semantic search index, not the policy engine.

The query flow is:

1. D1 determines allowed scope IDs, document IDs, versions, and policy bindings.
2. Vectorize performs semantic retrieval.
3. D1 post-validates returned IDs before the result is used in composition or runtime context.

Complex filtering by scope, domain, version, policy, and sensitivity must not rely solely on Vectorize metadata filtering.

## Secrets And AI Gateway

GitHub secrets are used for deployment automation. Runtime secrets are stored as Cloudflare Worker Secrets or account-level secret bindings.

`OPENAI_API_KEY` must not be committed to config files. Production OpenAI calls should go through Cloudflare AI Gateway:

```text
Worker -> AI Gateway -> OpenAI
```

This gives the system an explicit observability and routing point for LLM calls.

## Consequences

Positive:

- Control-plane data and runtime artifacts have separate ownership.
- Cloudflare resources map cleanly to composition contracts.
- Hetzner can optimize for write-heavy execution traces without polluting control metadata.
- Long-term memory updates are reviewable and policy-gated.
- AI calls have a Day-1 observability path.

Tradeoffs:

- The memory feedback loop adds an extra ingestion pipeline.
- Composer latency must be managed through batched Control API calls and versioned snapshots.
- D1 write limits and SQLite semantics require careful ingestion design.
- Vectorize needs D1 pre-filtering and post-validation for strict policy enforcement.

## Follow-Up

- Add `docs/policies/infrastructure-boundary.md`.
- Define D1 metadata schema and R2 key conventions in a later contract task.
- Define Hetzner runtime storage schema before implementing the runtime loop.
- Add Wrangler configuration only after resource names and bindings are documented.
- Add GitHub Actions only after local infrastructure validation commands exist.

