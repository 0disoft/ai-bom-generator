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

## Draft Inputs

- `model-directory`: required path to the model project directory.
- `config`: optional config path.
- `format`: selected exporter. The Action wrapper must mirror the CLI's accepted
  values; the current CLI value is `cyclonedx-json-1.7`.
- `output`: output path for generated BOM.
- `warning-report`: output path for warning report.
- `summary`: output path for JSON summary.
- `warnings`: warning policy. The Action wrapper must mirror the CLI's accepted
  values: `allow` and `fail`.
- `upload-artifact`: optional boolean, default false.

Exact GitHub Action input defaults, path conventions, and upload behavior remain
UNDECIDED until the wrapper is implemented. The wrapper must not invent values
that diverge from the CLI contract.

## Draft Outputs

- `bom-path`
- `warning-report-path`
- `summary-path`
- `warning-count`
- `completeness-status`
- `format`

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
