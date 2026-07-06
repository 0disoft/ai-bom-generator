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
- `format`: selected exporter, exact accepted values UNDECIDED.
- `output`: output path for generated BOM.
- `warnings`: warning policy, such as allow or fail, exact values UNDECIDED.
- `upload-artifact`: optional boolean, default false.

## Draft Outputs

- `bom-path`
- `warning-count`
- `completeness-status`
- `format`

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
