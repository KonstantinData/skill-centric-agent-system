// =============================================================
// daskuechenhaus-control-api · Entry point
// =============================================================
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import type { AppEnv } from './types';
import { authMiddleware, tenantMiddleware, actorMiddleware } from './middleware';
import casesRouter from './routes/cases';

const app = new Hono<AppEnv>();

app.use('*', logger());
app.use('*', cors({
  origin: '*',
  allowHeaders: ['Authorization', 'Content-Type', 'X-Actor'],
}));

app.get('/health', (c) =>
  c.json({ status: 'ok', service: 'daskuechenhaus-control-api' })
);

app.use('/tenant-cases/*', authMiddleware);
app.use('/tenant-cases/*', tenantMiddleware);
app.use('/tenant-cases/*', actorMiddleware);
app.route('/tenant-cases', casesRouter);

app.notFound((c) => c.json({ error: 'Not found' }, 404));
app.onError((err, c) => {
  console.error(err);
  return c.json({ error: 'Internal server error' }, 500);
});

export default app;
