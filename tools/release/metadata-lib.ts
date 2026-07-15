import { readFileSync } from "node:fs";
import { join } from "node:path";

import {
  SOURCE_PROJECT,
  type ReleaseVersion,
  readDeclaredVersion,
  run,
} from "./lib";

export type ReleaseMetadataDocuments = {
  changelog: string;
  readme: string;
  releaseNotes: string;
  lockVersion: string;
};

export type ValidatedReleaseMetadata = {
  release: ReleaseVersion;
  notesPath: string;
  notes: string;
  paths: string[];
};

const STATIC_METADATA_PATHS = ["CHANGELOG.md", "README.md", "pyproject.toml", "uv.lock"];
const RELEASE_SECTIONS = ["Highlights", "Compatibility", "Rollback"];
const ACTION_REF = /@(v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))/g;
const CHANGELOG_RELEASE = /^## (v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))\s*$/m;
const RELEASE_HEADING = /^## ([^\r\n]+?)[ \t]*\r?$/gm;

export function releaseMetadataPaths(release: ReleaseVersion): string[] {
  return [...STATIC_METADATA_PATHS, `docs/releases/${release.tag}.md`].sort();
}

export function assertReleaseMetadata(
  release: ReleaseVersion,
  documents: ReleaseMetadataDocuments,
): void {
  if (documents.lockVersion !== release.version) {
    throw new Error(`uv.lock version ${documents.lockVersion} does not match ${release.version}`);
  }

  const changelogRelease = CHANGELOG_RELEASE.exec(documents.changelog)?.[1];
  if (changelogRelease !== release.tag) {
    throw new Error(`first CHANGELOG release is ${changelogRelease ?? "missing"}, expected ${release.tag}`);
  }

  const actionRefs = [...documents.readme.matchAll(ACTION_REF)].map((match) => match[1]);
  if (actionRefs.length === 0 || actionRefs.some((ref) => ref !== release.tag)) {
    throw new Error(
      `README exact Action refs must all use ${release.tag}, found ${JSON.stringify(actionRefs)}`,
    );
  }

  const headings = [...documents.releaseNotes.matchAll(RELEASE_HEADING)];
  const headingNames = headings.map((match) => match[1]);
  if (JSON.stringify(headingNames) !== JSON.stringify(RELEASE_SECTIONS)) {
    throw new Error(
      `release notes sections must be exactly ${JSON.stringify(RELEASE_SECTIONS)}, ` +
      `found ${JSON.stringify(headingNames)}`,
    );
  }
  if (documents.releaseNotes.slice(0, headings[0].index).trim()) {
    throw new Error("release notes must start with the Highlights section");
  }
  for (const [index, section] of RELEASE_SECTIONS.entries()) {
    const heading = headings[index];
    const contentStart = (heading.index ?? 0) + heading[0].length;
    const nextSection = headings[index + 1]?.index;
    const content = documents.releaseNotes.slice(
      contentStart,
      nextSection,
    ).trim();
    if (!content) throw new Error(`## ${section} section must not be empty`);
  }
}

export function assertExactPathSet(actual: string[], expected: string[], label: string): void {
  const normalizedActual = [...new Set(actual.map(normalizeGitPath))].sort();
  const normalizedExpected = [...new Set(expected.map(normalizeGitPath))].sort();
  if (JSON.stringify(normalizedActual) !== JSON.stringify(normalizedExpected)) {
    throw new Error(
      `${label} must be exactly ${JSON.stringify(normalizedExpected)}, found ${JSON.stringify(normalizedActual)}`,
    );
  }
}

export function gitPaths(args: string[]): string[] {
  const output = run(args, SOURCE_PROJECT);
  return output ? output.split(/\r?\n/).filter(Boolean).map(normalizeGitPath) : [];
}

export function changedMetadataPaths(): string[] {
  return [
    ...gitPaths(["git", "diff", "--name-only"]),
    ...gitPaths(["git", "diff", "--cached", "--name-only"]),
    ...gitPaths(["git", "ls-files", "--others", "--exclude-standard"]),
  ];
}

export function validateReleaseMetadata(
  requested: ReleaseVersion = readDeclaredVersion(),
): ValidatedReleaseMetadata {
  const declared = readDeclaredVersion();
  if (declared.version !== requested.version) {
    throw new Error(`pyproject.toml version ${declared.version} does not match ${requested.version}`);
  }
  const notesPath = `docs/releases/${requested.tag}.md`;
  const notes = readFileSync(join(SOURCE_PROJECT, notesPath), "utf8");
  assertReleaseMetadata(requested, {
    changelog: readFileSync(join(SOURCE_PROJECT, "CHANGELOG.md"), "utf8"),
    readme: readFileSync(join(SOURCE_PROJECT, "README.md"), "utf8"),
    releaseNotes: notes,
    lockVersion: readLockVersion(),
  });
  return {
    release: requested,
    notesPath,
    notes: notes.trim(),
    paths: releaseMetadataPaths(requested),
  };
}

function readLockVersion(): string {
  return run([
    "uv", "run", "--no-sync", "--python", "3.12", "python", "-c",
    "import tomllib; d=tomllib.load(open('uv.lock','rb')); v=[p.get('version') for p in d.get('package',[]) if p.get('name')=='ai-bom-generator' and p.get('source',{}).get('editable')=='.']; assert len(v)==1 and isinstance(v[0],str); print(v[0])",
  ], SOURCE_PROJECT);
}

function normalizeGitPath(path: string): string {
  return path.replaceAll("\\", "/");
}
