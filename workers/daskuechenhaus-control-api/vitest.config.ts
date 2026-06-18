// Unit tests only — no Wrangler/D1 runtime required.
// For integration tests against local D1, use:
//   wrangler dev --local  +  manual smoke tests (see README)
// A separate vitest.worker.config.ts will be added when integration
// tests against real D1 bindings are set up.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['test/**/*.test.ts'],
  },
});
