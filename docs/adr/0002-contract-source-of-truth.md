# Contract Source of Truth

Status: Draft
Owner: UNASSIGNED

## Purpose

This ADR records where AI-BOM Generator contract decisions must live so the CLI,
GitHub Action, data pipeline, and docs do not drift apart.

## Source of Truth

- Product decision: Public behavior must be changed in source-of-truth docs before implementation follows.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Decision

- Product scope and MVP behavior live in docs/product/02-spec.md.
- CLI public behavior lives in docs/cli/command-contract.md.
- GitHub Action public behavior lives in docs/github-action/action-contract.md.
- Data collection, normalization, export, and warning behavior live in docs/data/pipeline-contract.md.
- Runtime flow and boundary language live in docs/architecture/00-system-boundary.md.
- Durable implementation choices live in docs/adr/.
- Validation names and final reporting expectations live in VALIDATION.md.

## Boundary

Examples, README prose, and generated artifacts may explain the current behavior,
but they do not override the source-of-truth documents above.

## Data Ownership

Source-of-truth docs may describe data categories and retention decisions. They
must not embed private dataset contents, credentials, model weights, or real
customer artifacts.

## Failure and Recovery Behavior

When public behavior changes, update the matching source-of-truth doc, fixtures,
and validation plan in the same change. If a runner command is unavailable, the
final report must mark the validation as skipped with a reason.

## Validation Needed Before Merge

VALIDATION.md owns stable validation names. Contract edits should at minimum run
docs/check-equivalent validation when configured, or report those checks as
skipped if this scaffold has no runner.

## Review Blockers

- The change implements or documents public behavior in only one surface.
- The change lets README, examples, generated output, or action metadata drift from source-of-truth docs.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
