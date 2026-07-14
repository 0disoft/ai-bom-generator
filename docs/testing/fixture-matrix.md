# Fixture Matrix

Status: Draft
Owner: UNASSIGNED

## Purpose

Fixtures prove that AI-BOM Generator reports real evidence and missing evidence
honestly. They should be synthetic and safe to publish.

## Required Fixture Candidates

| Fixture | Purpose |
| --- | --- |
| `complete-project` | Full metadata, artifact digest, dependencies, dataset, prompt, eval, and training references. Covered by CLI smoke, schema, and deterministic-output tests. |
| `dependency-lockfiles` | Explicit requirements and `uv.lock` files map to CycloneDX library and SPDX software package elements without resolution or downloads, while requirements hash options remain package-source evidence. Covered by parser and CLI integration tests. |
| `conda-lock-corpus` | Publication-safe values arranged in field orders and combinations observed in public conda-lock v1 fixtures cover version-at-end files, scalar and environment-variable channels, MD5-only packages, noarch URLs repeated across target platforms, optional categories, and pip wheel/sdist entries with `source: null`. Covered by focused parser tests and required in the source distribution. |
| `poetry-lock` | Publication-safe Poetry 2.1 TOML covers registry, Git, legacy index, local directory, and direct URL package sources plus groups, shared and differing group markers, resolved revisions, and per-file hashes. Groups remain non-exported selection metadata, and differing group markers warn instead of being flattened. Covered by parser, CycloneDX/SPDX integration, budget, and source-distribution tests. |
| `ml-ecosystem-dependencies` | Synthetic Transformers, PyTorch CUDA, ONNX Runtime, GGUF, and unified conda-lock v1 shapes preserve source types, indexes or channels, platforms, revisions, artifact hashes, local versions, markers, ranges, extras, and remote direct references. The conda-lock fixture covers Conda and pip managers plus duplicate name/version identities across platforms. Covered by parser-profile and combined CycloneDX/SPDX integration tests. |
| `sparse-project` | Missing optional metadata appears as warnings, not inferred facts. Covered by CLI warning tests. |
| `invalid-config` | Invalid config fails with actionable location. Covered by CLI invalid-input tests. |
| `missing-artifact` | Unmatched artifact include patterns warn without fabricating artifact evidence. Covered by CLI warning tests. |
| `hash-failure` | Digest collection failure produces collector failure. Covered by hashing failure and CLI collector-failure tests. |
| `exporter-failure` | Invalid exporter mapping fails validation. Covered by CLI exporter-failure tests. |
| `secret-redaction` | Secret-shaped, provider-token-shaped, and key-aware secret values are redacted or rejected across outputs. Covered by CLI redaction tests. |
| `symlink-escape` | Symlink and target-root escape attempts are blocked. Covered by CLI path-policy, output-path symlink, and model-card symlink tests. |
| `nondeterministic-ordering-guard` | Stable input produces stable BOM and warning-report ordering. Covered by deterministic-output tests. |
| `large-artifact-simulated` | Streaming hash behavior is tested without committing large binaries. Covered by chunked hashing tests. |

## Fixture Rules

- Use synthetic data only.
- Ecosystem compatibility fixtures may use public package names and representative
  syntax, but their versions and URLs are immutable test data rather than claims
  about current upstream releases.
- Do not commit real model weights, real private prompts, real customer data, or real private dataset URLs.
- Dummy model files may use small binary files with model-like names.
- Golden outputs must be stable and reviewed when schema or warning taxonomy changes.
- Contract tests must validate generated summary, warning report, and requested
  hard-failure report JSON against `schemas/`.
- Exporter tests must validate generated CycloneDX JSON against the vendored official schema.

## Review Blockers

- A collector, exporter, warning, or redaction behavior is added without a matching fixture.
- A fixture contains real secrets or private artifacts.
- Golden output makes compliance, safety, or license conclusions that the tool did not prove.
