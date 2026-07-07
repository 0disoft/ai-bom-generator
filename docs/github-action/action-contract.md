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
  output format, output path, warning policy, and redaction mode.
- GitHub Action validation evidence: workflow fixtures must cover clean output,
  warning output, and failure output.
- GitHub Action release or rollout policy: UNDECIDED.
- GitHub Action compatibility and migration policy: UNDECIDED

## Permission Policy

Default permissions should be read-only. Artifact upload, release attachment, or PR commenting must be explicit future decisions.
The default action path should not require secrets. Uploading artifacts, writing
comments, attaching releases, or publishing packages must remain opt-in future
contracts with least-privilege review.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
