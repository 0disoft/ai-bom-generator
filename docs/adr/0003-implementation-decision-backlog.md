# Implementation Decision Backlog

Status: Draft
Owner: UNASSIGNED

## Purpose

This ADR backlog records implementation decisions that are approved, proposed,
or deferred. It exists so source-of-truth docs can distinguish owner-approved
choices from plausible candidates that still need approval.

## Source of Truth

- Product decision: docs/product/02-spec.md
- Contract source: docs/adr/0002-contract-source-of-truth.md
- Technical owner: UNASSIGNED

## Decisions

| Area | Leading candidate | Status |
| --- | --- | --- |
| Config filename | `aibom.toml` | Approved for explicit and target-root discovered config files |
| Config discovery | `<model-directory>/aibom.toml` only | Approved for MVP polish on 2026-07-08 |
| Config schema | AI-BOM config schema v1 | Approved for runtime validation on 2026-07-07 |
| CLI command | `ai-bom generate` | Approved for MVP on 2026-07-07 |
| First exporter | CycloneDX JSON 1.7 | Approved by implementation kickoff on 2026-07-06 |
| Second exporter | SPDX AI profile | Deferred |
| Runtime | Python 3.12 | Approved by owner on 2026-07-06 |
| CLI adapter | `argparse` | Approved by owner on 2026-07-06 |
| Package metadata | `pyproject.toml` with setuptools build backend | Approved by implementation kickoff on 2026-07-06 |
| Schema validation dependency | `jsonschema>=4.25,<5` | Approved by implementation kickoff on 2026-07-06 |
| Project lockfile | `uv.lock` | Approved by uv adoption on 2026-07-06 |
| Dependency lockfile intake | Explicit config-declared dependency file references | Approved for MVP on 2026-07-07 |
| Artifact discovery opt-in | `[artifacts].discovery = true` adds bounded default model artifact patterns in config only | Approved for MVP polish on 2026-07-09 |
| Artifact discovery CLI flag | CLI override for artifact discovery | Deferred |
| Action wrapper | Composite GitHub Action invoking `uv run --project` | Approved for MVP on 2026-07-07 |
| First public release | GitHub Release `v0.1.0` with no PyPI package | Approved by owner on 2026-07-07 |
| Action tag policy | Immutable patch tags plus mutable `v0` for compatible 0.x action updates | Approved by owner on 2026-07-08 |
| PyPI package metadata | Classifiers, keywords, and project URLs in `pyproject.toml` | Approved for pre-publish preparation on 2026-07-07 |
| PyPI package publishing | `.github/workflows/publish-pypi.yml` publishes `v0.1.2` or later patch tags via PyPI Trusted Publishing after registry setup and external action smoke | Approved workflow policy on 2026-07-08 |
| Repository license | Apache-2.0 | Approved by owner on 2026-07-06 |
| Network policy | No network in MVP | Proposed |
| Telemetry policy | No telemetry in MVP | Proposed |
| Cache policy | No hidden cache in MVP | Proposed |
| Redaction default | strict | Approved for CLI and terminal output on 2026-07-07 |
| Action-managed runtime setup | Composite action installs or prepares Python and `uv` itself | Deferred |
| Staged output writes | Destination-local temp-file writes, stale-output cleanup, and partial-output cleanup | Approved for MVP hardening on 2026-07-08 |
| Generation manifest | Manifest-backed run identity and output-set verification | Approved for MVP hardening on 2026-07-08 |
| Artifact snapshot consistency | Single-descriptor stat/hash/stat validation with conservative failure on mutation | Approved for MVP hardening on 2026-07-08 |
| Artifact immutable staging | Tool-managed immutable artifact copy before hashing | Deferred |
| Artifact glob budgets | Fixed MVP match-count, single-file byte, and total-byte budgets with warning skips | Approved for MVP hardening on 2026-07-09 |
| Configurable artifact budgets | Config or CLI overrides for artifact match-count and byte budgets | Deferred |
| Common provider-token redaction | AWS, Slack, GitLab, Google API key, Hugging Face, GCP OAuth, Bearer, and JWT-shaped values in strict mode | Approved for MVP hardening on 2026-07-09 |
| Key-aware redaction matrix | Sensitive key names such as token, secret, password, credential, authorization, api_key, access_key, private_key, client_secret, refresh_token, and id_token redact values in strict mode | Approved for MVP hardening on 2026-07-09 |
| Schema-aware secret-key warnings | Warnings for sensitive keys detected in config beyond redaction | Proposed |

## Guardrails

- Approved decisions may be used by implementation and release docs.
- Proposed and deferred decisions must not be implemented as final choices until
  the matching ADR or source-of-truth doc moves them out of proposed status.
- Do not let exporter-specific fields leak into the normalized evidence model.
- Dependency lockfile support is config-driven path evidence in MVP. Automatic
  discovery, lockfile parsing, and package-manager-specific completeness claims
  remain deferred until a later ADR approves them.
- Artifact discovery is config-driven opt-in only. It must not run when
  `[artifacts].discovery` is absent or false, and it must reuse artifact budget,
  symlink, target-root, and no-fabrication warning policies.
- Config discovery is limited to the target-root `aibom.toml` filename. Parent
  directory search, alternate filenames, and environment-variable config remain
  deferred.
- The GitHub Action wrapper may invoke the packaged CLI from the action checkout,
  expose summary-derived outputs, and default output files under `RUNNER_TEMP`.
  Artifact upload remains deferred and must not be enabled by default.
- The first public release may create `v0.1.0` and a GitHub Release. Mutable
  `v0` may point to the latest compatible 0.x action release after external
  smoke verification. Marketplace registration remains deferred until that
  policy is explicitly approved.
- PyPI metadata may be prepared and validated locally. Package upload requires
  PyPI Trusted Publishing through `.github/workflows/publish-pypi.yml`,
  registry ownership confirmation, package-name recheck at release time, full
  validation, and a new patch tag.
- Do not add network, cache, telemetry, hosted registry, or write-permission
  behavior while these decisions remain proposed.
- Do not claim action-managed runtime setup, immutable artifact staging,
  artifact discovery CLI overrides, configurable artifact budgets, or
  schema-aware secret-key warnings until the corresponding deferred/proposed
  decision is approved and implemented with fixtures.

## Review Blockers

- A change treats proposed or deferred rows as approval for implementation.
- A change records a durable runtime, package, dependency, license, or exporter
  decision only in examples or README prose.
- A change weakens validation or skips required evidence.
