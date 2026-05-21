import { cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: {
        configPath: "./workers/control-api/wrangler.toml",
      },
    }),
  ],
  test: {
    include: ["workers/control-api/test/**/*.test.ts"],
  },
});
