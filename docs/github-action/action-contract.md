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

- GitHub Action ownership boundary: invoke the local CLI, expose outputs, and optionally upload artifacts; do not perform registry publication or compliance approval.
- GitHub Action public contract: inputs should cover model directory, config path, output format, output path, and warning policy.
- GitHub Action validation evidence: workflow fixtures must cover clean output, warning output, and failure output.
- GitHub Action release or rollout policy: UNDECIDED.
- GitHub Action compatibility and migration policy: UNDECIDED

## Permission Policy

Default permissions should be read-only. Artifact upload, release attachment, or PR commenting must be explicit future decisions.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
