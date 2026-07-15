import { mkdtempSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

import { SMOKE_PROJECT, readDeclaredVersion, run } from "./lib";
import { updateSmokeActionRef } from "./smoke-lib";

const apply = process.argv.includes("--apply");
const check = process.argv.includes("--check");
if (apply === check) throw new Error("choose exactly one of --check or --apply");

const workflowPath = ".github/workflows/ai-bom-release-smoke.yml";
const absoluteWorkflowPath = join(SMOKE_PROJECT, workflowPath);
const releaseVersion = readDeclaredVersion();
const original = readFileSync(absoluteWorkflowPath, "utf8");
const update = updateSmokeActionRef(original, releaseVersion.version);

validateWorkflow(update.nextText);
if (check) {
  if (update.changed) {
    throw new Error(
      `release smoke uses v${update.currentVersion}; expected ${releaseVersion.tag}`,
    );
  }
  console.log(`release smoke already uses ${releaseVersion.tag}`);
  process.exit(0);
}

if (!update.changed) {
  console.log(`release smoke already uses ${releaseVersion.tag}; no write needed`);
  process.exit(0);
}
if (run(["git", "status", "--porcelain"], SMOKE_PROJECT)) {
  throw new Error("smoke repository must be clean before updating the release workflow");
}

const temporaryPath = join(dirname(absoluteWorkflowPath), `.ai-bom-release-smoke-${process.pid}.tmp`);
try {
  writeFileSync(temporaryPath, update.nextText, "utf8");
  renameSync(temporaryPath, absoluteWorkflowPath);
} finally {
  rmSync(temporaryPath, { force: true });
}
console.log(`updated release smoke from v${update.currentVersion} to ${releaseVersion.tag}`);

function validateWorkflow(workflow: string): void {
  const temporaryDirectory = mkdtempSync(join(tmpdir(), "ai-bom-smoke-actionlint-"));
  const candidate = join(temporaryDirectory, "ai-bom-release-smoke.yml");
  try {
    writeFileSync(candidate, workflow, "utf8");
    run(["actionlint", candidate]);
  } finally {
    rmSync(temporaryDirectory, { recursive: true, force: true });
  }
}
