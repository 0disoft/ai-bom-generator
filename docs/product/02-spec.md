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
- Optional config file path. The leading filename candidate is `aibom.toml`, pending ADR approval.
- Model card or model metadata file when present.
- Model artifact or checkpoint files selected by explicit patterns.
- Dependency lockfiles from an initial supported set.
- Dataset, prompt template, eval dataset, and training script references from explicit config.
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
CycloneDX JSON 1.7 is the leading first-exporter candidate because its JSON schema
can support contract validation early. The first implemented exporter remains
UNDECIDED until mapping fixtures are written and approved by ADR.

## Required Decisions Before Implementation

- Runtime: Python 3.12 is approved.
- CLI adapter: `argparse` is approved, with application and domain layers kept framework-independent.
- Repository license: Apache-2.0 is approved.
- Package metadata: `pyproject.toml` with setuptools build backend is approved.
- Schema validation dependency: `jsonschema>=4.25,<5` is approved.
- Project lockfile: `uv.lock` is approved.
- Config filename and schema: `aibom.toml` plus config schema v1 is proposed, not approved.
- First exporter: CycloneDX JSON 1.7 is implemented first and must stay schema-validated.
- Lockfile support set: UNDECIDED.
- Model artifact discovery defaults: UNDECIDED.
- Redaction default: strict redaction is proposed, not approved.
- Validation needed before merge: VALIDATION.md.

## Review Blockers

- The change treats generated BOM output as proof of provenance.
- The change adds implicit network access or hosted registry behavior.
- The change reads dataset contents without an explicit privacy and retention decision.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
