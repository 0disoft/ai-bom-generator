import { describe, expect, test } from "bun:test";

import { parseReleaseVersion } from "./lib";
import {
  assertExactPathSet,
  assertReleaseMetadata,
  releaseMetadataPaths,
  type ReleaseMetadataDocuments,
} from "./metadata-lib";

const release = parseReleaseVersion("0.6.0");
const documents: ReleaseMetadataDocuments = {
  changelog: "# Changelog\n\n## v0.6.0\n\n- Current.\n\n## v0.5.0\n\n- Previous.\n",
  readme: "uses: 0disoft/ai-bom-generator@v0.6.0\n",
  releaseNotes: [
    "## Highlights",
    "",
    "- Current behavior.",
    "",
    "## Compatibility",
    "",
    "Existing consumers remain supported.",
    "",
    "## Rollback",
    "",
    "Publish a corrective patch.",
    "",
  ].join("\n"),
  lockVersion: "0.6.0",
};

describe("release metadata validation", () => {
  test("accepts one synchronized release metadata set", () => {
    expect(() => assertReleaseMetadata(release, documents)).not.toThrow();
    expect(releaseMetadataPaths(release)).toEqual([
      "CHANGELOG.md",
      "README.md",
      "docs/releases/v0.6.0.md",
      "pyproject.toml",
      "uv.lock",
    ]);
  });

  test("rejects stale version surfaces and incomplete notes", () => {
    const staleCases: ReleaseMetadataDocuments[] = [
      { ...documents, lockVersion: "0.5.0" },
      { ...documents, changelog: documents.changelog.replace("## v0.6.0", "## v0.5.1") },
      { ...documents, readme: documents.readme.replace("v0.6.0", "v0.5.0") },
      { ...documents, readme: `${documents.readme}Pin \`@v0.5.0\` for reproducibility.\n` },
      { ...documents, releaseNotes: documents.releaseNotes.replace("## Compatibility", "## Notes") },
      { ...documents, releaseNotes: documents.releaseNotes.replace("Existing consumers remain supported.", "") },
      { ...documents, releaseNotes: `Preamble.\n\n${documents.releaseNotes}` },
      { ...documents, releaseNotes: `${documents.releaseNotes}\n## Extra\n\nUnexpected.\n` },
    ];
    for (const stale of staleCases) {
      expect(() => assertReleaseMetadata(release, stale)).toThrow();
    }
  });

  test("requires the exact metadata path set", () => {
    const expected = releaseMetadataPaths(release);
    expect(() => assertExactPathSet([...expected].reverse(), expected, "metadata paths")).not.toThrow();
    expect(() => assertExactPathSet(expected.slice(1), expected, "metadata paths")).toThrow();
    expect(() => assertExactPathSet([...expected, "src/app.py"], expected, "metadata paths")).toThrow();
  });
});
