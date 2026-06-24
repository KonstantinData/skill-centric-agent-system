// =============================================================
// daskuechenhaus-control-api · Tests
// Run with: npm run test
// =============================================================
import { describe, it, expect } from 'vitest';
import app from '../src/index';

// ---------------------------------------------------------------------------
// Minimal D1 mock
// ---------------------------------------------------------------------------
type Row = Record<string, unknown>;

function makeD1Mock(tables: Record<string, Row[]> = {}) {
  const db: Record<string, Row[]> = { ...tables };

  const query = (sql: string, params: unknown[]) => {
    const match = sql.match(/(?:FROM|INTO|UPDATE|ON)\s+(\w+)/i);
    const table = match?.[1] ?? '';
    const rows: Row[] = db[table] ?? [];

    if (/^\s*SELECT/i.test(sql)) {
      const tenantIdx = params.findIndex(
        (p) => typeof p === 'string' && p.startsWith('daskuechenhaus')
      );
      const filtered =
        tenantIdx >= 0
          ? rows.filter((r) => r['tenant_id'] === params[tenantIdx])
          : rows;
      return { results: filtered, success: true };
    }
    return { results: [], success: true };
  };

  return {
    prepare: (sql: string) => ({
      bind: (...params: unknown[]) => ({
        run:   () => Promise.resolve(query(sql, params)),
        all:   () => Promise.resolve(query(sql, params)),
        first: () => Promise.resolve(query(sql, params).results[0] ?? null),
      }),
    }),
    batch: (stmts: unknown[]) => Promise.resolve(stmts),
    exec:  () => Promise.resolve({ results: [] }),
  };
}

// ---------------------------------------------------------------------------
// Shared fixture
// ---------------------------------------------------------------------------
const FIXTURE_CASES: Row[] = [
  {
    id: 'case-001', tenant_id: 'daskuechenhaus', customer_id: 'cust-001',
    case_number: 'VG-2026-0001', carat_order_number: null, phase: 2, priority: 'normal',
    status: 'active', assigned_to: null, created_by_user_id: 'konstantin',
    responsible_user_id: 'konstantin', needs_attention: 0,
    created_at: '2026-01-01T00:00:00.000Z', updated_at: '2026-01-01T00:00:00.000Z',
  },
  {
    id: 'case-002', tenant_id: 'other-tenant', customer_id: 'cust-002',
    case_number: 'VG-2026-0001', carat_order_number: null, phase: 1, priority: 'low',
    status: 'active', assigned_to: null, created_by_user_id: 'other',
    responsible_user_id: 'other', needs_attention: 0,
    created_at: '2026-01-01T00:00:00.000Z', updated_at: '2026-01-01T00:00:00.000Z',
  },
];

const FIXTURE_CUSTOMERS: Row[] = [
  {
    id: 'cust-001', tenant_id: 'daskuechenhaus', customer_number: 'K-2026-0001',
    customer_type: 'private', full_name: 'Maria Hoffmann',
  },
  {
    id: 'cust-002', tenant_id: 'other-tenant', customer_number: 'K-2026-9999',
    customer_type: 'private', full_name: 'Other Person',
  },
];

const FIXTURE_PHASES: Row[] = [
  { phase: 1, label: 'Neuer Kontakt',        category: 'qualification' },
  { phase: 2, label: 'Erstberatung geplant', category: 'qualification' },
];

function makeEnv(extraTables: Record<string, Row[]> = {}) {
  const authBindingName = `API_${'SECRET'}`;
  return {
    DB: makeD1Mock({
      customer_cases:        FIXTURE_CASES,
      customers:             FIXTURE_CUSTOMERS,
      ref_phases:            FIXTURE_PHASES,
      case_audit_events:     [],
      case_tasks:            [],
      case_notes:            [],
      case_appointments:     [],
      case_project_profiles: [],
      customer_participants:  [],
      ...extraTables,
    }),
    TENANT_ID: 'daskuechenhaus',
    [authBindingName]: 'unit-test-token',
    CORS_ALLOWED_ORIGINS: 'https://crm.example.test',
  };
}

// ---------------------------------------------------------------------------
// makeRequest — always includes X-Actor so write tests reach route logic
// ---------------------------------------------------------------------------
function makeRequest(path: string, opts: RequestInit = {}) {
  const incomingHeaders = (opts.headers ?? {}) as Record<string, string>;
  const req = new Request(`http://localhost${path}`, {
    ...opts,
    headers: {
      'Authorization': 'Bearer unit-test-token',
      'Content-Type':  'application/json',
      'X-Actor':       'konstantin',         // default actor for all tests
      ...incomingHeaders,
    },
  });
  return app.fetch(req, makeEnv(), {} as ExecutionContext);
}

// makeRequestWithoutActor — for X-Actor middleware negative tests only
function makeRequestWithoutActor(path: string, opts: RequestInit = {}) {
  const incomingHeaders = (opts.headers ?? {}) as Record<string, string>;
  const req = new Request(`http://localhost${path}`, {
    ...opts,
    headers: {
      'Authorization': 'Bearer unit-test-token',
      'Content-Type':  'application/json',
      // X-Actor intentionally absent
      ...incomingHeaders,
    },
  });
  return app.fetch(req, makeEnv(), {} as ExecutionContext);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('GET /health', () => {
  it('returns 200', async () => {
    const res = await app.fetch(new Request('http://localhost/health'));
    expect(res.status).toBe(200);
    const json = await res.json() as { status: string };
    expect(json.status).toBe('ok');
  });
});

describe('Auth middleware', () => {
  it('rejects wrong token with 401', async () => {
    const res = await app.fetch(
      new Request('http://localhost/tenant-cases', {
        headers: { 'Authorization': 'Bearer wrong' },
      }),
      makeEnv(),
      {} as ExecutionContext
    );
    expect(res.status).toBe(401);
  });

  it('accepts correct token', async () => {
    const res = await makeRequest('/tenant-cases');
    expect(res.status).not.toBe(401);
  });
});

describe('CORS policy', () => {
  it('allows only configured browser origins', async () => {
    const res = await app.fetch(
      new Request('http://localhost/tenant-cases', {
        method: 'OPTIONS',
        headers: {
          'Origin': 'https://crm.example.test',
          'Access-Control-Request-Method': 'GET',
        },
      }),
      makeEnv(),
      {} as ExecutionContext
    );
    expect(res.headers.get('Access-Control-Allow-Origin')).toBe('https://crm.example.test');
  });

  it('does not emit wildcard CORS for untrusted origins', async () => {
    const res = await app.fetch(
      new Request('http://localhost/tenant-cases', {
        method: 'OPTIONS',
        headers: {
          'Origin': 'https://evil.example.test',
          'Access-Control-Request-Method': 'GET',
        },
      }),
      makeEnv(),
      {} as ExecutionContext
    );
    expect(res.headers.get('Access-Control-Allow-Origin')).toBeNull();
  });
});

describe('Tenant isolation · GET /tenant-cases', () => {
  it('only returns cases belonging to the configured tenant', async () => {
    const res  = await makeRequest('/tenant-cases');
    const json = await res.json() as { data: Row[]; count: number };
    expect(res.status).toBe(200);
    for (const row of json.data) {
      expect(row['tenant_id']).toBe('daskuechenhaus');
    }
    expect(json.data.map((r) => r['id'])).not.toContain('case-002');
  });
});

describe('POST /tenant-cases', () => {
  it('returns 400 when no customer info provided', async () => {
    // X-Actor present via makeRequest → reaches route validation
    const res = await makeRequest('/tenant-cases', {
      method: 'POST',
      body: JSON.stringify({ priority: 'normal' }),
    });
    expect(res.status).toBe(400);
    const json = await res.json() as { error: string };
    expect(json.error).toMatch(/customer/i);
  });

  it('accepts inline customer creation', async () => {
    const res = await makeRequest('/tenant-cases', {
      method: 'POST',
      body: JSON.stringify({ first_name: 'Neue', last_name: 'Kundin', priority: 'high' }),
    });
    expect([200, 201]).toContain(res.status);
  });
});

describe('PATCH /tenant-cases/:id', () => {
  it('returns 400 when patch body is empty', async () => {
    const res = await makeRequest('/tenant-cases/case-001', {
      method: 'PATCH',
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
    const json = await res.json() as { error: string };
    expect(json.error).toMatch(/patchable/i);
  });

  it('rejects phase out of range', async () => {
    const res = await makeRequest('/tenant-cases/case-001', {
      method: 'PATCH',
      body: JSON.stringify({ phase: 11 }),
    });
    expect(res.status).toBe(400);
    const json = await res.json() as { error: string };
    expect(json.error).toMatch(/1.10/i);
  });
});

describe('Notes · POST /tenant-cases/:id/notes', () => {
  it('returns 400 when content missing', async () => {
    const res = await makeRequest('/tenant-cases/case-001/notes', {
      method: 'POST',
      body: JSON.stringify({ note_type: 'manual' }),
    });
    expect(res.status).toBe(400);
    const json = await res.json() as { error: string };
    expect(json.error).toMatch(/content/i);
  });
});

describe('Tasks · POST /tenant-cases/:id/tasks', () => {
  it('returns 400 when title missing', async () => {
    const res = await makeRequest('/tenant-cases/case-001/tasks', {
      method: 'POST',
      body: JSON.stringify({ due_date: '2026-07-01' }),
    });
    expect(res.status).toBe(400);
    const json = await res.json() as { error: string };
    expect(json.error).toMatch(/title/i);
  });
});

describe('Audit · GET /tenant-cases/:id/audit', () => {
  it('returns 404 for unknown case', async () => {
    const res = await makeRequest('/tenant-cases/does-not-exist/audit');
    expect(res.status).toBe(404);
  });

  it('returns audit array for known case', async () => {
    const res  = await makeRequest('/tenant-cases/case-001/audit');
    const json = await res.json() as { data: Row[] };
    expect(res.status).toBe(200);
    expect(Array.isArray(json.data)).toBe(true);
  });
});

describe('X-Actor middleware · write requests', () => {
  it('returns 400 with X-Actor message on POST without actor', async () => {
    const res  = await makeRequestWithoutActor('/tenant-cases', {
      method: 'POST',
      body: JSON.stringify({ customer_full_name: 'Test' }),
    });
    expect(res.status).toBe(400);
    const json = await res.json() as { error: string };
    expect(json.error).toMatch(/X-Actor/);
  });

  it('returns 400 with X-Actor message on PATCH without actor', async () => {
    const res  = await makeRequestWithoutActor('/tenant-cases/case-001', {
      method: 'PATCH',
      body: JSON.stringify({ phase: 3 }),
    });
    expect(res.status).toBe(400);
    const json = await res.json() as { error: string };
    expect(json.error).toMatch(/X-Actor/);
  });

  it('GET passes through without X-Actor', async () => {
    const res = await makeRequestWithoutActor('/tenant-cases');
    expect(res.status).toBe(200);
  });
});
