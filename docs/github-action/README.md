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
- Pass config, exporter, output path, and warning policy inputs only when the
  caller provides those optional overrides. When `config` is omitted, let the
  CLI discover `aibom.toml` from the model directory.
- Expose BOM path, warning count, and completeness status as outputs.
- Write generated files under explicit paths or under run-unique `RUNNER_TEMP`
  defaults.
- Preserve CLI config precedence for omitted `config`, `format`, and `warnings`
  inputs.
- Prepare Python 3.12 and pinned uv `0.11.28` inside the composite action,
  disable setup-uv's GitHub cache, and keep runtime state under `RUNNER_TEMP`.
- Install only the action's own locked project environment. Do not resolve or
  mutate the caller project's dependencies.
- Preserve read-only default permissions.

## Release Policy

- Artifact upload behavior: UNDECIDED
- First MVP action release: exact `v0.1.0` tag, published before GitHub
  immutable-release enforcement was enabled.
- Exact semver tags are smoke-tested before the mutable `v0` tag moves. Releases
  after `v0.2.0` are also protected by GitHub release immutability.
- Mutable major tag: `v0` tracks the latest compatible 0.x action release after
  external smoke verification.
- Marketplace registration: deferred.
- Compatibility policy: compatible 0.x releases preserve the current
  input/output contract; breaking changes require a new documented release
  decision.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
