# CLI Tool

Status: Draft
Repository Type: cli-tool

## Purpose

The CLI is the primary AI-BOM Generator interface. It should work locally and in
CI without requiring a hosted service.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Command contract: docs/cli/command-contract.md
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## CLI Responsibilities

- Resolve target model directory.
- Load explicit config.
- Collect model, dependency, dataset, prompt, eval, and training references.
- Hash selected artifacts.
- Export the selected BOM format.
- Report warnings and failure reasons.
- Emit JSON summary for automation.

## Still UNDECIDED

- Binary name.
- Config filename.
- First exporter.
- Runtime compatibility floor: UNDECIDED

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
