# CLI Configuration

Status: Draft
Repository Type: cli-tool

## Purpose

Configuration tells AI-BOM Generator which project metadata and artifacts to
collect. It must make explicit references easy and avoid broad hidden discovery.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Command contract: docs/cli/command-contract.md
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Draft Config Responsibilities

- Declare model metadata and a model-card path without copying model-card
  contents into generated output.
- Select model artifact paths or globs.
- Declare dataset references.
- Declare prompt template references.
- Declare eval artifact references.
- Declare training-code references.
- Choose exporter and output path when not supplied by CLI flags.
- Configure warning policy.

## Precedence

Explicit CLI flags should override config values. Environment variables are
out of MVP and should not be added until secret-redaction behavior and precedence
are designed.

## Config v1

`aibom.toml` is the approved MVP filename for explicit config files because it
is local and keeps configuration separate from model-card prose. Config schema
v1 covers output format, warning policy, model metadata pointers, artifact
include and exclude patterns, dependency references, dataset references, prompt
references, eval references, and training references. The runtime validates the
config against the packaged schema before output files are written.

## Still UNDECIDED

- Automatic config discovery.
- Format-specific dependency lockfile parsing.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
