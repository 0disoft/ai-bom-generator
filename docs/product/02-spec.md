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
- Optional config file path, exact filename UNDECIDED.
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

## Exporter Direction

SPDX AI and CycloneDX ML-BOM are the candidate output families because they already
model AI artifacts, datasets, configurations, and provenance-oriented metadata.
The first implemented exporter remains UNDECIDED until mapping fixtures are written.

## Required Decisions Before Implementation

- Runtime and packaging: UNDECIDED.
- Config filename and schema: UNDECIDED.
- First exporter: UNDECIDED between SPDX AI and CycloneDX ML-BOM.
- Lockfile support set: UNDECIDED.
- Model artifact discovery defaults: UNDECIDED.
- Validation needed before merge: VALIDATION.md.

## Review Blockers

- The change treats generated BOM output as proof of provenance.
- The change adds implicit network access or hosted registry behavior.
- The change reads dataset contents without an explicit privacy and retention decision.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
