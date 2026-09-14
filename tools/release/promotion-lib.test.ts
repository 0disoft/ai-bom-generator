import { expect, test } from "bun:test";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { promotionPushArgs } from "./promotion-lib";

test("promotion only accepts mutable channels and exact object IDs", () => {
  expect(promotionPushArgs("v0", "a".repeat(40)).at(-1)).toBe("--force-with-lease=refs/tags/v0:");
  expect(() => promotionPushArgs("v0.7.1", "a".repeat(40))).toThrow();
  expect(() => promotionPushArgs("v0", "HEAD")).toThrow();
  expect(() => promotionPushArgs("v0", "a".repeat(40), "HEAD")).toThrow();
});

test("promotion rejects concurrent creation and updates without changing the remote", () => {
  const dir = mkdtempSync(join(tmpdir(), "aibom-promotion-"));
  const remote = join(dir, "remote.git");
  const local = join(dir, "local");
  const git = (args: string[], cwd = local) => spawnSync("git", args, { cwd, encoding: "utf8" });
  const ok = (args: string[], cwd = local) => {
    const result = git(args, cwd);
    expect(result.status).toBe(0);
    return result.stdout.trim();
  };
  try {
    ok(["init", "--bare", remote], dir);
    ok(["init", local], dir);
    ok(["config", "user.name", "Synthetic Test"]);
    ok(["config", "user.email", "test@example.invalid"]);
    ok(["config", "commit.gpgsign", "false"]);
    ok(["remote", "add", "origin", remote]);
    ok(["commit", "--allow-empty", "-m", "first"]);
    const first = ok(["rev-parse", "HEAD"]);
    ok(["commit", "--allow-empty", "-m", "second"]);
    const second = ok(["rev-parse", "HEAD"]);
    ok(promotionPushArgs("v0", first).slice(1));
    expect(git(promotionPushArgs("v0", second).slice(1)).status).not.toBe(0);
    ok(promotionPushArgs("v0", second, first).slice(1));
    expect(git(promotionPushArgs("v0", first, first).slice(1)).status).not.toBe(0);
    expect(ok(["ls-remote", "origin", "refs/tags/v0"]).split(/\s+/)[0]).toBe(second);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
