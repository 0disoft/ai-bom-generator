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
2. Load explicit AI-BOM config when provided.
3. Discover known metadata files without reading arbitrary generated output as truth.
   MVP discovers the in-root `MODEL_CARD.md` path only; it does not copy or
   parse model-card contents.
4. Collect model card paths, training-code references, dependency lockfile references, dataset references, prompt references, eval references, and local Git commit references when in-root Git metadata is available.
5. Hash selected model artifacts and checkpoints.
6. Normalize collected evidence into an internal BOM model.
7. Export to the selected standards-backed BOM format.
8. Stage requested JSON outputs in destination-local temporary files.
9. Build a generation manifest from the staged file bytes, including a
   run-unique generation id plus role, path, size, and SHA-256 digest for every
   final output in the set.
10. Replace final BOM, warning-report, and summary files, then replace the
   manifest last as the commit marker for the output set.
11. Emit missing-metadata warnings and machine-readable summary output.

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
- Unsupported exporter mapping: failure.
- Partial collector support: warning with unsupported field names.
- Unresolved or unsupported Git metadata: warning without fabricating a commit.
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

## Review Blockers

- The change drops source location or warning context.
- The change mutates caller project files.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
