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
- `format`: selected exporter. `cyclonedx-json-1.7` is the leading first value candidate; exact accepted values remain UNDECIDED.
- `output`: output path for generated BOM.
- `warning-report`: output path for warning report.
- `summary`: output path for JSON summary.
- `warnings`: warning policy, with `allow` and `fail` as leading value candidates; exact values remain UNDECIDED.
- `upload-artifact`: optional boolean, default false.

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
