# Data Integrity

Status: Draft

## Contract

Data integrity covers deterministic collection, stable hashing, source-location
traceability, warning completeness, exporter mapping accuracy, and clear
separation between declared metadata and observed artifacts.

## Required Evidence

- Source of truth: docs/data/quality.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change drops source locations for collected evidence.
- A change treats absent metadata as inferred fact.
- A change changes digest algorithms, output ordering, or exporter fields without migration notes.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
