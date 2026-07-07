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

- Invoke the packaged CLI from the action checkout with `uv run --project`.
- Pass model directory, config, exporter, output path, and warning policy inputs.
- Expose BOM path, warning count, and completeness status as outputs.
- Write generated files under explicit paths or under `RUNNER_TEMP` defaults.
- Preserve read-only default permissions.

## Still UNDECIDED

- Artifact upload behavior: UNDECIDED
- GitHub Action release or rollout policy: UNDECIDED
- GitHub Action compatibility and migration policy: UNDECIDED

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
