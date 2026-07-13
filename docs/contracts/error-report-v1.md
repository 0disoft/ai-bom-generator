# Error Report v1

Status: Draft

## Purpose

The optional hard-failure report lets automation inspect a failed generation
without parsing terminal prose. Its executable schema is
`schemas/aibom-error-report-v1.schema.json`.

## Contract

- `schema_version` is `ai-bom-error-report/v1`.
- `status` is always `failed`.
- `error.code` and `exit_code` use the stable CLI failure taxonomy.
- `error.stage` identifies the boundary that rejected the operation.
- `error.message` is diagnostic text, not a stable programmatic identifier.
- All fields use strict redaction regardless of the generated-artifact
  redaction mode.
- The report is written atomically and is not included in the successful output
  manifest.
- Successful and warning-only runs remove a stale report at the requested path.

## Review Blockers

- A secret-shaped value survives in any report field.
- A success or warning-only run leaves an older failure report reusable.
- A failure-report write changes the primary CLI exit code.
- Consumers treat free-form `error.message` as a stable error code.
