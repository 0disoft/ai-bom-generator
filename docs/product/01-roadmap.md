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
- Parse discovered or explicit config and model metadata.
- Compute SHA-256 digests for configured model artifacts.
- Collect dependency, dataset, prompt, eval, and training-code references.
- Emit BOM output and missing-metadata warnings.
- Reject target-root escapes and symlink escapes by default.
- Prove secret-shaped values do not leak into summaries or warning reports.

## Phase 2: CI Integration

- Add GitHub Action wrapper around the CLI.
- Validate clean, warning-only, and fail-on-missing action modes.
- Defer artifact upload examples until upload behavior is explicitly designed.

## Phase 3: Exporter Expansion

- The second standards-backed exporter is implemented as the partial
  `spdx-ai` preview after CycloneDX fixtures stabilized.
- Deterministic output compatibility tests cover both exporter paths.
- Consider bridges to registry, release, or provenance tooling only after local generation is solid.

## v0.3.0 Hardening

- Define a producer-owned generation marker contract for multi-file model
  snapshots. Do not claim cross-file generation consistency until collection
  verifies the approved protocol before and after all selected reads. The
  proposed contract is recorded in `docs/adr/0004-producer-generation-marker.md`.
- Add bounded performance regression evidence for 100, 500, and 1,000 declared
  components. Record time and memory budgets before optimizing schema validation.
- Add an optional machine-readable hard-failure report without changing the
  existing exit-code contract or default terminal behavior.

## v0.4.0 Dependency Expansion

- Introduce a parser boundary that preserves package source, channel, platform,
  revision, and artifact hash evidence across lockfile formats.
- Add bounded `conda-lock` support first, then evaluate Poetry and Pipenv from
  real fixtures instead of filename-only detection.
- Keep dependency discovery explicit and config-driven. Unsupported or malformed
  files must continue to warn without fabricating package components.

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
