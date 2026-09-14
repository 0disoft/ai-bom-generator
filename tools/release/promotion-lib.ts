export function promotionPushArgs(majorTag: string, commit: string, expected?: string): string[] {
  if (!/^v(?:0|[1-9]\d*)$/.test(majorTag)) throw new Error("invalid mutable channel");
  if (!/^[a-f0-9]{40}$/.test(commit) || (expected !== undefined && !/^[a-f0-9]{40}$/.test(expected))) {
    throw new Error("invalid promotion object ID");
  }
  const ref = `refs/tags/${majorTag}`;
  return ["git", "push", "origin", `${commit}:${ref}`, `--force-with-lease=${ref}:${expected ?? ""}`];
}
