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
- `config`: optional config path. Empty means the action omits `--config`, so
  the CLI may discover `<model-directory>/aibom.toml`.
- `format`: selected exporter. The Action wrapper must mirror the CLI's accepted
  values; the current CLI value is `cyclonedx-json-1.7`.
- `output`: output path for generated BOM. Empty defaults under `RUNNER_TEMP`.
- `warning-report`: output path for warning report. Empty defaults under
  `RUNNER_TEMP`.
- `summary`: output path for JSON summary. Empty defaults under `RUNNER_TEMP`.
- `manifest`: output path for the generation manifest. Empty defaults under
  `RUNNER_TEMP`.
- `error-report`: output path for the optional hard-failure report. Empty
  defaults under the same run-unique `RUNNER_TEMP` directory.
  Explicit relative output and report paths resolve from `GITHUB_WORKSPACE`.
- `warnings`: warning policy. The Action wrapper must mirror the CLI's accepted
  values: `allow` and `fail`.
- `redaction`: redaction mode. The Action wrapper must mirror the CLI's accepted
  values: `strict` and `off`. The explicit `off` value permits unredacted
  generated artifacts and is intended only for controlled local debugging.

Artifact upload behavior remains UNDECIDED. The wrapper must not invent values
that diverge from the CLI contract.

## Outputs

- `bom-path`
- `warning-report-path`
- `summary-path`
- `manifest-path`
- `error-report-path`
- `error-code`: stable code from a schema-checked current-run failure report.
- `error-stage`: stage from a schema-checked current-run failure report.
- `warning-count`
- `status`: JSON summary run status, such as `success`, `success-with-warnings`,
  or `failed`.
- `completeness-status`: JSON summary evidence completeness status, such as
  `complete`, `partial`, or `empty`.
- `format`
- `exit-code`

The wrapper writes GitHub outputs with the multiline `GITHUB_OUTPUT` form so
path-like values remain output data even when they contain line breaks.
The wrapper publishes summary-derived outputs only after the generation manifest
exists and its path, size, and SHA-256 entries match the BOM, warning-report,
and summary files from the same run.
Failure-derived outputs are published only when the error report has
`schema_version` `ai-bom-error-report/v1`, status `failed`, and an `exit_code`
matching the CLI process status.
If any requested stale output cannot be removed before invocation, the wrapper
returns exit code 70 without invoking the CLI or accepting that stale file as
current-run evidence.

## Review Blockers

- Action permission changes lack least-privilege review.
- Outputs or exit behavior changes without workflow examples.
