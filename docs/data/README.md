# Data

Status: Draft
Owner: UNASSIGNED

## Purpose

Data in this repository means metadata about AI artifacts, not production user data.
The CLI collects declared project evidence and emits derived BOM output.

## Source of Truth

- Product decision: Keep artifact metadata, provenance references, and warning state explicit.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Decisions

- Boundary: model metadata, checkpoint digests, dependency references, dataset references, prompt references, eval references, and warning summaries.
- Data ownership: input project owns source evidence; AI-BOM Generator owns only generated derived output.
- Failure and recovery behavior: warn on absence, fail on invalid or unreadable required evidence.
- Validation needed before merge: VALIDATION.md

## Review Blockers

- The change reads or stores private dataset contents without an explicit design decision.
- The change reports inferred license, compliance, or safety status as fact.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
