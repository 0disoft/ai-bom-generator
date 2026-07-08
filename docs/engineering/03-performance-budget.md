# Performance Budget

Status: Draft

## Contract

Performance budgets must track model-directory scan cost, artifact hashing cost,
memory usage while reading large model files, generated output size, and CI job
runtime.

The MVP artifact collection budget is fixed rather than configurable:

- 256 candidate paths per include pattern after excludes.
- 16 GiB maximum single artifact size.
- 25 GiB maximum selected artifact bytes per run.

When a budget is hit, the collector emits a machine-readable warning and skips
the over-budget pattern or artifact. It does not fail the whole run unless the
configured warning policy treats warnings as failures.

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
