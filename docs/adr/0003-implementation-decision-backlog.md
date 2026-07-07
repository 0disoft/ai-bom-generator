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
| Config filename | `aibom.toml` | Approved for explicit config files on 2026-07-07 |
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
| Action wrapper | Composite GitHub Action invoking `uv run --project` | Approved for MVP on 2026-07-07 |
| First public release | GitHub Release `v0.1.0` with no PyPI package | Approved by owner on 2026-07-07 |
| Action tag policy | Immutable version tags only for MVP; no mutable `v0` tag yet | Approved by owner on 2026-07-07 |
| PyPI package metadata | Classifiers, keywords, and project URLs in `pyproject.toml` | Approved for pre-publish preparation on 2026-07-07 |
| Repository license | Apache-2.0 | Approved by owner on 2026-07-06 |
| Network policy | No network in MVP | Proposed |
| Telemetry policy | No telemetry in MVP | Proposed |
| Cache policy | No hidden cache in MVP | Proposed |
| Redaction default | strict | Approved for CLI and terminal output on 2026-07-07 |

## Guardrails

- Approved decisions may be used by implementation and release docs.
- Proposed and deferred decisions must not be implemented as final choices until
  the matching ADR or source-of-truth doc moves them out of proposed status.
- Do not let exporter-specific fields leak into the normalized evidence model.
- Dependency lockfile support is config-driven path evidence in MVP. Automatic
  discovery, lockfile parsing, and package-manager-specific completeness claims
  remain deferred until a later ADR approves them.
- The GitHub Action wrapper may invoke the packaged CLI from the action checkout,
  expose summary-derived outputs, and default output files under `RUNNER_TEMP`.
  Artifact upload remains deferred and must not be enabled by default.
- The first public release may create `v0.1.0` and a GitHub Release. It must not
  publish to PyPI, create a mutable `v0` action tag, or register the Action in a
  marketplace until those policies are explicitly approved.
- PyPI metadata may be prepared and validated locally, but package upload,
  trusted publishing, token setup, and registry ownership remain deferred until
  a package-registry release policy is approved.
- Do not add network, cache, telemetry, hosted registry, or write-permission
  behavior while these decisions remain proposed.

## Review Blockers

- A change treats proposed or deferred rows as approval for implementation.
- A change records a durable runtime, package, dependency, license, or exporter
  decision only in examples or README prose.
- A change weakens validation or skips required evidence.
