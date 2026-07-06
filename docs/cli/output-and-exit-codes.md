# Output and Exit Codes

Status: Draft
Repository Type: cli-tool

## Purpose

Output must separate successful generation, warnings, and hard failures so CI can
act without reading prose.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Command contract: docs/cli/command-contract.md
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Draft Exit Categories

- success: BOM generated with no warnings.
- success-with-warnings: BOM generated, but metadata is incomplete or ambiguous.
- invalid-input: target directory, config, or flags are invalid.
- collector-failure: evidence could not be collected or hashed.
- exporter-failure: selected BOM output could not be produced or validated.
- internal-error: unexpected implementation failure.

## Proposed Numeric Codes

- `0`: generation succeeded. Warnings may be present when warning policy allows them.
- `10`: warning policy failed.
- `20`: invalid input.
- `30`: collector failure.
- `40`: exporter failure.
- `70`: internal error.

Argument parsing failures, including missing required flags and invalid choices,
must use `20` rather than argparse's default process status.

`success-with-warnings` should be a JSON summary status rather than a distinct
process code when `--warnings allow` is active.

## JSON Summary Fields

When `--summary -` is used, the same JSON summary object is written to stdout
while BOM and warning-report outputs are still written to their explicit paths.

- `schema_version`
- `tool.name`
- `tool.version`
- `status`
- `format`
- `bom_path`
- `warning_report_path`
- `hash_algorithm`
- `artifact_count`
- `warning_count`
- `completeness_status`
- `warnings`
- `elapsed_ms`
- `exit_code`

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
