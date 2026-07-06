# Product Brief

Status: Draft
Owner: UNASSIGNED

## Purpose

AI-BOM Generator helps maintainers describe the ingredients of an AI model
project in a machine-readable bill of materials.

The first product promise is intentionally narrow: scan a single model project
directory, collect explicit model, dataset, dependency, prompt, eval, and
training-code references, compute stable artifact digests, and export a
standards-backed BOM plus a missing-metadata report.

The tool must make absence visible. A sparse project should produce warnings,
not a fake complete provenance story.

## Source of Truth

- Product decision: Build a small AI artifact BOM generator, not a compliance platform.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Decisions

- Boundary: CLI and optional GitHub Action collect local project evidence and emit BOM artifacts.
- Data ownership: Input model project files remain owned by the caller; the tool owns only generated BOM output and warning reports.
- Failure and recovery behavior: Missing optional metadata is a warning; unreadable required input, invalid config, digest mismatch, or unsupported exporter mapping is a failure.
- Validation needed before merge: VALIDATION.md

## Review Blockers

- The change claims compliance, audit completion, or license approval without external review.
- The change silently drops model, dataset, prompt, eval, or digest evidence.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
