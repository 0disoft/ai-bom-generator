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
- Load explicit config, or discover `<model-directory>/aibom.toml` when
  `--config` is omitted.
- Collect model, dependency, dataset, prompt, eval, and training references.
- Hash selected artifacts.
- Export the selected BOM format.
- Report warnings and failure reasons.
- Emit JSON summary for automation.

## Still UNDECIDED

- Parent-directory or alternate-filename config discovery.

## Approved Baseline

- Runtime compatibility floor: Python 3.12.
- Binary name: `ai-bom`.
- Explicit config filename: `aibom.toml`.
- Config schema: AI-BOM config schema v1.
- CLI adapter: `argparse`, isolated from application and domain layers.
- First exporter: CycloneDX JSON 1.7.
- Explicit Python dependency parsing: `uv.lock` and requirements files selected
  through `[[dependencies]]`; automatic discovery, recursive includes, and
  dependency resolution remain out of scope.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
