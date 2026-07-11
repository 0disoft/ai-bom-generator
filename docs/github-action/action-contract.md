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
  so the CLI uses discovered or explicit config values and executable defaults.
  When `config` is omitted, the action must not pass `--config`, so CLI
  target-root config discovery remains in one place.
- GitHub Action default output paths: when output paths are omitted, the action
  writes BOM, warning report, summary, and generation manifest files under a
  run-unique directory in `RUNNER_TEMP` and exposes those paths as action
  outputs.
- GitHub Action summary output safety: the action must remove stale generated
  output files before invoking the CLI and must publish summary-derived outputs
  only when the generation manifest matches the current BOM, warning-report, and
  summary files by path, size, and SHA-256 digest.
- GitHub Action runtime setup: the composite action prepares Python 3.12 and
  pinned uv `0.11.28`, with setup-uv's GitHub cache disabled. It runs the
  action checkout through `uv run --project --locked` and forces both the
  action environment and uv download cache under `RUNNER_TEMP`.
- GitHub Action network boundary: managed setup may download the pinned Python
  and uv toolchains plus dependencies from the action's own lockfile. The
  collector and exporters do not perform network requests, resolve the caller
  project's dependencies, or upload generated evidence.
- GitHub Action validation evidence: workflow fixtures must cover clean output,
  warning output, failure output, and a clean hosted runner with no caller-side
  Python or uv setup step.
- GitHub Action release or rollout policy: exact semver tags for public
  releases, GitHub-enforced immutable releases after `v0.2.0`, and mutable `v0`
  for the latest compatible 0.x action release after external smoke
  verification; Marketplace registration is deferred.
- GitHub Action compatibility and migration policy: compatible 0.x releases
  preserve the input/output contract; breaking action contract changes require
  a new documented release decision.

## Permission Policy

Default permissions should be read-only. Artifact upload, release attachment, or PR commenting must be explicit future decisions.
The default action path should not require secrets. Uploading artifacts, writing
comments, attaching releases, or publishing packages must remain opt-in future
contracts with least-privilege review.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
