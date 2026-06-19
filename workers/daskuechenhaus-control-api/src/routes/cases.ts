import { Hono } from 'hono';
import type { Context } from 'hono';
import { ulid } from 'ulid';
import { writeAuditEvent } from '../audit';
import { errorResponse } from '../middleware';
import type { AppEnv, JsonObject } from '../types';

type CasePatch = {
  assigned_to?: string | null;
  case_number?: string;
  carat_order_number?: string | null;
  phase?: number;
  priority?: string;
  responsible_user_id?: string | null;
  status?: string;
  needs_attention?: number;
};

const PATCHABLE_FIELDS = new Set([
  'assigned_to',
  'case_number',
  'carat_order_number',
  'phase',
  'priority',
  'responsible_user_id',
  'status',
  'needs_attention',
]);
const PRIORITIES = new Set(['low', 'normal', 'high', 'urgent']);
const STATUSES = new Set(['active', 'paused', 'won', 'lost', 'closed']);
const CUSTOMER_TYPES = new Set(['private', 'company']);

const casesRouter = new Hono<AppEnv>();
type AppContext = Context<AppEnv>;

casesRouter.get('/', async (c) => {
  const tenantId = tenant(c);
  const rows = await c.env.DB
    .prepare(
      `SELECT
        cc.*,
        cu.full_name AS customer_full_name,
        cu.customer_number,
        cu.customer_type,
        cu.salutation,
        cu.first_name,
        cu.last_name,
        cu.company_name,
        cu.company_name_2,
        cu.company_name_3,
        cu.company_name_4,
        cu.vat_id,
        cu.tax_number,
        cu.email AS customer_email,
        cu.phone AS customer_phone,
        cu.mobile AS customer_mobile,
        cu.country,
        cu.iso_country_code,
        cu.postal_code,
        cu.city,
        cu.is_nato,
        cu.has_custom_vat,
        cu.custom_vat_rate,
        cu.custom_vat_rate_label,
        cu.reverse_charge,
        cu.marketing_allowed,
        cu.e_invoice,
        rp.label AS phase_label,
        rp.category AS phase_category,
        CASE
          WHEN cc.needs_attention = 1 THEN 1
          WHEN EXISTS (
            SELECT 1
            FROM case_tasks task
            WHERE task.tenant_id = cc.tenant_id
              AND task.case_id = cc.id
              AND task.status IN ('open', 'in_progress')
              AND task.due_date IS NOT NULL
              AND task.due_date <= date('now')
          ) THEN 1
          WHEN cc.phase >= 6
            AND (cc.carat_order_number IS NULL OR trim(cc.carat_order_number) = '') THEN 1
          ELSE 0
        END AS has_attention
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
  const customerType = getString(body, 'customer_type') ?? 'private';
  if (!CUSTOMER_TYPES.has(customerType)) {
    return errorResponse(c, 400, 'customer_type must be private or company');
  }

  const inlineCustomerName =
    getString(body, 'customer_full_name') ?? buildCustomerFullName(body, customerType);

  if (!customerId && !inlineCustomerName) {
    return errorResponse(
      c,
      400,
      'customer_id or customer data is required to create a customer case'
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
    const customerNumber =
      getString(body, 'customer_number') ?? await nextCustomerNumber(c.env.DB, tenantId, now);
    await c.env.DB
      .prepare(
        `INSERT INTO customers (
          id,
          tenant_id,
          customer_number,
          customer_type,
          full_name,
          salutation,
          first_name,
          last_name,
          company_name,
          company_name_2,
          company_name_3,
          company_name_4,
          vat_id,
          tax_number,
          email,
          phone,
          mobile,
          country,
          iso_country_code,
          postal_code,
          city,
          is_nato,
          has_custom_vat,
          custom_vat_rate,
          custom_vat_rate_label,
          reverse_charge,
          marketing_allowed,
          e_invoice,
          created_at,
          updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(
        customerId,
        tenantId,
        customerNumber,
        customerType,
        inlineCustomerName,
        getString(body, 'salutation'),
        getString(body, 'first_name'),
        getString(body, 'last_name'),
        getString(body, 'company_name'),
        getString(body, 'company_name_2'),
        getString(body, 'company_name_3'),
        getString(body, 'company_name_4'),
        getString(body, 'vat_id'),
        getString(body, 'tax_number'),
        getString(body, 'customer_email'),
        getString(body, 'customer_phone'),
        getString(body, 'customer_mobile'),
        getString(body, 'country') ?? getString(body, 'iso_country_code'),
        getString(body, 'iso_country_code') ?? getString(body, 'country'),
        getString(body, 'postal_code'),
        getString(body, 'city'),
        getFlag(body, 'is_nato'),
        getFlag(body, 'has_custom_vat'),
        getString(body, 'custom_vat_rate'),
        getString(body, 'custom_vat_rate_label'),
        getFlag(body, 'reverse_charge'),
        getFlag(body, 'marketing_allowed'),
        getFlag(body, 'e_invoice'),
        now,
        now
      )
      .run();

    await c.env.DB
      .prepare(
        `INSERT INTO customer_participants (
          id,
          tenant_id,
          customer_id,
          participant_index,
          participant_type,
          role,
          salutation,
          first_name,
          last_name,
          company_name,
          company_name_2,
          company_name_3,
          company_name_4,
          vat_id,
          tax_number,
          phone,
          mobile,
          email,
          country,
          iso_country_code,
          postal_code,
          city,
          is_nato,
          has_custom_vat,
          custom_vat_rate,
          custom_vat_rate_label,
          reverse_charge,
          marketing_allowed,
          e_invoice,
          created_at,
          updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(
        ulid(),
        tenantId,
        customerId,
        1,
        customerType,
        getString(body, 'participant_role') ?? 'hauptkunde',
        getString(body, 'salutation'),
        getString(body, 'first_name'),
        getString(body, 'last_name'),
        getString(body, 'company_name'),
        getString(body, 'company_name_2'),
        getString(body, 'company_name_3'),
        getString(body, 'company_name_4'),
        getString(body, 'vat_id'),
        getString(body, 'tax_number'),
        getString(body, 'customer_phone'),
        getString(body, 'customer_mobile'),
        getString(body, 'customer_email'),
        getString(body, 'country') ?? getString(body, 'iso_country_code'),
        getString(body, 'iso_country_code') ?? getString(body, 'country'),
        getString(body, 'postal_code'),
        getString(body, 'city'),
        getFlag(body, 'is_nato'),
        getFlag(body, 'has_custom_vat'),
        getString(body, 'custom_vat_rate'),
        getString(body, 'custom_vat_rate_label'),
        getFlag(body, 'reverse_charge'),
        getFlag(body, 'marketing_allowed'),
        getFlag(body, 'e_invoice'),
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
  const responsibleUserId = getString(body, 'responsible_user_id') ?? assignedTo ?? actor;
  const caseNumber = getString(body, 'case_number') ?? await nextCaseNumber(c.env.DB, tenantId, now);
  const caratOrderNumber = getString(body, 'carat_order_number');

  await c.env.DB.batch([
    c.env.DB
      .prepare(
        `INSERT INTO customer_cases (
          id,
          tenant_id,
          customer_id,
          case_number,
          carat_order_number,
          phase,
          priority,
          status,
          assigned_to,
          created_by_user_id,
          responsible_user_id,
          needs_attention,
          created_at,
          updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
      )
      .bind(
        caseId,
        tenantId,
        customerId,
        caseNumber,
        caratOrderNumber,
        phase,
        priority,
        status,
        assignedTo,
        actor,
        responsibleUserId,
        0,
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
    details: { case_number: caseNumber, carat_order_number: caratOrderNumber, customer_id: customerId },
  });

  return c.json(
    {
      data: {
        id: caseId,
        tenant_id: tenantId,
        customer_id: customerId,
        case_number: caseNumber,
        carat_order_number: caratOrderNumber,
        phase,
        priority,
        status,
        assigned_to: assignedTo,
        created_by_user_id: actor,
        responsible_user_id: responsibleUserId,
        needs_attention: 0,
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

  if (patch.needs_attention !== undefined && ![0, 1].includes(patch.needs_attention)) {
    return errorResponse(c, 400, 'needs_attention must be 0 or 1');
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

function getFlag(body: JsonObject, key: string): number {
  const value = body[key];
  return value === true || value === 1 ? 1 : 0;
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
    } else if (key === 'needs_attention') {
      patch.needs_attention = Number(value);
    } else if (key === 'assigned_to') {
      patch.assigned_to = typeof value === 'string' && value.trim() ? value.trim() : null;
    } else if (key === 'carat_order_number' || key === 'responsible_user_id') {
      patch[key] = typeof value === 'string' && value.trim() ? value.trim() : null;
    } else if (typeof value === 'string') {
      patch[key as 'case_number' | 'priority' | 'status'] = value.trim();
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
    .bind(tenantId, `VG-${year}-%`)
    .first<{ count: number }>();
  const next = Number(countRow?.count ?? 0) + 1;
  return `VG-${year}-${String(next).padStart(4, '0')}`;
}

async function nextCustomerNumber(
  db: D1Database,
  tenantId: string,
  timestamp: string
): Promise<string> {
  const year = timestamp.slice(0, 4);
  const countRow = await db
    .prepare(
      `SELECT COUNT(*) AS count
      FROM customers
      WHERE tenant_id = ? AND customer_number LIKE ?`
    )
    .bind(tenantId, `K-${year}-%`)
    .first<{ count: number }>();
  const next = Number(countRow?.count ?? 0) + 1;
  return `K-${year}-${String(next).padStart(4, '0')}`;
}

function buildCustomerFullName(body: JsonObject, customerType: string): string | null {
  if (customerType === 'company') {
    return getString(body, 'company_name');
  }

  const firstName = getString(body, 'first_name');
  const lastName = getString(body, 'last_name');
  if (!firstName && !lastName) {
    return null;
  }
  return [firstName, lastName].filter(Boolean).join(' ');
}

export default casesRouter;
