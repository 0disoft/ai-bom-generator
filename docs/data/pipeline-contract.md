# Pipeline Contract

Status: Draft
Owner: UNASSIGNED

## Purpose

The AI-BOM pipeline turns local project evidence into a deterministic BOM artifact
and a warning report.

## Source of Truth

- Product decision: Collector pipeline must preserve provenance and absence information.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Pipeline Stages

1. Resolve the target model directory.
2. Load explicit AI-BOM config when provided, otherwise discover
   `<model-directory>/aibom.toml` when present.
3. When `[generation].marker` is configured, read and validate one complete
   producer generation before any governed evidence collection.
4. Discover known metadata files without reading arbitrary generated output as truth.
   MVP discovers the in-root `MODEL_CARD.md` path only; it does not copy or
   parse model-card contents.
5. Collect model card paths, training-code references, dependency-file
   references, dataset references, prompt references, eval references, and
   local Git commit references when in-root Git metadata is available. Parse
   explicitly declared `uv.lock`, Poetry 2.x `poetry.lock`, Pipenv
   `Pipfile.lock` specification 6, requirements files, and unified conda-lock v1
   YAML through one bounded parser boundary into
   normalized package and
   package-source evidence unless parsing is disabled for that reference. The
   boundary preserves source
   locator, channel, index, platform, revision, and artifact hash fields when a
   supported parser has direct evidence for them.
6. Select artifacts in one deterministic top-down tree walk from explicit
   include patterns and, only when
   `[artifacts].discovery = true`, bounded default model artifact patterns for
   `.safetensors`, `.gguf`, `.bin`, `.pt`, `.pth`, `.ckpt`, and `.onnx` files.
   Prune a directory before descent when every still-active pattern excludes its
   subtree. Explicit patterns retain their own exclude semantics.
7. Apply fixed MVP artifact budgets before hashing: at most 256 candidate paths
   per include pattern after excludes, at most 16 GiB for one artifact, and at
   most 25 GiB of selected artifacts per run. Budget hits are machine-readable
   warnings and the over-budget pattern or artifact is skipped.
8. Hash selected model artifacts and checkpoints through one open file
   descriptor. The recorded size and SHA-256 digest must come from the same
   stable file snapshot, verified by comparing file metadata before and after
   hashing.
9. Reopen the configured generation marker after all governed reads and require
   byte-equivalence with the initial complete marker.
10. Normalize collected evidence into an internal BOM model.
11. Export to the selected standards-backed BOM format.
12. Stage requested JSON outputs in destination-local temporary files.
13. Build a generation manifest from the staged file bytes, including a
   run-unique generation id plus role, path, size, and SHA-256 digest for every
   final output in the set.
14. Acquire stable destination-adjacent locks for every generated output path,
    including the manifest, in canonical path order; preserve any previous
    committed files as destination-local rollback copies, replace final BOM,
   warning-report, and summary files, then replace the manifest last as the
   commit marker. Restore the previous set on a handled replacement failure.
15. Emit missing-metadata warnings and machine-readable summary output.

Collectors must not know exporter-specific field names. Exporters must not read
the filesystem directly. Reporters must not mutate normalized evidence.
Dependency parsers must return the shared package-source evidence contract and
must leave unavailable provenance fields absent. A malformed nested provenance
field may be skipped with `DEPENDENCY_PARSE_PARTIAL`; it must not be replaced by
an inferred value.
Overlapping artifact include patterns must normalize to one artifact evidence
record per resolved target-root-relative file path.
Declared dependency, dataset, prompt, eval, and training references must have a
unique `kind` plus `object_id` identity before export, because CycloneDX
component `bom-ref` values are derived from that identity.

## Ownership Boundary

- Input files belong to the caller.
- Normalized evidence belongs to the current CLI invocation.
- Generated BOM and warning report are derived artifacts.
- The tool must not mutate the target model directory in MVP.

## Failure and Recovery

- Missing optional metadata: warning.
- Invalid config: failure with actionable location.
- Unreadable required input: failure.
- Unreadable or unsafe optional reference path: warning without adding the
  rejected path to normalized BOM evidence.
- Duplicate declared reference identity: invalid-config failure before writing
  generated output.
- Hash failure: failure.
- Artifact changed while hashing: collector failure before writing generated
  output. The caller must retry after checkpoint writes finish or point the
  config at an immutable or staged artifact copy.
- Initial generation marker missing, unsafe, oversized, malformed, duplicated,
  or not complete: invalid-input failure before governed collection.
- Final generation marker missing, unsafe, malformed, not complete, or changed:
  collector failure while preserving the previous committed output set.
- Artifact include pattern exceeds the match-count budget: warning, skip that
  pattern, and continue with other patterns.
- Artifact exceeds the single-file byte budget: warning, skip that artifact, and
  continue with other artifacts.
- Artifact would exceed the total selected byte budget: warning, skip that
  artifact, and continue with other artifacts.
- Unsupported exporter mapping: failure.
- Partial collector support: warning with unsupported field names.
- Unresolved or unsupported Git metadata: warning without fabricating a commit.
- Oversized Git metadata files: warning without fabricating a commit.
- Missing dataset license declarations include absent or blank
  `license_declared` values.
- Artifact discovery disabled or no include patterns declared: warning without
  fabricating artifact evidence.
- Artifact discovery enabled but no default patterns match: warning without
  fabricating artifact evidence.
- Collection or export failure: preserve the previous committed BOM,
  warning-report, summary, and manifest set. A failed run must not rewrite old
  outputs as if they came from the failed attempt.
- Output write failure: remove the current temporary files and restore the
  previous committed output set after handled replacement failures.
- Concurrent writers: serialize the final replacement phase through persistent,
  destination-adjacent OS-released lock files acquired in canonical path order.
  Writers that share any generated destination therefore contend even when
  their manifest paths differ. Staging may occur concurrently, but final files
  and the manifest must come from one lock owner.
- Interrupted output replacement: if the process stops after one final output is
  replaced but before the manifest is replaced, consumers can reject the output
  set because the current run has no committed manifest with matching digests.

## Validation Needed Before Merge

- Fixture coverage for complete, sparse, invalid-config, and missing-artifact projects.
- Security fixture coverage for secret-redaction and symlink-escape projects.
- Deterministic output check for stable input.
- Exporter schema or conformance check for every implemented exporter.
  `spdx-ai` uses local preview-contract validation until full upstream SPDX
  conformance validation is adopted.

## Review Blockers

- The change drops source location or warning context.
- The change mutates caller project files.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
