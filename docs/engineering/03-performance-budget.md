# Performance Budget

Status: Draft

## Contract

Performance budgets must track model-directory scan cost, artifact hashing cost,
memory usage while reading large model files, generated output size, and CI job
runtime.

The MVP artifact collection budget is fixed rather than configurable:

- 1 MiB maximum config-file read size.
- 1,000 declared references across dependency, dataset, prompt, eval, and
  training sections.
- 256 artifact include patterns and 256 artifact exclude patterns.
- 256 candidate paths per include pattern after excludes.
- 16 GiB maximum single artifact size.
- 25 GiB maximum selected artifact bytes per run.

When a budget is hit, the collector emits a machine-readable warning and skips
the over-budget pattern or artifact. It does not fail the whole run unless the
configured warning policy treats warnings as failures.

Artifact discovery is config opt-in and reuses the same budgets. Discovery must
not add unbounded recursive scans outside the fixed default model artifact
patterns and built-in hidden/cache/build/dependency excludes.

Explicit dependency-file parsing has separate fixed limits:

- 4 MiB maximum dependency-file read size.
- 10,000 logical lines per requirements file.
- 5,000 parsed packages per dependency file.
- 256 distinct artifact hash records per parsed package.
- 128 metadata channels, 64 metadata platforms, and 64 nested YAML levels per
  conda-lock file. YAML aliases and duplicate mapping keys are rejected.
- 128 declared package sources and 64 nested JSON levels per Pipenv lockfile.
  Duplicate JSON keys are rejected.

When a dependency limit is hit, the original file reference remains in the BOM,
no package components are emitted for that file, and the collector emits
`DEPENDENCY_FILE_LIMIT_EXCEEDED`. Artifact hash deduplication occurs before the
per-package limit is checked.

## Required Evidence

The component-generation regression gate exercises 100, 500, and 1,000
explicit dataset components through config validation, collection, CycloneDX
mapping, schema validation, and committed JSON output. Each size uses three
uninstrumented runs for median wall-clock time and one separate traced run for
Python allocation peak, so memory instrumentation does not pollute latency.
The gate uses these intentionally low-noise ceilings:

| Components | Median time | Allocation peak |
| ---: | ---: | ---: |
| 100 | 2 seconds | 16 MiB |
| 500 | 4 seconds | 32 MiB |
| 1,000 | 8 seconds | 64 MiB |

These are regression tripwires, not throughput promises. CI runs the gate once
on Python 3.12; the existing test matrix continues to cover Python 3.13 and
3.14 compatibility. Tightening a ceiling requires repeated hosted evidence.
Optimization or validator caching requires a measured breach or a separately
recorded performance decision.

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
