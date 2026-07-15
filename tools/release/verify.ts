import {
  SMOKE_PROJECT,
  SMOKE_REPOSITORY,
  SOURCE_PROJECT,
  SOURCE_REPOSITORY,
  fetchReleaseTag,
  listWorkflowRuns,
  requestedVersion,
  run,
  selectPublishRun,
  selectSmokeRun,
} from "./lib";

const { version, tag } = requestedVersion(process.argv.slice(2));
const releaseCommit = fetchReleaseTag(tag);
const smokeHead = run(["git", "rev-parse", "HEAD"], SMOKE_PROJECT);
const smokeRun = selectSmokeRun(
  listWorkflowRuns(SMOKE_REPOSITORY, "ai-bom-release-smoke.yml", 20),
  smokeHead,
);
if (!smokeRun || smokeRun.status !== "completed" || smokeRun.conclusion !== "success") {
  throw new Error(`exact release smoke did not succeed: ${smokeRun?.url ?? "missing run"}`);
}

const publishRun = selectPublishRun(
  listWorkflowRuns(SOURCE_REPOSITORY, "publish-pypi.yml", 20),
  tag,
  releaseCommit,
);
if (!publishRun || publishRun.status !== "completed" || publishRun.conclusion !== "success") {
  throw new Error(`missing successful ${tag} PyPI publish run`);
}

run(
  [
    "uv", "run", "--no-sync", "--python", "3.12", "python", "-B", "scripts/verify_release.py",
    "--version", version, "--publish-run-id", String(publishRun.databaseId),
    "--smoke-run-id", String(smokeRun.databaseId),
  ],
  SOURCE_PROJECT,
);
console.log(
  `release verification passed for ${tag} with publish run ${publishRun.databaseId} ` +
  `and smoke run ${smokeRun.databaseId}`,
);
