# Config Contract v1 Draft

Status: Draft
Owner: UNASSIGNED

## Purpose

This file defines the proposed config contract for AI-BOM Generator. It is not
approved until the config ADR accepts the filename and schema.

## Filename Candidate

`aibom.toml` is the leading filename candidate.

## Required Properties

- `schema_version`: config schema version.
- `output.format`: selected exporter format.

## Candidate Sections

- `warning_policy`: missing metadata and unsupported field behavior.
- `model`: declared model metadata and model-card path.
- `artifacts`: include and exclude patterns for model artifacts and checkpoints.
- `dependencies`: lockfile references and declared package-manager type.
- `datasets`: declared dataset references.
- `prompts`: declared prompt references, with content inclusion disabled by default.
- `evals`: declared eval artifact references.
- `training`: declared training-code or pipeline references.

## Precedence

Explicit CLI flags override config values. Environment-variable config is out of
MVP until redaction and precedence behavior are explicitly designed.

## Review Blockers

- Config accepts implicit secrets or network credentials without a redaction policy.
- Config requires prompt, dataset, eval, or model-card contents to be copied into output.
- Config permits target-root escape or symlink escape by default.
