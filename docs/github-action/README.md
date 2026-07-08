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
- Pass model directory, config, exporter, output path, and warning policy inputs
  only when the caller provides those optional overrides.
- Expose BOM path, warning count, and completeness status as outputs.
- Write generated files under explicit paths or under run-unique `RUNNER_TEMP`
  defaults.
- Preserve CLI config precedence for omitted `format` and `warnings` inputs.
- Require consuming workflows to provide Python 3.12 and `uv` before invoking
  the action until action-managed setup is explicitly approved.
- Preserve read-only default permissions.

## Release Policy

- Artifact upload behavior: UNDECIDED
- First MVP action release: immutable `v0.1.0` tag.
- Current smoke-tested patch tag: immutable `v0.1.1` tag.
- Mutable major tags such as `v0`: deferred.
- Marketplace registration: deferred.
- Compatibility policy: patch tags preserve the current input/output contract;
  breaking changes require a new documented release decision.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
