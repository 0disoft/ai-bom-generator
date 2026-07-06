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

Numeric values are UNDECIDED.

## JSON Summary Fields

- exporter
- output_path
- warning_count
- warnings
- hash_algorithm
- artifact_count
- completeness_status
- elapsed_ms

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
