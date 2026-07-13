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
- Optionally declare a producer-owned generation marker for cross-file snapshot
  consistency.

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

An optional marker uses this shape:

```toml
[generation]
marker = ".aibom-generation.json"
```

The marker file follows `docs/adr/0004-producer-generation-marker.md`. It must
be a complete, target-root-local, non-symlink JSON file no larger than 4 KiB.
The producer enters `writing` before governed file changes and publishes a new
complete generation afterward. Unconfigured projects retain file-by-file
stability checks but do not claim cross-file generation consistency.

`[output].format` may be `cyclonedx-json-1.7` or `spdx-ai`. The SPDX option is a
preview mapping to SPDX 3.0.1 AI Profile terms and marks conformance as
partial. It records unavailable or unsupported SPDX AI fields in the generated
BOM instead of inventing source evidence.

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

- Support for dependency formats beyond `uv.lock` and requirements files.
- CLI override for artifact discovery.
- Configurable artifact budget overrides.

## Review Blockers

- A command changes without updating help, examples, output, and exit-code expectations.
- JSON output exposes generated or existing file contents.
- Runtime compatibility changes without smoke validation.
