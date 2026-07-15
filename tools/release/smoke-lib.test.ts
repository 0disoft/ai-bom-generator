import { expect, test } from "bun:test";

import { assertSoleStagedWorkflow, updateSmokeActionRef } from "./smoke-lib";

const workflow = `jobs:
  smoke:
    steps:
      - uses: actions/checkout@v7.0.0
      - id: ai-bom
        uses: 0disoft/ai-bom-generator@v0.5.0
`;

test("updates the one exact ai-bom-generator Action ref", () => {
  const result = updateSmokeActionRef(workflow, "0.6.0");
  expect(result.changed).toBeTrue();
  expect(result.currentVersion).toBe("0.5.0");
  expect(result.nextText).toContain("uses: 0disoft/ai-bom-generator@v0.6.0");
  expect(result.nextText).toContain("uses: actions/checkout@v7.0.0");
});

test("is idempotent when the workflow already uses the requested version", () => {
  const current = workflow.replace("@v0.5.0", "@v0.6.0");
  expect(updateSmokeActionRef(current, "0.6.0")).toEqual({
    changed: false,
    currentVersion: "0.6.0",
    nextText: current,
  });
});

test("rejects mutable, branch, missing, and duplicate target refs", () => {
  for (const ref of ["v0", "main", "v0.6.0-rc.1"]) {
    expect(() => updateSmokeActionRef(workflow.replace("v0.5.0", ref), "0.6.0")).toThrow();
  }
  expect(() => updateSmokeActionRef("jobs: {}\n", "0.6.0")).toThrow();
  expect(() => updateSmokeActionRef(`${workflow}${workflow}`, "0.6.0")).toThrow();
});

test("accepts only the one expected staged workflow", () => {
  const expected = ".github/workflows/ai-bom-release-smoke.yml";
  expect(() => assertSoleStagedWorkflow([expected], expected)).not.toThrow();
  expect(() => assertSoleStagedWorkflow([], expected)).toThrow();
  expect(() => assertSoleStagedWorkflow([expected, "README.md"], expected)).toThrow();
  expect(() => assertSoleStagedWorkflow(["README.md"], expected)).toThrow();
});
