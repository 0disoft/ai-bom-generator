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

Explicit CLI flags override discovered or explicit config values. Explicit
`--config` paths override automatic config discovery. Environment variables are
out of MVP and should not be added until secret-redaction behavior and
precedence are designed.

## Config v1

`aibom.toml` is the approved MVP filename because it is local and keeps
configuration separate from model-card prose. When `--config` is omitted, the
CLI checks only `<model-directory>/aibom.toml`. It does not search parent
directories, alternate filenames, or environment variables. If the target-root
`aibom.toml` does not exist, the CLI uses inline defaults and reports missing
optional metadata as warnings.

Config schema v1 covers output format, warning policy, model metadata pointers,
artifact include and exclude patterns, artifact discovery opt-in, dependency
references, dataset references, prompt references, eval references, and training
references. The runtime validates discovered and explicit config files against
the packaged schema before output files are written.

Artifact discovery is disabled unless `[artifacts].discovery = true` appears in
the config. It is config-only in MVP; there is no CLI flag. Discovery adds
bounded defaults for common model artifact extensions: `.safetensors`, `.gguf`,
`.bin`, `.pt`, `.pth`, `.ckpt`, and `.onnx`. It excludes hidden, cache,
dependency, virtualenv, build, and Git metadata paths before hashing.

Artifact budget limits are fixed in MVP and are not config or CLI options yet:
256 candidate paths per include pattern after excludes, 16 GiB per artifact,
and 25 GiB total selected artifact bytes per run. A budget hit is reported in
the warning report and JSON summary, and the over-budget pattern or artifact is
skipped.

## Still UNDECIDED

- Format-specific dependency lockfile parsing.
- CLI override for artifact discovery.
- Configurable artifact budget overrides.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
