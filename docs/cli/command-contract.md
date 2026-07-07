# Command Contract

Status: Draft
Repository Type: cli-tool

## Repository Type Contract

This repository type owns command behavior, arguments, flags, config loading, exit codes, terminal output, JSON output, runtime compatibility, and shell integration contracts.

## Source of Truth

- Product decision: AI-BOM Generator is a local evidence collector and BOM exporter.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Decisions

- Command list and flag ownership: first command is expected to generate an AI-BOM from one model directory. `ai-bom generate` is the leading command-name candidate, pending ADR approval.
- Exit-code taxonomy: success, success-with-warnings, invalid-input, collector-failure, exporter-failure, and internal-error need stable numeric codes.
- Machine-readable output contract: JSON summary must include output paths, warning counts, exporter, hash algorithm, and completeness status without embedding full source file contents.
- Config precedence and default behavior: explicit CLI flags override config; environment-variable config is out of MVP until redaction and precedence are designed.
- Runtime compatibility floor: Python 3.12.
- CLI adapter boundary: `argparse` may own argument parsing and exit-code translation, but application and domain layers must not import it.

## Candidate CLI Shape

```text
ai-bom generate <model-directory>
  --config <path>
  --format <cyclonedx-json-1.7|spdx-ai>
  --output <path>
  --warning-report <path>
  --summary <path|->
  --warnings <allow|fail>
  --redaction <strict|off>
```

The exact binary name, flag names, accepted formats, and output filename defaults
remain draft until implementation starts. MVP should prefer explicit output paths
over silently writing into the target model directory. Generated output paths
must resolve outside the target model directory and must not overlap each other.
Overlapping output paths include identical resolved paths and parent-child
resolved paths.
When `--format` is omitted, the explicit config file's `[output].format` value is
used. If neither CLI nor config declares a format, `cyclonedx-json-1.7` is used
as the current executable default.
When `--warnings` is omitted, the explicit config file's
`[warning_policy].missing_metadata` value is used. Config `warn` maps to the
executable `allow` behavior and config `fail` maps to the executable `fail`
behavior.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
