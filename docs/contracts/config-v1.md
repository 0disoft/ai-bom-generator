# Config Contract v1

Status: Accepted for MVP runtime validation
Owner: UNASSIGNED

## Purpose

This file defines the approved MVP config contract for explicit config files.

The source contract schema lives at `schemas/aibom-config-v1.schema.json`.
The packaged runtime copy lives at
`src/ai_bom_generator/config/schema/aibom-config-v1.schema.json` and must stay
byte-equivalent at the JSON object level.

## Filename Candidate

`aibom.toml` is the approved filename for explicit MVP config examples and
fixtures. When `--config` is omitted, the CLI discovers only
`<model-directory>/aibom.toml`. It does not search parent directories, alternate
filenames, or environment variables. If the target-root `aibom.toml` is absent,
the CLI uses inline defaults and reports missing optional metadata as warnings.

## Required Properties

- `schema_version`: config schema version.
- `output.format`: selected exporter format.

## Candidate Sections

- `warning_policy`: missing metadata and unsupported field behavior.
- `output.format`: `cyclonedx-json-1.7` or `spdx-ai`.
- `model`: declared model metadata and model-card path.
- `artifacts`: include and exclude patterns for model artifacts and checkpoints,
  plus explicit opt-in artifact discovery.
- `dependencies`: explicit dependency-file references, scalar metadata, and an
  optional `parse` boolean.
- `datasets`: declared dataset references.
- `prompts`: declared prompt references, with content inclusion disabled by default.
- `evals`: declared eval artifact references.
- `training`: declared training-code or pipeline references.

## Supported Field Values

The executable implementation collects scalar string, number, and boolean values
from metadata and reference sections. Structured values such as arrays or nested
tables are ignored with an `UNSUPPORTED_CONFIG_FIELD` warning until the field is
explicitly modeled.

The runtime schema validates section shape, config version, artifact pattern
types, artifact discovery opt-in type, warning-policy field names and values,
known top-level sections, and known path fields before output files are written.
It intentionally allows
unknown nested values in metadata/reference
objects so the collector can emit `UNSUPPORTED_CONFIG_FIELD` warnings instead of
silently dropping user intent.

## Artifact Discovery

Artifact discovery is disabled by default. `[artifacts].discovery = true` is the
only MVP opt-in control; there is no CLI flag. When enabled, the collector adds
bounded default model artifact patterns for `.safetensors`, `.gguf`, `.bin`,
`.pt`, `.pth`, `.ckpt`, and `.onnx` files. Explicit `[artifacts].include`
patterns may still be used with discovery.

Discovery applies built-in excludes for hidden, cache, dependency, virtualenv,
build, and Git metadata paths before hashing. Discovery still uses the artifact
match-count, single-file byte, total-byte, target-root, symlink, and
no-fabrication warning policies.

## Precedence

Explicit CLI flags override config values. Explicit `--config` paths override
automatic discovery. When `--format` is omitted, the executable implementation
uses `[output].format` from the discovered or explicit config file and falls
back to `cyclonedx-json-1.7` when the config does not declare an output format.
When `--warnings` is omitted, `[warning_policy].missing_metadata = "warn"` maps
to the executable `allow` behavior and `"fail"` maps to the executable `fail`
behavior. The CLI `--warnings` flag overrides this config value.
Environment-variable config is out of MVP until redaction and precedence
behavior are explicitly designed.

## Dependency Lockfiles

Dependency-file intake is config-driven. Every `[[dependencies]]` entry keeps
its declared file path and scalar metadata as evidence. Supported Python files
are also parsed unless `parse = false`:

- `type = "uv"` or an undeclared type with path `uv.lock` parses the TOML
  `package` array.
- `type = "pip"` or `type = "requirements"` parses PEP 508 requirement lines,
  including exact pins, ranges, markers, extras, direct URLs, continuations,
  and hash options.
- When `type` is absent, `requirements*.txt` and `requirements.lock` paths use
  the requirements parser.

Requirements-file includes, constraints, editable installs, local paths,
dependency resolution, package downloads, and automatic discovery are not
followed. Unsupported or malformed entries produce warnings and no fabricated
package components. Package-lock, Poetry, Conda, and other formats remain
unsupported.

## Review Blockers

- Config accepts implicit secrets or network credentials without a redaction policy.
- Config requires prompt, dataset, eval, or model-card contents to be copied into output.
- Config permits target-root escape or symlink escape by default.
