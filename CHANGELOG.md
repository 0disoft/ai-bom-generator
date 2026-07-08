# Changelog

## v0.1.2

- Adds the first PyPI Trusted Publishing release path for package releases.
- Adds a post-release verification script for PyPI, GitHub Release, and external smoke evidence.
- Updates GitHub Actions `uv` setup pins to `astral-sh/setup-uv@v8.3.1`.

## v0.1.1

GitHub Release patch with PyPI publishing still deferred.

- Adds package classifiers, keywords, and project URLs for future PyPI publishing.
- Adds Ruff as the configured lint runner for local and CI validation.
- Preserves CLI config precedence in the GitHub Action when `format` or `warnings` inputs are omitted.
- Uses run-unique default GitHub Action output directories under `RUNNER_TEMP`.
- Rejects duplicate declared reference identities before exporting duplicate CycloneDX `bom-ref` values.
- Excludes optional prompt, eval, and training references from BOM output when their declared paths are unreadable or unsafe.
- Applies recursive artifact exclude globs before hashing, including `.git` and `__pycache__` subtrees selected by broad include patterns.
- Expands strict redaction coverage for common AWS, Slack, GitLab, Google API key, Bearer, and JWT-shaped values.
- Reports blank dataset `license_declared` values as missing license warnings.
- Caps Git metadata reads so oversized packed refs resolve as warnings instead of unbounded reads.
- Stages generated JSON files through destination-local temporary files, writes a generation manifest as the commit marker, and removes stale or partial outputs on generation/write failures.
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
