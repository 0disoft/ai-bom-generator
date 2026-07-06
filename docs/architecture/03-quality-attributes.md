# Quality Attributes

Status: Draft

## Boundary

Quality attributes apply to the CLI, GitHub Action wrapper, collector pipeline,
exporter mappings, warning report, JSON summary, and validation fixtures.

## Required Attributes

- Deterministic output for stable input.
- Honest warning behavior for missing or unsupported metadata.
- Source traceability from BOM fields back to collected evidence where possible.
- No mutation of caller-owned project files in MVP.
- No private dataset contents, credentials, or model weights embedded in summaries or logs.
- Clear separation between collected evidence and legal, security, or compliance conclusions.
- Fixture-backed exporter mappings before standards compatibility is claimed.

## Review Blockers

- A change makes output nondeterministic without a documented reason.
- A change hides warnings or treats missing metadata as collected evidence.
- A change claims audit completeness, safety, compliance, or license correctness.
- A change adds network access, caching, or dataset-content inspection without an ADR.
