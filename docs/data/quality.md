# Data Quality

Status: Draft
Owner: UNASSIGNED

## Purpose

Data quality for AI-BOM Generator means deterministic, traceable, standards-valid
output from the same input project.

## Source of Truth

- Product decision: Prefer deterministic output and explicit warnings over broad autodetection.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Quality Gates

- Stable input produces byte-stable or semantically stable output.
- Hashes use a documented algorithm.
- Artifact size and digest are recorded from one stable file snapshot, not from
  separate observations that can race with mutable checkpoints.
- Exported CycloneDX JSON 1.7 BOM passes the vendored official schema.
- Missing metadata appears in the warning report.
- JSON output does not expose full source file contents.
- Warnings are testable by code, not only prose.
- Missing data is represented as machine-readable warnings, not inferred facts.
- Declared values remain distinguishable from observed or derived values.

## Known Quality Risks

- Model project layouts vary widely.
- Lockfile formats differ by ecosystem.
- SPDX and CycloneDX mapping details can drift.
- Large artifact hashing can be expensive.
- Mutable checkpoints can change while being hashed; MVP treats this as a
  collector failure instead of retrying or emitting mixed evidence.
- Warning noise can make important gaps easy to ignore.
- Schema-valid output can still be semantically misleading if declared, observed, derived, and concluded fields are mixed.

## Review Blockers

- The change cannot reproduce output from fixtures.
- The change adds exporter support without schema or fixture evidence.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
