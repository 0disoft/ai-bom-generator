# Runtime Flow

Status: Draft

## Boundary

Runtime flow covers one local CLI invocation or one GitHub Action job that wraps
the CLI. It does not include hosted registry workflows, long-running daemons, or
model serving.

## Runtime Flow

1. Parse command arguments or GitHub Action inputs.
2. Resolve the target model directory and explicit or discovered config path.
3. Validate config shape and warning policy.
4. Collect declared model metadata, dependency file references, prompt, dataset,
   eval, and training-code references from discovered or explicit config. Parse
   explicitly declared supported Python dependency files into package evidence.
   Select model artifacts from explicit include/exclude patterns and
   config-enabled artifact discovery defaults.
5. Apply fixed dependency-file and artifact collection budgets.
6. Hash selected model artifacts through one open file descriptor and reject
   artifacts that change before hashing completes.
7. Normalize evidence and absence information.
8. Run exporter mapping for the selected BOM family.
9. Validate exporter output when the selected format has an available schema or conformance check.
10. Write BOM, warning report, JSON summary, and generation manifest.
11. Treat the manifest as the commit marker for consumers that need to verify
    all generated JSON files belong to the same run.
12. Return success, success-with-warnings, or failure according to the exit-code contract.

## Quality Attributes

- Maintainability: changes must preserve source-of-truth documents.
- Security: runtime output must avoid embedding full private source files.
- Operability: CI users must be able to decide whether warnings fail the job.
- Recovery: failures should name the input, collector, or exporter stage that failed.
