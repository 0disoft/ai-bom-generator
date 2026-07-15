import {
  SOURCE_PROJECT,
  SOURCE_REPOSITORY,
  assertImmutableRelease,
  fetchReleaseTag,
  listWorkflowRuns,
  optionalRun,
  publicationState,
  pypiVersionExists,
  requestedVersion,
  run,
  selectPublishRun,
  waitForPublish,
} from "./lib";
import { validateReleaseMetadata } from "./metadata-lib";

if (!process.argv.includes("--apply")) throw new Error("refusing release mutation without --apply");

const releaseVersion = requestedVersion(process.argv.slice(2));
const { version, tag } = releaseVersion;
const releaseJson = optionalRun([
  "gh", "release", "view", tag, "--repo", SOURCE_REPOSITORY,
  "--json", "isDraft,isImmutable,isPrerelease,tagName,url",
]);
const releaseExists = releaseJson !== undefined;
const pypiExists = await pypiVersionExists(version);
const state = publicationState(pypiExists, releaseExists);

if (state === "complete") {
  const release = assertImmutableRelease(tag);
  const releaseCommit = fetchReleaseTag(tag);
  const publish = selectPublishRun(
    listWorkflowRuns(SOURCE_REPOSITORY, "publish-pypi.yml", 20),
    tag,
    releaseCommit,
  );
  if (!publish || publish.status !== "completed" || publish.conclusion !== "success") {
    throw new Error(`${tag} exists publicly but has no matching successful PyPI publish run`);
  }
  console.log(`${tag} is already published at ${release.url} (run ${publish.databaseId})`);
  process.exit(0);
}

if (state === "partial") {
  if (releaseExists) {
    assertImmutableRelease(tag);
    const releaseCommit = fetchReleaseTag(tag);
    const publish = selectPublishRun(
      listWorkflowRuns(SOURCE_REPOSITORY, "publish-pypi.yml", 20),
      tag,
      releaseCommit,
    );
    if (publish?.status !== "completed") {
      const completed = await waitForPublish(tag, releaseCommit);
      console.log(`resumed ${tag} PyPI publish: ${completed.url} (run ${completed.databaseId})`);
      process.exit(0);
    }
  }
  throw new Error(
    `partial release state for ${tag}: GitHub release=${releaseExists}, PyPI version=${pypiExists}`,
  );
}

const status = run(["git", "status", "--porcelain"], SOURCE_PROJECT);
if (status) throw new Error("source repository must be clean before release");
const branch = run(["git", "branch", "--show-current"], SOURCE_PROJECT);
if (branch !== "main") throw new Error(`release requires main, found ${branch || "detached HEAD"}`);
run(["git", "fetch", "origin", "main"], SOURCE_PROJECT);
const head = run(["git", "rev-parse", "HEAD"], SOURCE_PROJECT);
const remoteMain = run(["git", "rev-parse", "origin/main"], SOURCE_PROJECT);
if (head !== remoteMain) throw new Error(`local HEAD ${head} does not match origin/main ${remoteMain}`);

const metadata = validateReleaseMetadata(releaseVersion);

const releaseUrl = run([
  "gh", "release", "create", tag, "--repo", SOURCE_REPOSITORY, "--target", head,
  "--title", `AI-BOM Generator ${tag}`, "--notes-file", metadata.notesPath, "--latest",
]);
console.log(`created release: ${releaseUrl}`);
const publish = await waitForPublish(tag, head);
console.log(`PyPI publish succeeded: ${publish.url} (run ${publish.databaseId})`);
