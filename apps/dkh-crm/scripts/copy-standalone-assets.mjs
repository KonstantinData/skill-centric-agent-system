import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { cwd } from "node:process";

const appRoot = cwd();
const standaloneRoot = join(appRoot, ".next", "standalone");

if (!existsSync(standaloneRoot)) {
  process.exit(0);
}

const copies = [
  [join(appRoot, "public"), join(standaloneRoot, "public")],
  [join(appRoot, ".next", "static"), join(standaloneRoot, ".next", "static")],
];

for (const [source, target] of copies) {
  if (!existsSync(source)) continue;
  rmSync(target, { recursive: true, force: true });
  mkdirSync(target, { recursive: true });
  cpSync(source, target, { recursive: true });
}
