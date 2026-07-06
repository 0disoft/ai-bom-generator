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

## Config v1 Candidate

`aibom.toml` is the leading filename candidate because it is explicit, local, and
keeps configuration separate from model-card prose. The proposed v1 schema should
cover output format, warning policy, model metadata pointers, artifact include
and exclude patterns, dependency lockfiles, dataset references, prompt references,
eval references, and training references.

## Still UNDECIDED

- Config filename approval.
- Config schema approval.
- Whether lockfile discovery is automatic or config-driven.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
