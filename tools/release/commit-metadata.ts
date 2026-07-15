import { run } from "./lib";
import {
  assertExactPathSet,
  gitPaths,
  validateReleaseMetadata,
} from "./metadata-lib";

if (!process.argv.includes("--apply")) throw new Error("refusing metadata commit without --apply");

const metadata = validateReleaseMetadata();
assertExactPathSet(
  gitPaths(["git", "diff", "--cached", "--name-only"]),
  metadata.paths,
  "staged release metadata",
);
if (gitPaths(["git", "diff", "--name-only"]).length > 0) {
  throw new Error("release metadata commit has unstaged tracked changes");
}
if (gitPaths(["git", "ls-files", "--others", "--exclude-standard"]).length > 0) {
  throw new Error("release metadata commit has untracked files");
}
run(["git", "diff", "--cached", "--check"]);
run(["git", "commit", "-m", `chore(release): prepare ${metadata.release.tag}`]);
console.log(`committed synchronized release metadata for ${metadata.release.tag}`);
