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
4. Collect model card fields, training-code references, dependency lockfile references, dataset references, prompt references, and eval references.
5. Hash selected model artifacts and checkpoints.
6. Normalize collected evidence into an internal BOM model.
7. Export to the selected standards-backed BOM format.
8. Emit missing-metadata warnings and machine-readable summary output.

## Ownership Boundary

- Input files belong to the caller.
- Normalized evidence belongs to the current CLI invocation.
- Generated BOM and warning report are derived artifacts.
- The tool must not mutate the target model directory in MVP.

## Failure and Recovery

- Missing optional metadata: warning.
- Invalid config: failure with actionable location.
- Unreadable required input: failure.
- Hash failure: failure.
- Unsupported exporter mapping: failure.
- Partial collector support: warning with unsupported field names.

## Validation Needed Before Merge

- Fixture coverage for complete, sparse, invalid-config, and missing-artifact projects.
- Deterministic output check for stable input.
- Exporter schema or conformance check once the first exporter is selected.

## Review Blockers

- The change drops source location or warning context.
- The change mutates caller project files.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
