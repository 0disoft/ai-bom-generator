# Performance Budget

Status: Maintained guide

## Contract

Performance budgets must track model-directory scan cost, artifact hashing cost,
memory usage while reading large model files, generated output size, and CI job
runtime.

Artifact collection defaults remain hard ceilings. Config and CLI may lower them
as documented in `docs/cli/artifact-overrides.md`:

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

Artifact discovery is config opt-in and reuses the same budgets. One top-down
tree walk evaluates all fixed default model-artifact patterns, and directories
excluded for every active pattern are pruned before descent. Candidate counts
remain bounded per pattern. A run may enumerate at most 100,000 directory entries
(files and directories, including excluded entries in an opened directory).
Incremental directory enumeration enforces this before materializing an unbounded
flat directory. Excluded subtrees are pruned before descent. If enumeration
exceeds the ceiling, all partial artifact matches are discarded and
`ARTIFACT_TRAVERSAL_LIMIT_EXCEEDED` is emitted. This avoids filesystem-order-based
partial selection. The limit bounds work and allocation, not wall-clock latency.

The synthetic tree regression contains 16 directories and 2,048 nonmatching files.
On the Windows/Python 3.12 local validation run it scanned 2,064 entries in 2.366
seconds with 355,047 traced allocation bytes (allocation tracing enabled).
This is a fixture baseline, not a hosted latency promise or a linear projection.
The 100,000-entry ceiling permits substantially larger caller trees while placing
an explicit finite cap on enumeration and pending-directory storage. Normal,
exact-limit, overflow, and partial-result-discard cases use smaller injected
limits to test the same boundary without creating 100,000 files on every CI run.

Persistent digest reuse is rejected: path, size, inode, and modification time do
not establish identical bytes. Rehashing is required for current evidence; an
external content-addressed immutable store can be used as caller-owned input.

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
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change reads entire large artifacts into memory when streaming would preserve digest behavior.
- A change makes output order or runtime dependent on filesystem enumeration order.
- A change adds broad recursive scanning without include/exclude boundaries.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
