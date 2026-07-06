# Design Review Questions

Status: Draft

## Contract

Design review questions must cover problem boundary, ownership, data/state, failure and recovery, future cost, and source-of-truth drift.

## Required Evidence

- Source of truth: docs/product/02-spec.md
- Owner: UNASSIGNED
- Merge-blocking validation: VALIDATION.md
- Related checklist: CHECKLIST.md

## Review Blockers

- A change expands the product boundary without updating the spec or an ADR.
- A change omits how missing metadata is surfaced.
- A change omits privacy impact for input files, logs, summaries, or artifacts.
- A change weakens validation or hides skipped checks.
- A change lacks failure, recovery, security, performance, or test evidence where relevant.
