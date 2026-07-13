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

`ai-bom --version` writes the installed `ai-bom-generator` package version to
stdout, writes nothing to stderr, and exits with `0`.

`success-with-warnings` should be a JSON summary status rather than a distinct
process code when `--warnings allow` is active.

## JSON Summary Fields

When `--summary -` is used, the same JSON summary object is written to stdout
while BOM and warning-report outputs are still written to their explicit paths.
Requested JSON files are staged in destination-local temporary files before
final replacement. Generation failures before commit preserve the previous
output set. The commit phase is serialized by a stable manifest-adjacent lock;
if final replacement raises a handled error, the writer restores the previous
files and removes the current run's staged temporary files before returning an
internal error.
The generation manifest is replaced last. Consumers that need transaction-level
confidence should treat BOM, warning-report, and summary files as current only
when the manifest exists with `schema_version` `ai-bom-output-manifest/v1`,
`status` `committed`, and matching path, size, and SHA-256 entries for the
expected output files.

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

Supported BOM formats are `cyclonedx-json-1.7` and `spdx-ai`. The SPDX output
is JSON-LD-shaped and validates against the local
`aibom-spdx-ai-preview.schema.json` contract before files are committed.

## Generation Manifest Fields

- `schema_version`
- `generation_id`
- `status`
- `files[].role`
- `files[].path`
- `files[].sha256`
- `files[].size_bytes`

## Hard-Failure Report Fields

When `--error-report <path>` is provided, exit codes `20`, `30`, `40`, and `70`
write a separate JSON object validated by
`schemas/aibom-error-report-v1.schema.json`:

- `schema_version`: `ai-bom-error-report/v1`
- `tool.name`
- `tool.version`
- `status`: `failed`
- `error.code`: `INVALID_INPUT`, `COLLECTOR_FAILURE`, `EXPORTER_FAILURE`, or
  `INTERNAL_ERROR`
- `error.stage`
- `error.message`
- `exit_code`

Every field is strict-redacted even when `--redaction off` was requested.
Success and warning-policy exit code `10` do not fabricate failure reports and
remove a stale requested report before generation.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
