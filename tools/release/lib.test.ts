import { describe, expect, test } from "bun:test";

import {
  optionValue,
  parseReleaseVersion,
  publicationState,
  selectPublishRun,
  selectSmokeRun,
  type WorkflowRun,
} from "./lib";

const runs: WorkflowRun[] = [
  {
    databaseId: 2,
    status: "completed",
    conclusion: "success",
    headBranch: "v0.6.0",
    headSha: "release-sha",
    url: "https://example.invalid/run/2",
  },
  {
    databaseId: 1,
    status: "completed",
    conclusion: "success",
    headBranch: "main",
    headSha: "smoke-sha",
    url: "https://example.invalid/run/1",
  },
];

describe("parseReleaseVersion", () => {
  test("derives immutable and moving tags", () => {
    expect(parseReleaseVersion("0.6.0")).toEqual({
      version: "0.6.0",
      tag: "v0.6.0",
      majorTag: "v0",
    });
    expect(parseReleaseVersion("12.3.4").majorTag).toBe("v12");
  });

  test("rejects loose, prerelease, and zero-padded versions", () => {
    for (const value of ["v0.6.0", "0.6", "0.6.0-rc.1", "00.6.0", "0.06.0"]) {
      expect(() => parseReleaseVersion(value)).toThrow();
    }
  });
});

test("publication state distinguishes resumable completion from partial state", () => {
  expect(publicationState(false, false)).toBe("available");
  expect(publicationState(true, true)).toBe("complete");
  expect(publicationState(true, false)).toBe("partial");
  expect(publicationState(false, true)).toBe("partial");
});

test("workflow selectors bind runs to the exact release and smoke commits", () => {
  expect(selectPublishRun(runs, "v0.6.0", "release-sha")?.databaseId).toBe(2);
  expect(selectPublishRun(runs, "v0.6.0", "wrong-sha")).toBeUndefined();
  expect(selectSmokeRun(runs, "smoke-sha")?.databaseId).toBe(1);
  expect(selectSmokeRun(runs, "wrong-sha")).toBeUndefined();
});

test("optionValue fails closed on missing values", () => {
  expect(optionValue(["--version", "0.6.0"], "--version")).toBe("0.6.0");
  expect(() => optionValue(["--version"], "--version")).toThrow();
  expect(() => optionValue(["--version", "--apply"], "--version")).toThrow();
});
