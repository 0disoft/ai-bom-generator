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
| Config filename | `aibom.toml` | Proposed |
| First exporter | CycloneDX JSON 1.7 | Approved by implementation kickoff on 2026-07-06 |
| Second exporter | SPDX AI profile | Deferred |
| Runtime | Python 3.12 | Approved by owner on 2026-07-06 |
| CLI adapter | `argparse` | Approved by owner on 2026-07-06 |
| Package metadata | `pyproject.toml` with setuptools build backend | Approved by implementation kickoff on 2026-07-06 |
| Schema validation dependency | `jsonschema>=4.25,<5` | Approved by implementation kickoff on 2026-07-06 |
| Lockfile | `uv.lock` | Proposed |
| Action wrapper | Composite GitHub Action | Proposed |
| Repository license | Apache-2.0 | Approved by owner on 2026-07-06 |
| Network policy | No network in MVP | Proposed |
| Telemetry policy | No telemetry in MVP | Proposed |
| Cache policy | No hidden cache in MVP | Proposed |
| Redaction default | strict | Proposed |

## Guardrails

- Approved decisions may be used by implementation and release docs.
- Proposed and deferred decisions must not be implemented as final choices until
  the matching ADR or source-of-truth doc moves them out of proposed status.
- Do not let exporter-specific fields leak into the normalized evidence model.
- Do not add network, cache, telemetry, hosted registry, or write-permission
  behavior while these decisions remain proposed.

## Review Blockers

- A change treats proposed or deferred rows as approval for implementation.
- A change records a durable runtime, package, dependency, license, or exporter
  decision only in examples or README prose.
- A change weakens validation or skips required evidence.
