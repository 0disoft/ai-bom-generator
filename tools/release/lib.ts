export const SOURCE_REPOSITORY = "0disoft/ai-bom-generator";
export const SMOKE_REPOSITORY = "0disoft/ai-bom-generator-action-smoke";
export const SOURCE_PROJECT = ".";
export const SMOKE_PROJECT = "../ai-bom-generator-action-smoke";

export type ReleaseVersion = {
  version: string;
  tag: string;
  majorTag: string;
};

export type WorkflowRun = {
  databaseId: number;
  status: string;
  conclusion: string;
  headBranch: string;
  headSha: string;
  url: string;
};

export type PublicationState = "available" | "complete" | "partial";

export function run(args: string[], cwd?: string): string {
  const result = Bun.spawnSync({ cmd: args, cwd, stdout: "pipe", stderr: "pipe" });
  if (result.exitCode !== 0) {
    throw new Error(new TextDecoder().decode(result.stderr).trim() || `${args[0]} exited ${result.exitCode}`);
  }
  return new TextDecoder().decode(result.stdout).trim();
}

export function optionalRun(args: string[], cwd?: string): string | undefined {
  const result = Bun.spawnSync({ cmd: args, cwd, stdout: "pipe", stderr: "pipe" });
  if (result.exitCode !== 0) return undefined;
  return new TextDecoder().decode(result.stdout).trim();
}

export function parseReleaseVersion(raw: string): ReleaseVersion {
  const match = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.exec(raw);
  if (!match) throw new Error(`expected strict MAJOR.MINOR.PATCH version, got ${JSON.stringify(raw)}`);
  return { version: raw, tag: `v${raw}`, majorTag: `v${match[1]}` };
}

export function optionValue(args: string[], name: string): string | undefined {
  const index = args.indexOf(name);
  if (index === -1) return undefined;
  const value = args[index + 1];
  if (!value || value.startsWith("--")) throw new Error(`${name} requires a value`);
  return value;
}

export function readDeclaredVersion(): ReleaseVersion {
  const raw = run([
    "uv", "run", "--no-sync", "--python", "3.12", "python", "-c",
    "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])",
  ], SOURCE_PROJECT);
  return parseReleaseVersion(raw);
}

export function requestedVersion(args: string[]): ReleaseVersion {
  const requested = optionValue(args, "--version");
  return requested ? parseReleaseVersion(requested) : readDeclaredVersion();
}

export function publicationState(pypiExists: boolean, releaseExists: boolean): PublicationState {
  if (!pypiExists && !releaseExists) return "available";
  if (pypiExists && releaseExists) return "complete";
  return "partial";
}

export function selectPublishRun(
  runs: WorkflowRun[],
  tag: string,
  releaseCommit: string,
): WorkflowRun | undefined {
  return runs.find((item) => item.headBranch === tag && item.headSha === releaseCommit);
}

export function selectSmokeRun(runs: WorkflowRun[], smokeHead: string): WorkflowRun | undefined {
  return runs.find((item) => item.headSha === smokeHead);
}

export function listWorkflowRuns(
  repository: string,
  workflow: string,
  limit = 20,
): WorkflowRun[] {
  return JSON.parse(
    run([
      "gh", "run", "list", "--repo", repository, "--workflow", workflow,
      "--limit", String(limit), "--json", "databaseId,status,conclusion,headBranch,headSha,url",
    ]),
  ) as WorkflowRun[];
}

export async function pypiVersionExists(version: string): Promise<boolean> {
  const response = await fetch(`https://pypi.org/pypi/ai-bom-generator/${version}/json`);
  if (response.ok) return true;
  if (response.status === 404) return false;
  throw new Error(`PyPI availability check returned ${response.status}`);
}

export async function waitForPublish(
  tag: string,
  releaseCommit: string,
  timeoutMs = 8 * 60 * 1000,
): Promise<WorkflowRun> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const publish = selectPublishRun(
      listWorkflowRuns(SOURCE_REPOSITORY, "publish-pypi.yml", 20),
      tag,
      releaseCommit,
    );
    if (publish?.status === "completed") {
      if (publish.conclusion !== "success") throw new Error(`PyPI publish failed: ${publish.url}`);
      return publish;
    }
    await Bun.sleep(5_000);
  }
  throw new Error(`timed out waiting for ${tag} PyPI publish`);
}

export function fetchReleaseTag(tag: string): string {
  run(["git", "fetch", "origin", "--tags", "--force"], SOURCE_PROJECT);
  return run(["git", "rev-list", "-n", "1", tag], SOURCE_PROJECT);
}

export function assertImmutableRelease(tag: string): { url: string } {
  const release = JSON.parse(
    run([
      "gh", "release", "view", tag, "--repo", SOURCE_REPOSITORY,
      "--json", "isDraft,isImmutable,isPrerelease,tagName,url",
    ]),
  ) as {
    isDraft: boolean;
    isImmutable: boolean;
    isPrerelease: boolean;
    tagName: string;
    url: string;
  };
  if (release.tagName !== tag || release.isDraft || release.isPrerelease || !release.isImmutable) {
    throw new Error(`${tag} is not a published immutable GitHub release`);
  }
  return { url: release.url };
}
