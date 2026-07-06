# Roadmap

Status: Draft
Owner: UNASSIGNED

## Purpose

This roadmap keeps AI-BOM Generator small enough to ship while leaving room for
later exporter and CI integrations.

## Source of Truth

- Product decision: Build collector and exporter confidence before adding broad framework support.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Phase 0: Contract Baseline

- Lock the source-of-truth docs.
- Choose runtime, packaging, config filename, and first exporter.
- Keep CycloneDX JSON 1.7 schema validation passing for the implemented first exporter.
- Decide license, visibility, redaction default, no-network posture, and cache policy.
- Create fixtures for one complete and one sparse model directory.
- Define JSON summary, warning report, warning taxonomy, and exit-code taxonomy.

## Phase 1: Local CLI MVP

- Read one model directory.
- Parse explicit config and model metadata.
- Compute SHA-256 digests for configured model artifacts.
- Collect dependency, dataset, prompt, eval, and training-code references.
- Emit BOM output and missing-metadata warnings.
- Reject target-root escapes and symlink escapes by default.
- Prove secret-shaped values do not leak into summaries or warning reports.

## Phase 2: CI Integration

- Add GitHub Action wrapper around the CLI.
- Support artifact upload examples without requiring repository secrets.
- Add workflow examples for warning-only and fail-on-missing modes.

## Phase 3: Exporter Expansion

- Add the second standards-backed exporter after the first exporter has stable fixtures.
- Add compatibility tests for deterministic output.
- Consider bridges to registry, release, or provenance tooling only after local generation is solid.

## Deferred

- Hosted registry.
- Vulnerability scanning.
- Dataset auditing.
- Legal compliance scoring.
- Automatic support for every ML framework.

## Review Blockers

- A roadmap item expands into a platform before the local CLI is proven.
- A phase depends on private services, credentials, or hosted accounts.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
