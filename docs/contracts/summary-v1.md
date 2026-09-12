# JSON Summary Contract v1

Status: Accepted contract

## Purpose

The JSON summary is the automation surface for local CLI and GitHub Action runs.
It should let CI decide whether a run generated an artifact, produced warnings,
or failed without scraping terminal prose.

The executable schema lives at `schemas/aibom-summary-v1.schema.json`.

## Fields

- `schema_version`
- `tool.name`
- `tool.version`
- `status`
- `format`
- `bom_path`
- `warning_report_path`
- `hash_algorithm`
- `artifact_count`
- `warning_count`
- `completeness_status`
- `warnings`
- `elapsed_ms`
- `exit_code`

## Privacy Rules

- Do not embed full model-card, prompt, eval, dataset, dependency, or model file contents.
- In strict mode, do not emit unredacted token-bearing URLs, private key blocks, credentialed
  Git remotes, provider token shapes, or values attached to sensitive key names.
- Explicit `--redaction off` permits unredacted generated summaries; terminal
  diagnostics and hard-failure reports remain strictly redacted.
- Prefer relative paths when they preserve enough source context.

## Status Values

- `success`
- `success-with-warnings`
- `failed`

## Review Blockers

- A summary field changes without updating CLI, Action, and fixture contracts.
- The summary becomes the only place where warnings are emitted.
- The summary treats missing evidence as collected evidence.
