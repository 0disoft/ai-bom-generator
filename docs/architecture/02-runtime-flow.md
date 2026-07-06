# Runtime Flow

Status: Draft

## Boundary

Runtime flow covers one local CLI invocation or one GitHub Action job that wraps
the CLI. It does not include hosted registry workflows, long-running daemons, or
model serving.

## Runtime Flow

1. Parse command arguments or GitHub Action inputs.
2. Resolve the target model directory and config path.
3. Validate config shape and warning policy.
4. Discover supported metadata, lockfile, artifact, prompt, dataset, eval, and training-code references.
5. Hash selected model artifacts.
6. Normalize evidence and absence information.
7. Run exporter mapping for the selected BOM family.
8. Validate exporter output when the selected format has an available schema or conformance check.
9. Write BOM, warning report, and JSON summary.
10. Return success, success-with-warnings, or failure according to the exit-code contract.

## Quality Attributes

- Maintainability: changes must preserve source-of-truth documents.
- Security: runtime output must avoid embedding full private source files.
- Operability: CI users must be able to decide whether warnings fail the job.
- Recovery: failures should name the input, collector, or exporter stage that failed.
