# Changelog

## v0.1.1

Unreleased PyPI packaging preparation.

- Adds package classifiers, keywords, and project URLs for future PyPI publishing.
- Preserves CLI config precedence in the GitHub Action when `format` or `warnings` inputs are omitted.
- Uses run-unique default GitHub Action output directories under `RUNNER_TEMP`.
- Rejects duplicate declared reference identities before exporting duplicate CycloneDX `bom-ref` values.
- Excludes optional prompt, eval, and training references from BOM output when their declared paths are unreadable or unsafe.
- Tightens config schema validation for unknown top-level sections and `warning_policy` keys.
- Keeps PyPI publishing deferred until package-registry policy is approved.

## v0.1.0

First public MVP release.

- Adds the `ai-bom generate` CLI for local AI/ML BOM generation.
- Exports CycloneDX JSON 1.7 and validates generated BOMs against the packaged schema.
- Reads explicit `aibom.toml` config files with config schema v1 validation.
- Collects declared model metadata, in-root `MODEL_CARD.md` paths, selected artifact digests, dependency references, dataset references, prompt references, eval references, training references, and local Git commit evidence.
- Emits machine-readable warning reports and JSON summaries.
- Defaults to strict redaction for generated output and terminal errors.
- Rejects unsafe target-root escapes, symlink escapes, overlapping output paths, directory output paths, and invalid artifact globs.
- Provides a composite GitHub Action wrapper around the CLI.

Deferred:

- PyPI publishing.
- Mutable major action tags such as `v0`.
- GitHub Marketplace registration.
- Automatic config, artifact, and lockfile discovery.
- SPDX AI exporter.
