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
8. Emit missing-metadata warnings and machine-readable summary output.

Collectors must not know exporter-specific field names. Exporters must not read
the filesystem directly. Reporters must not mutate normalized evidence.

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
- Hash failure: failure.
- Unsupported exporter mapping: failure.
- Partial collector support: warning with unsupported field names.
- Unresolved or unsupported Git metadata: warning without fabricating a commit.

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
