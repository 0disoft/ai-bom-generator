# Data Integrity

Status: Draft

## Contract

Data integrity covers deterministic collection, stable hashing, source-location
traceability, warning completeness, exporter mapping accuracy, and clear
separation between declared metadata and observed artifacts.

Artifact size and digest fields must describe the same stable file snapshot.
The collector hashes selected artifacts through a single open file descriptor,
compares file metadata before and after hashing, and fails conservatively when
the artifact changes during collection. Mutable training checkpoints should be
collected only after writes finish or after being copied to an immutable staging
path.

## Required Evidence

- Source of truth: docs/data/quality.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change drops source locations for collected evidence.
- A change treats absent metadata as inferred fact.
- A change changes digest algorithms, output ordering, or exporter fields without migration notes.
- A change records artifact size and digest from different file observations.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
