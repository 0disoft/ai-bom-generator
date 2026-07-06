# Performance Budget

Status: Draft

## Contract

Performance budgets must track model-directory scan cost, artifact hashing cost,
memory usage while reading large model files, generated output size, and CI job
runtime. Exact numeric thresholds remain UNDECIDED until executable fixtures
exist.

## Required Evidence

- Source of truth: docs/architecture/03-quality-attributes.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change reads entire large artifacts into memory when streaming would preserve digest behavior.
- A change makes output order or runtime dependent on filesystem enumeration order.
- A change adds broad recursive scanning without include/exclude boundaries.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
