# Development

Status: Draft
Owner: UNASSIGNED

## Purpose

This document defines development expectations for the AI-BOM Generator CLI,
collector pipeline, exporter mappings, and GitHub Action wrapper.

## Source of Truth

- Product decision: Development work should keep the tool deterministic, local-first, and honest about missing evidence.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Approved Development Baseline

- Boundary: Python 3.12 through 3.14, uv for the project lock and validation
  environment, the `ai-bom` binary, CycloneDX JSON 1.7, and the partial
  `spdx-ai` preview are recorded in the product spec and ADR 0003.
- Data ownership: Development fixtures may use synthetic model projects only; do not commit private datasets, real credentials, or unreleased model artifacts.
- Failure and recovery behavior: Tests should cover complete, sparse, invalid-config, missing-artifact, hash-failure, and exporter-failure cases before release.
- Validation needed before merge: VALIDATION.md

## Review Blockers

- The change adds a framework, runtime, package manager, dependency format, or
  exporter outside the approved source-of-truth baseline.
- The change makes output nondeterministic for stable input.
- The change stores private input contents in JSON summaries, logs, caches, or fixtures.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
