# GitHub Action

Status: Draft
Repository Type: github-action

## Purpose

The GitHub Action should make the local CLI usable in CI without adding hosted
state, registry publication, or compliance approval.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Action contract: docs/github-action/action-contract.md
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Action Responsibilities

- Install or invoke the packaged CLI.
- Pass model directory, config, exporter, output path, and warning policy inputs.
- Expose BOM path, warning count, and completeness status as outputs.
- Optionally upload BOM artifacts only when explicitly configured.
- Preserve read-only default permissions.

## Still UNDECIDED

- GitHub Action release or rollout policy: UNDECIDED
- GitHub Action compatibility and migration policy: UNDECIDED

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
