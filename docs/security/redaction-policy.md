# Redaction Policy

Status: Draft
Owner: UNASSIGNED

## Purpose

The tool writes BOMs, warning reports, and JSON summaries. Anything copied from a
caller project can become a disclosure, so redaction is part of the product
contract, not just terminal polish.

## Default Candidate

Strict redaction is the leading default candidate. Redaction off may be useful
for debugging, but it should require explicit user choice and a machine-readable
`REDACTION_DISABLED` warning.

## Secret-Shaped Values

The redaction layer should detect obvious credential forms before output:

- Token-bearing URLs.
- Basic-auth URLs.
- Private key blocks.
- Credentialed Git remotes.
- Common API-token-shaped strings.
- Disabled redaction must be reported as a warning instead of silently producing
  unredacted output.

## Output Surfaces

- BOM file.
- Warning report.
- JSON summary.
- Terminal output. Error messages are safety-redacted even when generated
  artifacts are requested with `--redaction off`, because failures may occur
  before a warning report can be written.
- GitHub Action logs and outputs.

## Review Blockers

- A new output surface bypasses redaction.
- Redaction only covers JSON summary but not BOM output.
- A fixture includes real credentials, real private prompts, real private datasets, or real model weights.
