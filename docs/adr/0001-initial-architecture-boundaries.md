# Initial Architecture Boundaries

Status: Draft
Owner: UNASSIGNED

## Purpose

This ADR records the first architecture boundary for AI-BOM Generator.

## Source of Truth

- Product decision: AI-BOM Generator is a local collector and exporter for AI/ML bill-of-materials artifacts.
- Technical owner: UNASSIGNED
- Related ADR: docs/product/02-spec.md

## Decision

AI-BOM Generator owns:

- CLI command contracts for generating an AI-BOM from one target model directory.
- Optional GitHub Action behavior that wraps the CLI in CI.
- Collector contracts for model cards, metadata manifests, model/checkpoint hashes, dependency lockfiles, training-code references, dataset references, prompt references, and eval references.
- Exporter mappings to an existing BOM family once the first exporter is selected.
- Deterministic BOM and missing-metadata warning reports plus machine-readable
  summaries with explicitly run-specific timing.

AI-BOM Generator does not own:

- Model registry behavior.
- Model serving.
- Vulnerability scanning.
- Legal license judgment.
- Training-data audit guarantees.
- Dataset hosting.
- Compliance approval.
- Broad automatic support for every ML framework layout.

## Data Ownership

Input project files are caller-owned. Normalized evidence exists only for the
current invocation unless a future implementation explicitly records cache
behavior. BOM files, warning reports, and JSON summaries are derived artifacts.

## Failure and Recovery Behavior

- Missing optional metadata produces warnings.
- Invalid config, unreadable required files, hashing failures, and invalid exporter output fail the run.
- Stable inputs should produce byte-stable BOM and warning-report outputs.
  Summary timing and manifest generation identity are invocation-specific.
- JSON summaries must report evidence gaps without embedding private source contents.

## Validation Needed Before Merge

VALIDATION.md owns stable validation names. Implementation changes must add
fixtures for complete, sparse, invalid-config, missing-artifact, hash-failure,
and exporter-failure cases as those behaviors become executable.

## Review Blockers

- The change implies BOM output proves full provenance, safety, or compliance.
- The change adds implicit network access, registry publishing, or dataset-content inspection.
- The change changes CLI, action, collector, or exporter contracts without updating source-of-truth docs.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
