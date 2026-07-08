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

- Command list and flag ownership: `ai-bom --version` reports the installed package version, and `ai-bom generate` generates an AI-BOM from one model directory.
- Exit-code taxonomy: success, success-with-warnings, invalid-input, collector-failure, exporter-failure, and internal-error need stable numeric codes.
- Machine-readable output contract: JSON summary must include output paths, warning counts, exporter, hash algorithm, and completeness status without embedding full source file contents.
- Config precedence and default behavior: explicit CLI flags override config; environment-variable config is out of MVP until redaction and precedence are designed.
- Runtime compatibility floor: Python 3.12.
- CLI adapter boundary: `argparse` may own argument parsing and exit-code translation, but application and domain layers must not import it.

## Candidate CLI Shape

```text
ai-bom --version

ai-bom generate <model-directory>
  --config <path>
  --format <cyclonedx-json-1.7|spdx-ai>
  --output <path>
  --warning-report <path>
  --summary <path|->
  --manifest <path>
  --warnings <allow|fail>
  --redaction <strict|off>
```

The exact binary name, flag names, accepted formats, and output filename defaults
are implemented for the current MVP CLI. MVP prefers explicit output paths over
silently writing into the target model directory. Generated output paths must
resolve outside the target model directory and must not overlap each other.
Overlapping output paths include identical resolved paths and parent-child
resolved paths.
The CLI writes a generation manifest for each successful output set. When
`--manifest` is omitted, the manifest defaults to `<summary>.manifest.json` for
file summaries and `<output>.manifest.json` when `--summary -` writes the summary
to stdout. The manifest records a run-unique generation id plus role, path,
size, and SHA-256 digest entries for every final JSON output in the set.
When `--format` is omitted, the explicit config file's `[output].format` value is
used. If neither CLI nor config declares a format, `cyclonedx-json-1.7` is used
as the current executable default.
When `--warnings` is omitted, the explicit config file's
`[warning_policy].missing_metadata` value is used. Config `warn` maps to the
executable `allow` behavior and config `fail` maps to the executable `fail`
behavior.
Config files are validated against AI-BOM config schema v1 before new final
output files are written. After output-path validation succeeds, stale files at
the requested generated-output destinations are removed before config loading,
collection, or export starts, so a failed run does not leave previous-run JSON
where callers expect current-run output.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
