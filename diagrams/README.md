# Diagrams

Status: Draft
Owner: UNASSIGNED

## Purpose

This directory is for diagrams that explain the AI-BOM Generator boundary,
collector pipeline, exporter mapping flow, and CI wrapper behavior.

## Source of Truth

- Product decision: Diagrams should clarify evidence flow without implying audit completeness.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Decisions

- Boundary: Prefer diagrams for local CLI flow, GitHub Action wrapper flow, collector inputs, warning/report outputs, and exporter boundaries.
- Data ownership: Diagrams must show caller-owned input files separately from derived BOM and warning artifacts.
- Failure and recovery behavior: Diagrams should distinguish warnings for missing optional metadata from failures for invalid input, hash errors, and exporter errors.
- Validation needed before merge: VALIDATION.md

## Review Blockers

- The change shows hosted registry, legal approval, vulnerability scanning, or model serving as owned by this repository.
- The change hides missing-metadata warning paths.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
