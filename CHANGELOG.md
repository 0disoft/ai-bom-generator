# Changelog

## Unreleased

- Expands the caller-setup-free GitHub Action smoke to Ubuntu, macOS, and
  Windows hosted runners without fail-fast result suppression.
- Adds a repository security policy backed by GitHub Private Vulnerability
  Reporting, with supported-version and sensitive-reporting guidance.

## v0.2.0

- Adds synthetic Transformers, PyTorch CUDA, ONNX Runtime, and GGUF compatibility
  fixtures that exercise representative dependency syntax across both exporters.
- Makes the composite GitHub Action prepare pinned Python and uv runtimes,
  disables persistent setup caching, and verifies caller-setup-free execution
  in hosted CI.
- Binds post-release verification to the external smoke run's exact workflow
  commit and immutable Action version reference.
- Parses explicitly declared `uv.lock` and requirements files into normalized
  dependency package components without discovery, resolution, or downloads.
- Adds bounded dependency-file reads and machine-readable warnings for
  unsupported formats, malformed files, skipped entries, and safety limits.

## v0.1.4

- Adds the `spdx-ai` exporter as a partial SPDX 3.0.1 AI Profile preview with
  local contract validation and explicit unavailable-field notes.
- Extends deterministic output regression coverage to both CycloneDX and SPDX
  AI export paths, omits unsupported wall-clock creation timestamps from SPDX
  output, and synchronizes the release documentation.

## v0.1.3

- Adds `ai-bom --version` for installed CLI version checks.
- Discovers `<model-directory>/aibom.toml` when `--config` is omitted.
- Improves the README and PyPI landing-page quickstart for first-time users.
- Documents the mutable `v0` GitHub Action tag for compatible patch updates.
- Rejects artifacts that change while hashing so artifact size and digest
  describe the same stable file snapshot.
- Adds fixed artifact match-count and byte budgets with machine-readable
  warnings for skipped over-budget artifact patterns and files.
- Expands strict redaction with Hugging Face and GCP token shapes plus
  key-aware masking for sensitive config and JSON fields.
- Adds config-only opt-in artifact discovery with bounded default model artifact
  patterns and built-in discovery excludes.

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

- GitHub Marketplace registration.
- Artifact and lockfile discovery.
- SPDX AI exporter.
