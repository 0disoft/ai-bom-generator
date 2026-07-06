# Shell Completion

Status: Draft
Repository Type: cli-tool

## Purpose

Shell completion should help users discover stable commands, flags, and enum
values without implying that arbitrary file discovery is safe or complete.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Command contract: docs/cli/command-contract.md
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Completion Boundary

- Complete command names and stable flag names after the CLI contract is implemented.
- Complete supported exporter names from the implemented exporter registry.
- Do not auto-complete secrets, tokens, private URLs, or dataset contents.
- File path completion should be delegated to the shell when possible.

## Still UNDECIDED

- Supported shells.
- Completion generation command.
- Whether completions are packaged or generated on demand.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
