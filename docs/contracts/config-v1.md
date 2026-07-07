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
fixtures. The CLI does not perform implicit config discovery yet; callers pass
the config path with `--config`.

## Required Properties

- `schema_version`: config schema version.
- `output.format`: selected exporter format.

## Candidate Sections

- `warning_policy`: missing metadata and unsupported field behavior.
- `model`: declared model metadata and model-card path.
- `artifacts`: include and exclude patterns for model artifacts and checkpoints.
- `dependencies`: explicit dependency lockfile references and scalar metadata.
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
types, warning-policy values, and known path fields before output files are
written. It intentionally allows unknown nested values in metadata/reference
objects so the collector can emit `UNSUPPORTED_CONFIG_FIELD` warnings instead of
silently dropping user intent.

## Precedence

Explicit CLI flags override config values. When `--format` is omitted, the
executable implementation uses `[output].format` from the explicit config file
and falls back to `cyclonedx-json-1.7` when the config does not declare an output
format.
When `--warnings` is omitted, `[warning_policy].missing_metadata = "warn"` maps
to the executable `allow` behavior and `"fail"` maps to the executable `fail`
behavior. The CLI `--warnings` flag overrides this config value.
Environment-variable config is out of MVP until redaction and precedence
behavior are explicitly designed.

## Dependency Lockfiles

MVP dependency lockfile intake is config-driven. The tool records declared
dependency file paths and scalar metadata. It does not automatically discover,
parse, or claim completeness for `uv.lock`, `requirements*.txt`, package-lock,
poetry, conda, or other lockfile formats yet.

## Review Blockers

- Config accepts implicit secrets or network credentials without a redaction policy.
- Config requires prompt, dataset, eval, or model-card contents to be copied into output.
- Config permits target-root escape or symlink escape by default.
