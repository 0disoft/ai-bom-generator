# Product Specification

Status: Draft
Owner: UNASSIGNED

## Purpose

This document defines the first usable shape of AI-BOM Generator.

AI-BOM Generator reads a local model project directory and creates a machine-readable
bill of materials for AI artifacts. It focuses on evidence collection and exporter
mapping, not on proving that the evidence is complete or legally sufficient.

## Source of Truth

- Product decision: Evidence-first AI/ML BOM generator for local model project directories.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## MVP Input

- A target model directory.
- Optional explicit config file path. The approved MVP config filename and
  schema are `aibom.toml` and config schema v1. When no explicit config path is
  provided, the CLI discovers only `<model-directory>/aibom.toml`.
- Model card or model metadata file when present. MVP discovers an in-root
  `MODEL_CARD.md` path as evidence without copying or parsing its contents.
- Model artifact or checkpoint files selected by explicit patterns.
- Dependency files declared explicitly in config. The Python-first parser reads
  bounded `uv.lock` and requirements files into normalized package evidence
  while preserving the original file reference. Automatic discovery, recursive
  includes, dependency resolution, downloads, and completeness claims remain
  out of scope.
- Dataset, prompt template, eval dataset, and training script references from
  discovered or explicit config.
- Git commit reference when the target project is a Git repository.

## MVP Output

- One primary BOM file in a standards-backed format.
- A warning report for missing or ambiguous metadata.
- Stable JSON output for automation.
- Non-zero exit code for invalid input, unreadable required files, digest failures, or invalid exporter output.

## Initial Collector Boundaries

- Collects file paths, hashes, declared metadata, references, and warnings.
- Does not inspect private dataset contents unless a future explicit mode is designed.
- Does not infer dataset licenses from names, URLs, or comments.
- Does not claim model safety, bias status, vulnerability status, or regulatory compliance.
- Does not perform network access, telemetry, hidden caching, or target-directory mutation in MVP.

## Exporter Direction

SPDX AI and CycloneDX ML-BOM are the candidate output families because they already
model AI artifacts, datasets, configurations, and provenance-oriented metadata.
CycloneDX JSON 1.7 is the approved first implemented exporter and must remain
schema-validated. The `spdx-ai` exporter is an approved preview mapping to SPDX
3.0.1 AI Profile terms with partial conformance only; it must not fabricate
unavailable supplier, download, release-time, safety, metric, or sensitive-data
metadata.

## Required Decisions Before Implementation

- Runtime: Python 3.12 is approved.
- CLI adapter: `argparse` is approved, with application and domain layers kept framework-independent.
- Repository license: Apache-2.0 is approved.
- Package metadata: `pyproject.toml` with setuptools build backend is approved.
- Schema validation dependency: `jsonschema>=4.25,<5` is approved.
- Python requirement parser dependency: `packaging>=24,<27` is approved.
- Project lockfile: `uv.lock` is approved.
- Config filename and schema: `aibom.toml` plus config schema v1 is approved.
  Automatic config discovery is limited to `<model-directory>/aibom.toml`.
- First exporter: CycloneDX JSON 1.7 is implemented first and must stay schema-validated.
- Second exporter: `spdx-ai` emits an SPDX 3.0.1 AI Profile preview with local
  preview contract validation and explicit unsupported-field notes.
- Lockfile support set: explicit config-declared dependency file references,
  with bounded local parsing for `uv.lock` and requirements files. Parsing may
  be disabled per reference with `parse = false`.
- Model artifact discovery defaults: config opt-in discovery is approved.
- Redaction default: strict redaction is approved for CLI and terminal output.
- Validation needed before merge: VALIDATION.md.

## Review Blockers

- The change treats generated BOM output as proof of provenance.
- The change adds implicit network access or hosted registry behavior.
- The change reads dataset contents without an explicit privacy and retention decision.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
