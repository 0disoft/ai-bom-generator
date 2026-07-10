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
3. Discover known metadata files without reading arbitrary generated output as truth.
   MVP discovers the in-root `MODEL_CARD.md` path only; it does not copy or
   parse model-card contents.
4. Collect model card paths, training-code references, dependency-file
   references, dataset references, prompt references, eval references, and
   local Git commit references when in-root Git metadata is available. Parse
   explicitly declared `uv.lock` and requirements files into bounded normalized
   Python package evidence unless parsing is disabled for that reference.
5. Select artifacts from explicit include patterns and, only when
   `[artifacts].discovery = true`, bounded default model artifact patterns for
   `.safetensors`, `.gguf`, `.bin`, `.pt`, `.pth`, `.ckpt`, and `.onnx` files.
6. Apply fixed MVP artifact budgets before hashing: at most 256 candidate paths
   per include pattern after excludes, at most 16 GiB for one artifact, and at
   most 25 GiB of selected artifacts per run. Budget hits are machine-readable
   warnings and the over-budget pattern or artifact is skipped.
7. Hash selected model artifacts and checkpoints through one open file
   descriptor. The recorded size and SHA-256 digest must come from the same
   stable file snapshot, verified by comparing file metadata before and after
   hashing.
8. Normalize collected evidence into an internal BOM model.
9. Export to the selected standards-backed BOM format.
10. Stage requested JSON outputs in destination-local temporary files.
11. Build a generation manifest from the staged file bytes, including a
   run-unique generation id plus role, path, size, and SHA-256 digest for every
   final output in the set.
12. Replace final BOM, warning-report, and summary files, then replace the
   manifest last as the commit marker for the output set.
13. Emit missing-metadata warnings and machine-readable summary output.

Collectors must not know exporter-specific field names. Exporters must not read
the filesystem directly. Reporters must not mutate normalized evidence.
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
- Stale generated output from a previous run: removed after output-path
  validation and before collection or export starts, so a failed run does not
  leave old BOM, warning-report, summary, or manifest files at the requested
  destinations.
- Output write failure: temporary files are removed, and any final files already
  replaced by the current output staging attempt are removed before the failure
  is surfaced.
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
