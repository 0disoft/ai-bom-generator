# Inputs and Outputs

Status: Draft
Repository Type: github-action

## Purpose

Inputs and outputs must mirror the CLI contract closely enough that local and CI
behavior stay comparable.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Action contract: docs/github-action/action-contract.md
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Inputs

- `model-directory`: required path to the model project directory.
- `config`: optional config path. Empty means the CLI runs without an explicit
  config file.
- `format`: selected exporter. The Action wrapper must mirror the CLI's accepted
  values; the current CLI value is `cyclonedx-json-1.7`.
- `output`: output path for generated BOM. Empty defaults under `RUNNER_TEMP`.
- `warning-report`: output path for warning report. Empty defaults under
  `RUNNER_TEMP`.
- `summary`: output path for JSON summary. Empty defaults under `RUNNER_TEMP`.
- `warnings`: warning policy. The Action wrapper must mirror the CLI's accepted
  values: `allow` and `fail`.
- `redaction`: redaction mode. The Action wrapper must mirror the CLI's accepted
  values: `strict` and `off`.

Artifact upload behavior remains UNDECIDED. The wrapper must not invent values
that diverge from the CLI contract.

## Outputs

- `bom-path`
- `warning-report-path`
- `summary-path`
- `warning-count`
- `completeness-status`
- `format`
- `exit-code`

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
