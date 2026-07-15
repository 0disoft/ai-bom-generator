import {
  SOURCE_PROJECT,
  fetchReleaseTag,
  requestedVersion,
  run,
} from "./lib";

if (!process.argv.includes("--apply")) throw new Error("refusing tag mutation without --apply");

const { version, tag, majorTag } = requestedVersion(process.argv.slice(2));
run(["bun", "tools/release/verify.ts", "--version", version], SOURCE_PROJECT);
const releaseCommit = fetchReleaseTag(tag);
const remote = run(["git", "ls-remote", "origin", `refs/tags/${majorTag}`], SOURCE_PROJECT);
const remoteTarget = remote ? remote.split(/\s+/)[0] : undefined;
if (remoteTarget === releaseCommit) {
  console.log(`${majorTag} already resolves to ${tag} at ${releaseCommit}`);
  process.exit(0);
}

run(["git", "tag", "--force", majorTag, tag], SOURCE_PROJECT);
run(["git", "push", "origin", `refs/tags/${majorTag}`, "--force"], SOURCE_PROJECT);
const promotedTarget = run(
  ["git", "ls-remote", "origin", `refs/tags/${majorTag}`],
  SOURCE_PROJECT,
).split(/\s+/)[0];
if (promotedTarget !== releaseCommit) {
  throw new Error(`remote ${majorTag} resolves to ${promotedTarget || "nothing"}, expected ${releaseCommit}`);
}
console.log(`${majorTag} now resolves to ${tag} at ${releaseCommit}`);
