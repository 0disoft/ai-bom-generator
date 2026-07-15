import { readFileSync } from "node:fs";
import { join } from "node:path";

import { SMOKE_PROJECT, readDeclaredVersion, run } from "./lib";
import { assertSoleStagedWorkflow, updateSmokeActionRef } from "./smoke-lib";

if (!process.argv.includes("--apply")) throw new Error("refusing smoke commit without --apply");

const workflowPath = ".github/workflows/ai-bom-release-smoke.yml";
const staged = run(["git", "diff", "--cached", "--name-only"], SMOKE_PROJECT)
  .split(/\r?\n/)
  .filter(Boolean);
assertSoleStagedWorkflow(staged, workflowPath);
if (run(["git", "diff", "--name-only"], SMOKE_PROJECT)) {
  throw new Error("smoke repository has unstaged tracked changes");
}

const releaseVersion = readDeclaredVersion();
const workflow = readFileSync(join(SMOKE_PROJECT, workflowPath), "utf8");
const update = updateSmokeActionRef(workflow, releaseVersion.version);
if (update.changed) throw new Error(`staged smoke workflow does not use ${releaseVersion.tag}`);
run(["actionlint", workflowPath], SMOKE_PROJECT);
run(["git", "commit", "-m", `test: verify ai-bom-generator ${releaseVersion.tag}`], SMOKE_PROJECT);
console.log(`committed exact release smoke for ${releaseVersion.tag}`);
