import { run } from "./lib";
import {
  assertExactPathSet,
  changedMetadataPaths,
  gitPaths,
  validateReleaseMetadata,
} from "./metadata-lib";

if (!process.argv.includes("--apply")) throw new Error("refusing metadata staging without --apply");

const metadata = validateReleaseMetadata();
assertExactPathSet(changedMetadataPaths(), metadata.paths, "release metadata changes");
run(["git", "add", "--", ...metadata.paths]);
assertExactPathSet(
  gitPaths(["git", "diff", "--cached", "--name-only"]),
  metadata.paths,
  "staged release metadata",
);
console.log(`staged synchronized release metadata for ${metadata.release.tag}`);
