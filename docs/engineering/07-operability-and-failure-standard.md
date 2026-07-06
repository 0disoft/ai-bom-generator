# Operability and Failure Standard

Status: Draft

## Contract

Operability standard connects CLI/action behavior to actionable errors,
machine-readable summaries, warning policy, deterministic artifacts, rollback
expectations, and CI failure evidence.

## Required Evidence

- Source of truth: docs/cli/output-and-exit-codes.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A failure path does not name the failing input, collector, exporter, or validation stage.
- A warning cannot be surfaced in JSON output or CI logs.
- A rollback cannot restore the previous CLI/action public contract.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
