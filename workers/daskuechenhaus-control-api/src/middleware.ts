// =============================================================
// daskuechenhaus-control-api · Middleware
// =============================================================
import type { Context, Next } from 'hono';
import type { AppEnv } from './types';

const WRITE_METHODS = new Set(['POST', 'PATCH', 'PUT', 'DELETE']);

// Bearer-token auth
export async function authMiddleware(
  c: Context<AppEnv>,
  next: Next
) {
  const authHeader = c.req.header('Authorization') ?? '';
  const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7) : '';
  if (!token || token !== c.env.API_SECRET) {
    return c.json({ error: 'Unauthorized' }, 401);
  }
  return next();
}

// Attach tenant_id from env to context
export async function tenantMiddleware(
  c: Context<AppEnv>,
  next: Next
) {
  c.set('tenant_id', c.env.TENANT_ID);
  return next();
}

// X-Actor required on all write requests.
// Sprint 1: Streamlit sets 'X-Actor: konstantin'.
// Later: derive from session/JWT instead of trusting the header.
export async function actorMiddleware(
  c: Context<AppEnv>,
  next: Next
) {
  if (WRITE_METHODS.has(c.req.method)) {
    const actor = c.req.header('X-Actor')?.trim();
    if (!actor) {
      return c.json({ error: 'X-Actor header required for write requests' }, 400);
    }
  }
  return next();
}

export function errorResponse(
  c: Context,
  status: 400 | 404 | 409 | 500,
  message: string
) {
  return c.json({ error: message }, status);
}
