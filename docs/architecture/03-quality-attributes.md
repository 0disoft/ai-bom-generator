# Quality Attributes

Status: Draft

## Boundary

Quality attributes apply to the CLI, GitHub Action wrapper, collector pipeline,
exporter mappings, warning report, JSON summary, and validation fixtures.

## Required Attributes

- Byte-stable BOM and warning-report output for stable input. Summary timing and
  manifest generation identity are explicitly run-specific.
- Honest warning behavior for missing or unsupported metadata.
- Source traceability from BOM fields back to collected evidence where possible.
- No mutation of caller-owned project files in MVP.
- No private dataset contents, credentials, or model weights embedded in summaries or logs.
- Clear separation between collected evidence and legal, security, or compliance conclusions.
- Fixture-backed exporter mappings before standards compatibility is claimed.
- Bounded config validation and export cost at the supported 1,000-reference
  limit, backed by low-noise runtime and allocation regression evidence.

## Review Blockers

- A change makes BOM or warning-report output nondeterministic without a
  documented reason, or adds another run-specific field without documenting it.
- A change hides warnings or treats missing metadata as collected evidence.
- A change claims audit completeness, safety, compliance, or license correctness.
- A change adds network access, caching, or dataset-content inspection without an ADR.
- A change raises component performance ceilings or adds validator caching
  without measured evidence.
