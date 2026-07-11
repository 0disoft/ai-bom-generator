# Privacy and Retention

Status: Draft
Owner: UNASSIGNED

## Purpose

AI-BOM Generator must avoid turning a provenance tool into a private-data leak.
The default collector should record references, paths, hashes, and declared
metadata rather than copying source file contents into telemetry or JSON summaries.

## Source of Truth

- Product decision: Do not inspect private dataset contents in MVP.
- Technical owner: UNASSIGNED
- Related ADR: docs/adr/0001-initial-architecture-boundaries.md

## Privacy Boundary

- Input model project files remain local to the caller.
- Generated BOM output may include paths, hashes, declared names, declared licenses, URLs, and references.
- JSON summary must not include full model card, prompt, eval, or dataset file contents.
- Known secret-shaped values and values attached to sensitive key names should
  be redacted or rejected before they enter generated reports.
- The collector and exporters do not make network requests. GitHub Action
  runtime setup may download only the approved pinned toolchain and the
  action's locked dependencies; it does not upload or resolve caller evidence.
- Prompt contents, private dataset rows, model weights, and full eval output contents are not collected by default.
- BOM output is also a privacy surface and must follow redaction rules, not only the JSON summary.

## Retention Boundary

- The CLI should write only requested output artifacts.
- No background cache, telemetry log, or hidden local database is part of MVP.
  The Action's explicit `RUNNER_TEMP` uv cache is ephemeral runtime state and
  is not persisted through the GitHub Actions cache service.
- GitHub Action artifact upload must be explicit and documented.

## Validation Needed Before Merge

- Redaction fixtures for obvious token, provider-token, URL-like, and
  key-aware secrets.
- Symlink and target-root escape fixtures.
- Negative fixtures proving source file contents are not embedded in JSON summary.

## Review Blockers

- The change stores prompt, eval, dataset, or model-card contents by default.
- The change adds network upload or telemetry without a privacy decision.
- The change weakens validation or skips required evidence.
- The change relies on generated, cache, or build output as source truth.
