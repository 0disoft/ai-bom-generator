import { parseReleaseVersion } from "./lib";

const TARGET_REF = /^(\s*uses:\s*)0disoft\/ai-bom-generator@([^\s#]+)\s*$/gm;

export type SmokeRefUpdate = {
  changed: boolean;
  currentVersion: string;
  nextText: string;
};

export function updateSmokeActionRef(workflow: string, requestedVersion: string): SmokeRefUpdate {
  const target = parseReleaseVersion(requestedVersion);
  const matches = [...workflow.matchAll(TARGET_REF)];
  if (matches.length !== 1) {
    throw new Error(`expected exactly one ai-bom-generator Action ref, found ${matches.length}`);
  }
  const currentRef = matches[0][2];
  if (!currentRef.startsWith("v")) {
    throw new Error(`expected an exact vMAJOR.MINOR.PATCH Action ref, found ${currentRef}`);
  }
  const current = parseReleaseVersion(currentRef.slice(1));
  if (current.version === target.version) {
    return { changed: false, currentVersion: current.version, nextText: workflow };
  }
  const nextText = workflow.replace(
    TARGET_REF,
    `$1` + `0disoft/ai-bom-generator@${target.tag}`,
  );
  return { changed: true, currentVersion: current.version, nextText };
}

export function assertSoleStagedWorkflow(paths: string[], expectedPath: string): void {
  if (paths.length !== 1 || paths[0] !== expectedPath) {
    throw new Error(`expected only ${expectedPath} to be staged, found ${JSON.stringify(paths)}`);
  }
}
