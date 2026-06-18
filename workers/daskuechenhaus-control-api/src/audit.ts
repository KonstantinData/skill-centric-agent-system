import { ulid } from 'ulid';
import type { JsonObject } from './types';

export interface AuditEventInput {
  tenantId: string;
  caseId: string;
  actor: string;
  action: string;
  fieldName?: string | null;
  oldValue?: unknown;
  newValue?: unknown;
  details?: JsonObject | null;
}

export async function writeAuditEvent(
  db: D1Database,
  input: AuditEventInput
): Promise<void> {
  await db
    .prepare(
      `INSERT INTO case_audit_events (
        id,
        tenant_id,
        case_id,
        actor,
        action,
        field_name,
        old_value,
        new_value,
        details,
        created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(
      ulid(),
      input.tenantId,
      input.caseId,
      input.actor,
      input.action,
      input.fieldName ?? null,
      serializeAuditValue(input.oldValue),
      serializeAuditValue(input.newValue),
      input.details ? JSON.stringify(input.details) : null,
      new Date().toISOString()
    )
    .run();
}

function serializeAuditValue(value: unknown): string | null {
  if (value === undefined || value === null) {
    return null;
  }
  if (typeof value === 'string') {
    return value;
  }
  return JSON.stringify(value);
}
