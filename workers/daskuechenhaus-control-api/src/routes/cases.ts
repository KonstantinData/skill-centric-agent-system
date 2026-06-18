import { Hono } from 'hono';
import type { Context } from 'hono';
import { ulid } from 'ulid';
import { writeAuditEvent } from '../audit';
import { errorResponse } from '../middleware';
import type { AppEnv, JsonObject } from '../types';

type CasePatch = {
  assigned_to?: string | null;
  phase?: number;
  priority?: string;
  status?: string;
};

const PATCHABLE_FIELDS = new Set(['assigned_to', 'phase', 'priority', 'status']);
const PRIORITIES = new Set(['low', 'normal', 'high', 'urgent']);
const STATUSES = new Set(['active', 'paused', 'won', 'lost', 'closed']);

const casesRouter = new Hono<AppEnv>();
type AppContext = Context<AppEnv>;

casesRouter.get('/', async (c) => {
  const tenantId = tenant(c);
  const rows = await c.env.DB
    .prepare(
      `SELECT
        cc.*,
        cu.full_name AS customer_full_name,
        rp.label AS phase_label,
        rp.category AS phase_category
      FROM customer_cases cc
      LEFT JOIN customers cu ON cu.id = cc.customer_id AND cu.tenant_id = cc.tenant_id
      LEFT JOIN ref_phases rp ON rp.phase = cc.phase
      WHERE cc.tenant_id = ?
      ORDER BY cc.updated_at DESC, cc.created_at DESC`
    )
    .bind(tenantId)
    .all();

  return c.json({ data: rows.results ?? [], count: rows.results?.length ?? 0 });
});

casesRouter.post('/', async (c) => {
  const tenantId = tenant(c);
  const actor = requestActor(c);
  const body = await readJson(c);
  const now = new Date().toISOString();

  let customerId = getString(body, 'customer_id');
  const inlineCustomerName = getString(body, 'customer_full_name');

  if (!customerId && !inlineCustomerName) {
    return errorResponse(
      c,
      400,
      'customer_id or customer_full_name is required to create a customer case'
    );
  }

  if (customerId) {
    const customer = await c.env.DB
      .prepare('SELECT id FROM customers WHERE tenant_id = ? AND id = ?')
      .bind(tenantId, customerId)
      .first();
    if (!customer) {
      return errorResponse(c, 404, 'Customer not found for tenant');
    }
  } else {
    customerId = ulid();
    await c.env.DB
      .prepare(
        `INSERT INTO customers (
          id,
          tenant_id,
          full_name,
          email,
          phone,
          created_at,
          updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(
        customerId,
        tenantId,
        inlineCustomerName,
        getString(body, 'customer_email'),
        getString(body, 'customer_phone'),
        now,
        now
      )
      .run();
  }

  const caseId = ulid();
  const phase = normalizePhase(body.phase ?? 1);
  if (typeof phase === 'string') {
    return errorResponse(c, 400, phase);
  }

  const priority = getString(body, 'priority') ?? 'normal';
  if (!PRIORITIES.has(priority)) {
    return errorResponse(c, 400, 'priority must be one of low, normal, high, urgent');
  }

  const status = getString(body, 'status') ?? 'active';
  if (!STATUSES.has(status)) {
    return errorResponse(c, 400, 'status must be one of active, paused, won, lost, closed');
  }

  const assignedTo = getString(body, 'assigned_to');
  const caseNumber = await nextCaseNumber(c.env.DB, tenantId, now);

  await c.env.DB.batch([
    c.env.DB
      .prepare(
        `INSERT INTO customer_cases (
          id,
          tenant_id,
          customer_id,
          case_number,
          phase,
          priority,
          status,
          assigned_to,
          created_at,
          updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(
        caseId,
        tenantId,
        customerId,
        caseNumber,
        phase,
        priority,
        status,
        assignedTo,
        now,
        now
      ),
    c.env.DB
      .prepare(
        `INSERT INTO case_project_profiles (
          id,
          tenant_id,
          case_id,
          created_at,
          updated_at
        ) VALUES (?, ?, ?, ?, ?)`
      )
      .bind(ulid(), tenantId, caseId, now, now),
  ]);

  await writeAuditEvent(c.env.DB, {
    tenantId,
    caseId,
    actor,
    action: 'case.created',
    details: { case_number: caseNumber, customer_id: customerId },
  });

  return c.json(
    {
      data: {
        id: caseId,
        tenant_id: tenantId,
        customer_id: customerId,
        case_number: caseNumber,
        phase,
        priority,
        status,
        assigned_to: assignedTo,
        created_at: now,
        updated_at: now,
      },
    },
    201
  );
});

casesRouter.patch('/:id', async (c) => {
  const tenantId = tenant(c);
  const actor = requestActor(c);
  const caseId = c.req.param('id');
  const body = await readJson(c);
  const patch = pickPatch(body);

  if (Object.keys(patch).length === 0) {
    return errorResponse(c, 400, 'No patchable fields provided');
  }

  if (patch.phase !== undefined) {
    const phase = normalizePhase(patch.phase);
    if (typeof phase === 'string') {
      return errorResponse(c, 400, phase);
    }
    patch.phase = phase;
  }

  if (patch.priority !== undefined && !PRIORITIES.has(patch.priority)) {
    return errorResponse(c, 400, 'priority must be one of low, normal, high, urgent');
  }

  if (patch.status !== undefined && !STATUSES.has(patch.status)) {
    return errorResponse(c, 400, 'status must be one of active, paused, won, lost, closed');
  }

  const existing = await c.env.DB
    .prepare('SELECT * FROM customer_cases WHERE tenant_id = ? AND id = ?')
    .bind(tenantId, caseId)
    .first<JsonObject>();
  if (!existing) {
    return errorResponse(c, 404, 'Customer case not found for tenant');
  }

  const now = new Date().toISOString();
  const fields = Object.keys(patch);
  const setSql = fields.map((field) => `${field} = ?`).join(', ');
  const values = fields.map((field) => patch[field as keyof CasePatch]);

  await c.env.DB
    .prepare(
      `UPDATE customer_cases
      SET ${setSql}, updated_at = ?
      WHERE tenant_id = ? AND id = ?`
    )
    .bind(...values, now, tenantId, caseId)
    .run();

  for (const field of fields) {
    await writeAuditEvent(c.env.DB, {
      tenantId,
      caseId,
      actor,
      action: field === 'phase' ? 'case.phase_changed' : 'case.updated',
      fieldName: field,
      oldValue: existing[field],
      newValue: patch[field as keyof CasePatch],
    });
  }

  return c.json({ data: { id: caseId, ...patch, updated_at: now } });
});

casesRouter.post('/:id/notes', async (c) => {
  const tenantId = tenant(c);
  const actor = requestActor(c);
  const caseId = c.req.param('id');
  const body = await readJson(c);
  const content = getString(body, 'content');

  if (!content) {
    return errorResponse(c, 400, 'content is required');
  }
  if (!(await caseExists(c.env.DB, tenantId, caseId))) {
    return errorResponse(c, 404, 'Customer case not found for tenant');
  }

  const now = new Date().toISOString();
  const noteId = ulid();
  await c.env.DB
    .prepare(
      `INSERT INTO case_notes (
        id,
        tenant_id,
        case_id,
        note_type,
        content,
        source,
        created_by,
        created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(
      noteId,
      tenantId,
      caseId,
      getString(body, 'note_type') ?? 'manual',
      content,
      getString(body, 'source') ?? 'manual',
      actor,
      now
    )
    .run();

  await writeAuditEvent(c.env.DB, {
    tenantId,
    caseId,
    actor,
    action: 'note.created',
    details: { note_id: noteId },
  });

  return c.json({ data: { id: noteId, case_id: caseId, content, created_at: now } }, 201);
});

casesRouter.post('/:id/tasks', async (c) => {
  const tenantId = tenant(c);
  const actor = requestActor(c);
  const caseId = c.req.param('id');
  const body = await readJson(c);
  const title = getString(body, 'title');

  if (!title) {
    return errorResponse(c, 400, 'title is required');
  }
  if (!(await caseExists(c.env.DB, tenantId, caseId))) {
    return errorResponse(c, 404, 'Customer case not found for tenant');
  }

  const source = getString(body, 'source') ?? 'manual';
  const taskId = ulid();
  const now = new Date().toISOString();

  await c.env.DB
    .prepare(
      `INSERT INTO case_tasks (
        id,
        tenant_id,
        case_id,
        title,
        description,
        status,
        due_date,
        assigned_to,
        source,
        confirmed_by,
        created_at,
        updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(
      taskId,
      tenantId,
      caseId,
      title,
      getString(body, 'description'),
      getString(body, 'status') ?? 'open',
      getString(body, 'due_date'),
      getString(body, 'assigned_to'),
      source,
      source === 'skill_suggestion' ? null : actor,
      now,
      now
    )
    .run();

  await writeAuditEvent(c.env.DB, {
    tenantId,
    caseId,
    actor,
    action: 'task.created',
    details: { task_id: taskId, source },
  });

  return c.json({ data: { id: taskId, case_id: caseId, title, created_at: now } }, 201);
});

casesRouter.get('/:id/audit', async (c) => {
  const tenantId = tenant(c);
  const caseId = c.req.param('id');

  if (!(await caseExists(c.env.DB, tenantId, caseId))) {
    return errorResponse(c, 404, 'Customer case not found for tenant');
  }

  const rows = await c.env.DB
    .prepare(
      `SELECT *
      FROM case_audit_events
      WHERE tenant_id = ? AND case_id = ?
      ORDER BY created_at DESC`
    )
    .bind(tenantId, caseId)
    .all();

  return c.json({ data: rows.results ?? [] });
});

async function readJson(c: AppContext): Promise<JsonObject> {
  try {
    return (await c.req.json()) as JsonObject;
  } catch {
    return {};
  }
}

function tenant(c: AppContext): string {
  return c.get('tenant_id');
}

function requestActor(c: AppContext): string {
  return c.req.header('X-Actor')?.trim() ?? 'unknown';
}

function getString(body: JsonObject, key: string): string | null {
  const value = body[key];
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function normalizePhase(value: unknown): number | string {
  const phase = typeof value === 'number' ? value : Number(value);
  if (!Number.isInteger(phase) || phase < 1 || phase > 10) {
    return 'phase must be in range 1-10';
  }
  return phase;
}

function pickPatch(body: JsonObject): CasePatch {
  const patch: CasePatch = {};
  for (const [key, value] of Object.entries(body)) {
    if (!PATCHABLE_FIELDS.has(key)) {
      continue;
    }
    if (key === 'phase') {
      patch.phase = value as number;
    } else if (key === 'assigned_to') {
      patch.assigned_to = typeof value === 'string' && value.trim() ? value.trim() : null;
    } else if (typeof value === 'string') {
      patch[key as 'priority' | 'status'] = value.trim();
    }
  }
  return patch;
}

async function caseExists(
  db: D1Database,
  tenantId: string,
  caseId: string
): Promise<boolean> {
  const row = await db
    .prepare('SELECT id FROM customer_cases WHERE tenant_id = ?')
    .bind(tenantId)
    .all<{ id: string }>();
  return (row.results ?? []).some((candidate) => candidate.id === caseId);
}

async function nextCaseNumber(
  db: D1Database,
  tenantId: string,
  timestamp: string
): Promise<string> {
  const year = timestamp.slice(0, 4);
  const countRow = await db
    .prepare(
      `SELECT COUNT(*) AS count
      FROM customer_cases
      WHERE tenant_id = ? AND case_number LIKE ?`
    )
    .bind(tenantId, `KH-${year}-%`)
    .first<{ count: number }>();
  const next = Number(countRow?.count ?? 0) + 1;
  return `KH-${year}-${String(next).padStart(4, '0')}`;
}

export default casesRouter;
