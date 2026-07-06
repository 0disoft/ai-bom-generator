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

- Command list and flag ownership: first command is expected to generate an AI-BOM from one model directory; exact command name is UNDECIDED.
- Exit-code taxonomy: success, success-with-warnings, invalid-input, collector-failure, exporter-failure, and internal-error need stable numeric codes.
- Machine-readable output contract: JSON summary must include output paths, warning counts, exporter, hash algorithm, and completeness status without embedding full source file contents.
- Config precedence and default behavior: explicit CLI flags override config; config filename and defaults remain UNDECIDED.
- Runtime compatibility floor: UNDECIDED

## Candidate CLI Shape

```text
ai-bom generate <model-directory> --config <path> --format <spdx-ai|cyclonedx-mlbom> --out <path> --json
```

The exact binary name, flag names, and output filenames remain draft until implementation starts.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
