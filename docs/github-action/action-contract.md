# Action Contract

Status: Draft
Repository Type: github-action

## Repository Type Contract

This repository type owns action inputs, outputs, permissions, token handling, and runner compatibility.

## Source of Truth

- Product decision: GitHub Action wraps the CLI for CI generation and validation of AI-BOM artifacts.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Required Decisions

- GitHub Action ownership boundary: invoke the local CLI through the packaged
  action checkout, expose outputs, and do not perform registry publication or
  compliance approval.
- GitHub Action public contract: inputs cover model directory, config path,
  output format, output paths, generation manifest path, warning policy, and
  redaction mode.
- GitHub Action config precedence: `format` and `warnings` inputs are optional
  overrides. When omitted, the action must not pass the corresponding CLI flag,
  so the CLI uses explicit config values and executable defaults.
- GitHub Action default output paths: when output paths are omitted, the action
  writes BOM, warning report, summary, and generation manifest files under a
  run-unique directory in `RUNNER_TEMP` and exposes those paths as action
  outputs.
- GitHub Action summary output safety: the action must remove stale generated
  output files before invoking the CLI and must publish summary-derived outputs
  only when the generation manifest matches the current BOM, warning-report, and
  summary files by path, size, and SHA-256 digest.
- GitHub Action runtime prerequisites: consuming workflows must provide Python
  3.12 and `uv` before invoking the action until an action-managed setup policy
  is approved.
- GitHub Action validation evidence: workflow fixtures must cover clean output,
  warning output, and failure output.
- GitHub Action release or rollout policy: immutable version tag `v0.1.0` for
  the first public MVP and immutable patch tags such as `v0.1.2`; mutable major
  tags and Marketplace registration are deferred.
- GitHub Action compatibility and migration policy: patch tags may preserve the
  current input/output contract; breaking action contract changes require a new
  documented release decision.

## Permission Policy

Default permissions should be read-only. Artifact upload, release attachment, or PR commenting must be explicit future decisions.
The default action path should not require secrets. Uploading artifacts, writing
comments, attaching releases, or publishing packages must remain opt-in future
contracts with least-privilege review.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
