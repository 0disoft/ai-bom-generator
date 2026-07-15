import { readdirSync } from "node:fs";
import { join } from "node:path";

const directory = import.meta.dir;
const entrypoints = readdirSync(directory)
  .filter((name) => name.endsWith(".ts") && !name.endsWith(".test.ts"))
  .map((name) => join(directory, name));

const result = await Bun.build({
  entrypoints,
  format: "esm",
  target: "bun",
  write: false,
  throw: false,
});
if (!result.success) {
  for (const log of result.logs) console.error(log);
  throw new Error(`failed to build ${entrypoints.length} release tooling entrypoints`);
}
console.log(`built ${entrypoints.length} release tooling entrypoints without writes`);
