# Fixture Matrix

Status: Draft
Owner: UNASSIGNED

## Purpose

Fixtures prove that AI-BOM Generator reports real evidence and missing evidence
honestly. They should be synthetic and safe to publish.

## Required Fixture Candidates

| Fixture | Purpose |
| --- | --- |
| `complete-project` | Full metadata, artifact digest, dependencies, dataset, prompt, eval, and training references. |
| `sparse-project` | Missing optional metadata appears as warnings, not inferred facts. |
| `invalid-config` | Invalid config fails with actionable location. |
| `missing-artifact` | Required artifact path fails or warns according to policy. |
| `hash-failure` | Digest collection failure produces collector failure. |
| `exporter-failure` | Invalid exporter mapping fails validation. |
| `secret-redaction` | Secret-shaped values are redacted or rejected across outputs. |
| `symlink-escape` | Symlink and target-root escape attempts are blocked. |
| `nondeterministic-ordering-guard` | Stable input produces stable ordering. |
| `large-artifact-simulated` | Streaming hash behavior is tested without committing large binaries. |

## Fixture Rules

- Use synthetic data only.
- Do not commit real model weights, real private prompts, real customer data, or real private dataset URLs.
- Dummy model files may use small binary files with model-like names.
- Golden outputs must be stable and reviewed when schema or warning taxonomy changes.
- Contract tests must validate generated summary and warning report JSON against `schemas/`.
- Exporter tests must validate generated CycloneDX JSON against the vendored official schema.

## Review Blockers

- A collector, exporter, warning, or redaction behavior is added without a matching fixture.
- A fixture contains real secrets or private artifacts.
- Golden output makes compliance, safety, or license conclusions that the tool did not prove.
