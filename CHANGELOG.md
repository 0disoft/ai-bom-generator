# Changelog

## v0.5.0

- Adds bounded Poetry 2.x lockfile parsing for exact package versions, markers,
  package source locators or indexes, resolved Git revisions, and per-file
  artifact hashes without dependency resolution, downloads, or local path reads.
- Adds a publication-safe Poetry compatibility corpus for lock versions 2.0 and
  2.1, covering category-era and group-era records, source variants, file hashes,
  and group-marker ambiguity without inferring selected dependency groups.
- Splits requirements, uv, and conda-lock parsing into format-owned modules
  behind the existing dependency-file facade without changing CLI behavior,
  parser budgets, warning semantics, or exported result types.
- Adds a publication-safe compatibility corpus modeled on public conda-lock v1
  fixture shapes, covering legacy field ordering, scalar and environment-variable
  channels, MD5-only and noarch records, multiple target platforms, optional
  categories, and pip wheel or source-distribution entries.
- Requires the compatibility corpus in source distributions so release packaging
  cannot silently drop the evidence used to validate conda-lock support.

## v0.4.0

- Introduces one normalized dependency source boundary for lockfile parsers,
  preserving source locators, package indexes, revisions, and artifact hashes
  without changing explicit config-driven dependency selection.
- Preserves requirements `--hash` and direct-URL fragment hashes plus uv sdist
  and wheel hashes, while malformed evidence fields warn instead of producing
  invented hash claims.
- Bounds artifact hash evidence to 256 distinct records per package.
- Adds bounded, config-explicit conda-lock v1 YAML parsing for Conda and pip
  package entries, preserving declared platforms, matched channels, remote
  locators, and MD5 or SHA-256 artifact hashes without solving environments or
  accessing the network.
- Rejects conda-lock aliases, duplicate mapping keys, excessive nesting,
  oversized files, excessive package arrays, and malformed package evidence
  without fabricating components.

## v0.3.1

- Adds an optional strict-redacted `ai-bom-error-report/v1` hard-failure report
  for CLI and GitHub Action automation without changing existing exit codes or
  successful output manifests.
- Removes stale requested error reports on successful and warning-only runs and
  publishes Action error metadata only after matching the current process exit.
- Adds a low-noise CI regression gate for median runtime and Python allocation
  peaks at 100, 500, and 1,000 explicit components.

## v0.3.0

- Adds an optional producer-owned generation marker protocol that rejects
  active or changed multi-file generations and preserves the previous committed
  output set on failure.
- Exports only the marker's target-root-relative path and SHA-256 digest; the
  opaque producer generation value is never copied into BOM output.

## v0.2.2

- Redacts userinfo credentials from non-HTTP hierarchical URIs, preserves
  declared model release time in SPDX AI preview output, and prevents failed
  Action runs from publishing status fields from an older verified output set.
- Preserves strict-redacted dependency source locators and keeps equal package
  names and versions from distinct uv sources as separate BOM components.
- Preserves previous outputs when generation fails, serializes output-set
  commits with an OS-released lock, restores the previous committed set after
  handled replacement failures, and writes only to validated resolved paths.
- Opens config, dependency, artifact, and Git metadata through a shared
  no-follow descriptor boundary that rejects entry replacement before reads.
- Pins every external GitHub Action to a reviewed commit SHA, aligns CI and
  release jobs on uv 0.11.28, and pins the PEP 517 build backend.
- Bounds package support to Python 3.12-3.14 and validates every supported
  interpreter in the hosted CI matrix.
- Rejects configs over 1 MiB, more than 1,000 declared references, or more than
  256 artifact include/exclude patterns before expensive collection and export.

## v0.2.1

- Separates mutable-channel and exact-release consumer smoke workflows so
  release verification no longer requires temporarily rewriting the `@v0`
  smoke test.
- Enables GitHub immutable releases for future versions and makes release
  verification reject non-immutable post-enforcement tags while retaining an
  explicit legacy exception through `v0.2.0`.
- Restores the canonical Apache License 2.0 text so repository and package
  metadata scanners can identify the declared SPDX license consistently.
- Keeps GitHub Action setup dependencies exactly pinned without duplicating
  their current versions in the verifier, so Dependabot patch updates remain
  independently testable.
- Expands the caller-setup-free GitHub Action smoke to Ubuntu, macOS, and
  Windows hosted runners without fail-fast result suppression.
- Adds a repository security policy backed by GitHub Private Vulnerability
  Reporting, with supported-version and sensitive-reporting guidance.
- Adds weekly and change-triggered Python CodeQL analysis with least-privilege
  result-upload permissions.
- Prevents PyPI project-root `latest` propagation lag from failing exact-version
  release verification while preserving artifact and version checks.
- Adds grouped weekly Dependabot updates for the root uv project and GitHub
  Actions with bounded open pull requests.

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
