# Permissions

Status: Draft
Repository Type: github-action

## Purpose

The default action posture is read-only. The action should generate evidence from
the checked-out repository, not mutate repository state or publish artifacts by
default.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Action contract: docs/github-action/action-contract.md
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Default Permission Boundary

- `contents: read` should be sufficient for normal generation.
- No write permissions by default.
- No package, release, issue, pull request, or security-event writes unless a future feature explicitly owns them.
- No secrets required for MVP generation.

## Review Requirements

Any permission expansion must name the user-facing capability, the smallest
GitHub permission required, and the failure mode when that permission is absent.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
